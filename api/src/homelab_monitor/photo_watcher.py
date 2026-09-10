import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from homelab_monitor.database import get_engine
from homelab_monitor.photo_events import PhotoEventRepository, resolved_watch_folders
from homelab_monitor.photo_folders import display_folder_name, inspect_watch_folder
from homelab_monitor.photo_telegram import format_new_photo_message
from homelab_monitor.realtime import hub
from homelab_monitor.settings import Settings
from homelab_monitor.telegram import TelegramNotificationError, TelegramNotifier

logger = logging.getLogger("homelab_monitor.photo_watcher")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp"}
IGNORE_SUFFIXES = {".tmp", ".part"}
ALLOWED_INTERVALS = {5, 10, 30, 60}
ALLOWED_MAX_EVENTS = {100, 500, 1000}
ALLOWED_AUTO_DELETE_DAYS = {0, 30, 90}


def is_ignored_name(name: str) -> bool:
    if name.startswith("."):
        return True
    lowered = name.lower()
    return any(lowered.endswith(suffix) for suffix in IGNORE_SUFFIXES)


def is_image_file(path: Path) -> bool:
    if is_ignored_name(path.name):
        return False
    return path.suffix.lower() in IMAGE_EXTENSIONS


def path_is_hidden(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    return any(part.startswith(".") for part in relative.parts)


def iter_image_files(watch_folder: Path, recursive: bool) -> list[Path]:
    if not watch_folder.is_dir():
        return []
    try:
        candidates = watch_folder.rglob("*") if recursive else watch_folder.iterdir()
        files: list[Path] = []
        for candidate in candidates:
            try:
                if not candidate.is_file():
                    continue
            except OSError:
                continue
            if path_is_hidden(candidate, watch_folder):
                continue
            if is_image_file(candidate):
                files.append(candidate)
        return files
    except OSError:
        return []


def file_created_at(path: Path) -> datetime:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return stamp


class PhotoWatcherService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._primed: set[str] = set()
        self._seen: dict[str, set[tuple[str, str]]] = {}
        self._logged_enabled: bool | None = None
        self.indexed_files = 0

    def reset_baseline(self) -> None:
        self._primed = set()
        self._seen = {}

    def sync_watch_roots(self, folders: list[str]) -> None:
        incoming = set(folders)
        self._primed = {item for item in self._primed if item in incoming}
        self._seen = {key: value for key, value in self._seen.items() if key in incoming}

    def scan_once(
        self,
        db: Session,
        *,
        send_text: Callable[[str], dict] | None = None,
    ) -> int:
        logger.info("photo_watcher_tick")
        repo = PhotoEventRepository(db)
        config = repo.ensure_settings(self._settings)
        folders = resolved_watch_folders(config)
        self.sync_watch_roots(folders)
        if not config.enabled:
            if self._logged_enabled is not False:
                logger.info("Photo Monitor disabled")
                self._logged_enabled = False
            self.indexed_files = 0
            db.commit()
            return 0
        if self._logged_enabled is not True:
            self._log_startup(folders)
            self._logged_enabled = True
        created = 0
        scanned = 0
        for watch_root in folders:
            logger.info("loading_settings folder=%s", watch_root)
            reason = inspect_watch_folder(watch_root)
            accessible = reason is None
            logger.info(
                "checking_folder folder=%s exists=%s accessible=%s",
                watch_root,
                Path(watch_root).exists(),
                accessible,
            )
            if reason is not None:
                logger.warning("⚠ Cannot access")
                logger.warning("%s", watch_root)
                logger.warning("Reason")
                logger.warning("%s", reason)
                logger.info("scan_complete folder=%s files=%s", watch_root, 0)
                continue
            logger.info("scanning_files folder=%s", watch_root)
            try:
                discovered = iter_image_files(Path(watch_root), config.recursive)
            except OSError as exc:
                logger.warning("⚠ Cannot access")
                logger.warning("%s", watch_root)
                logger.warning("Reason")
                logger.warning("%s", exc.strerror or str(exc))
                logger.info("scan_complete folder=%s files=%s", watch_root, 0)
                continue
            scanned += len(discovered)
            created += self._scan_folder(
                db,
                repo,
                watch_root=watch_root,
                discovered=discovered,
                send_text=send_text,
            )
            logger.info("scan_complete folder=%s files=%s", watch_root, len(discovered))
        self.indexed_files = scanned
        repo.prune(max_events=config.max_events, auto_delete_days=config.auto_delete_days)
        if created:
            db.commit()
            hub.notify_ingest(reason="photo_monitor", agent_id=None, alerts_changed=False)
        else:
            db.commit()
        return created

    def _log_startup(self, folders: list[str]) -> None:
        logger.info("Photo Monitor enabled")
        logger.info("Watching %s folders", len(folders))
        for folder in folders:
            reason = inspect_watch_folder(folder)
            if reason is None:
                logger.info("✓ %s", folder)
                continue
            logger.warning("⚠ Cannot access")
            logger.warning("%s", folder)
            logger.warning("Reason")
            logger.warning("%s", reason)

    def _scan_folder(
        self,
        db: Session,
        repo: PhotoEventRepository,
        *,
        watch_root: str,
        discovered: list[Path],
        send_text: Callable[[str], dict] | None,
    ) -> int:
        seen = self._seen.setdefault(watch_root, set())
        if watch_root not in self._primed:
            self._seen[watch_root] = {(str(path.parent), path.name) for path in discovered}
            self._primed.add(watch_root)
            logger.info("baseline_created folder=%s files=%s", watch_root, len(discovered))
            return 0
        created = 0
        for path in discovered:
            folder = str(path.parent)
            filename = path.name
            key = (folder, filename)
            if key in seen or repo.exists(folder, filename):
                continue
            try:
                size_bytes = path.stat().st_size
                created_at = file_created_at(path)
            except OSError:
                logger.warning("photo_stat_failed folder=%s path=%s", watch_root, str(path))
                continue
            telegram_sent = self._notify(
                send_text,
                filename=filename,
                folder=watch_root,
                size_bytes=size_bytes,
                created_at=created_at,
            )
            try:
                with db.begin_nested():
                    repo.add(
                        filename=filename,
                        folder=folder,
                        size_bytes=size_bytes,
                        created_at=created_at,
                        telegram_sent=telegram_sent,
                    )
            except IntegrityError:
                seen.add(key)
                continue
            logger.info("new_photo_detected folder=%s file=%s", watch_root, filename)
            if telegram_sent:
                logger.info("telegram_sent folder=%s file=%s", watch_root, filename)
            else:
                logger.warning("telegram_failed folder=%s file=%s", watch_root, filename)
            seen.add(key)
            created += 1
        return created

    def _notify(
        self,
        send_text: Callable[[str], dict] | None,
        *,
        filename: str,
        folder: str,
        size_bytes: int,
        created_at: datetime,
    ) -> bool:
        message = format_new_photo_message(
            filename=filename,
            folder=folder,
            size_bytes=size_bytes,
            created_at=created_at,
        )
        sender = send_text
        if sender is None:
            try:
                notifier = TelegramNotifier.from_settings(self._settings)
            except ValueError:
                logger.warning("photo_telegram_config_invalid")
                return False
            if notifier is None:
                logger.warning("photo_telegram_not_configured folder=%s", folder)
                return False
            sender = notifier.send_text
        try:
            sender(message)
        except TelegramNotificationError:
            logger.exception("photo_telegram_failed")
            return False
        except Exception:
            logger.exception("photo_telegram_failed")
            return False
        return True


_service: PhotoWatcherService | None = None


def get_photo_watcher_service(settings: Settings) -> PhotoWatcherService:
    global _service
    if _service is None:
        _service = PhotoWatcherService(settings)
    return _service


def reset_photo_watcher_service() -> None:
    global _service
    _service = None


def _next_interval(value: object) -> int:
    try:
        seconds = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 10
    if seconds in ALLOWED_INTERVALS:
        return seconds
    return 10


async def run_photo_watcher(settings: Settings) -> None:
    logger.info("photo_watcher_started")
    if not settings.photo_watcher_enabled:
        logger.info("photo_watcher_disabled")
        return

    service = get_photo_watcher_service(settings)
    while True:
        interval = 10
        try:
            interval = await asyncio.to_thread(_scan_and_interval, settings, service)
            logger.info("photo_watcher_scan_finished interval=%s", interval)
        except asyncio.CancelledError:
            logger.info("photo_watcher_cancelled")
            raise
        except Exception:
            logger.exception("photo_watcher_failed")
            interval = 10
        delay = max(_next_interval(interval), 5)
        logger.info("photo_watcher_sleep seconds=%s", delay)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info("photo_watcher_cancelled")
            raise


def _scan_and_interval(settings: Settings, service: PhotoWatcherService) -> int:
    del settings
    with Session(get_engine()) as db:
        service.scan_once(db)
        if db.in_transaction():
            db.commit()
        row = PhotoEventRepository(db).get_settings()
        if row is None:
            return 10
        return _next_interval(row.scan_interval_seconds)