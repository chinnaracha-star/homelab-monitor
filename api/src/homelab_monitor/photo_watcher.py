import asyncio
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from homelab_monitor.database import get_engine
from homelab_monitor.photo_baseline import baseline_file_path, load_baseline, save_baseline
from homelab_monitor.photo_events import PhotoEventRepository, resolved_watch_folders
from homelab_monitor.photo_folders import inspect_watch_folder
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


def _skip(reason: str, path: Path, **detail: object) -> None:
    extra = " ".join(f"{key}={value}" for key, value in detail.items())
    name = path.name.encode("utf-8", "replace").decode("utf-8")
    if extra:
        logger.debug("SKIP: %s file=%s %s", reason, name, extra)
    else:
        logger.debug("SKIP: %s file=%s", reason, name)


def _entry_is_file(path: Path) -> bool | None:
    try:
        return path.is_file()
    except OSError as exc:
        if path.suffix.lower() in IMAGE_EXTENSIONS and not is_ignored_name(path.name):
            logger.debug(
                "cifs_stat_unknown_including_candidate file=%s reason=%s",
                path.name.encode("utf-8", "replace").decode("utf-8"),
                exc.strerror or exc,
            )
            return True
        _skip("stat failed", path, reason=exc.strerror or str(exc))
        return None


def iter_image_files(watch_folder: Path, recursive: bool) -> list[Path]:
    if not watch_folder.is_dir():
        logger.info("scan_ended reason=not_a_directory folder=%s", watch_folder)
        return []
    files: list[Path] = []

    def on_walk_error(error: OSError) -> None:
        logger.warning(
            "walk_error folder=%s error=%s",
            error.filename,
            error.strerror or error,
        )

    try:
        if recursive:
            for dirpath, dirnames, filenames in os.walk(
                watch_folder, followlinks=False, onerror=on_walk_error
            ):
                dirnames[:] = [name for name in dirnames if not name.startswith(".")]
                current = Path(dirpath)
                for name in filenames:
                    if name.startswith("."):
                        continue
                    try:
                        candidate = current / name
                        if _include_candidate(candidate, watch_folder):
                            files.append(candidate)
                    except Exception:
                        logger.exception("SKIP: candidate_failed file=%s", name)
        else:
            with os.scandir(watch_folder) as entries:
                for entry in entries:
                    if entry.name.startswith("."):
                        continue
                    try:
                        candidate = Path(entry.path)
                        if _include_candidate(candidate, watch_folder):
                            files.append(candidate)
                    except Exception:
                        logger.exception("SKIP: candidate_failed file=%s", entry.name)
    except OSError as exc:
        logger.info(
            "scan_ended reason=walk_failed folder=%s error=%s",
            watch_folder,
            exc.strerror or exc,
        )
        return files
    return files


def _include_candidate(candidate: Path, root: Path) -> bool:
    if path_is_hidden(candidate, root):
        _skip("hidden file", candidate)
        return False
    if any(candidate.name.lower().endswith(suffix) for suffix in IGNORE_SUFFIXES):
        _skip("partial upload", candidate)
        return False
    if candidate.name.startswith("."):
        _skip("hidden file", candidate)
        return False
    is_file = _entry_is_file(candidate)
    if is_file is None:
        return False
    if not is_file:
        if candidate.suffix.lower() in IMAGE_EXTENSIONS:
            _skip("not a file", candidate)
        return False
    if candidate.suffix.lower() not in IMAGE_EXTENSIONS:
        _skip("unsupported extension", candidate)
        return False
    logger.debug("discovered filename=%s path=%s", candidate.name, candidate)
    return True


def file_created_at(path: Path) -> datetime:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return stamp


def _file_key(path: Path) -> tuple[str, str]:
    return (os.path.normpath(str(path.parent)), path.name)


class PhotoWatcherService:
    def __init__(self, settings: Settings, *, baseline_path: Path | None = None) -> None:
        self._settings = settings
        self._baseline_path = baseline_path or baseline_file_path(settings)
        self._seen = load_baseline(self._baseline_path)
        self._primed: set[str] = set(self._seen)
        self._dirty = False
        self._logged_enabled: bool | None = None
        self.indexed_files = 0
        if self._primed:
            logger.info(
                "photo_baseline_restored folders=%s files=%s",
                len(self._primed),
                sum(len(keys) for keys in self._seen.values()),
            )

    def reset_baseline(self) -> None:
        self._primed = set()
        self._seen = {}
        self._dirty = True
        self._persist()

    def sync_watch_roots(self, folders: list[str]) -> None:
        incoming = {os.path.normpath(item) for item in folders}
        primed = {item for item in self._primed if item in incoming}
        seen = {key: value for key, value in self._seen.items() if key in incoming}
        if primed != self._primed or seen.keys() != self._seen.keys():
            self._dirty = True
        self._primed = primed
        self._seen = seen

    def _persist(self) -> None:
        if not self._dirty:
            return
        try:
            save_baseline(self._baseline_path, self._seen)
            self._dirty = False
        except OSError:
            logger.exception("photo_baseline_save_failed path=%s", self._baseline_path)

    def scan_once(
        self,
        db: Session,
        *,
        send_text: Callable[[str], dict] | None = None,
    ) -> int:
        logger.info("photo_watcher_tick")
        repo = PhotoEventRepository(db)
        config = repo.ensure_settings(self._settings)
        folders = [os.path.normpath(item) for item in resolved_watch_folders(config)]
        self.sync_watch_roots(folders)
        if not config.enabled:
            if self._logged_enabled is not False:
                logger.info("Photo Monitor disabled")
                self._logged_enabled = False
            self.indexed_files = 0
            db.commit()
            logger.info("scan_ended reason=disabled")
            return 0
        if not folders:
            db.commit()
            logger.info("scan_ended reason=no_watch_folders")
            return 0
        if self._logged_enabled is not True:
            self._log_startup(folders)
            self._logged_enabled = True
        logger.info("recursive=%s folders=%s", config.recursive, len(folders))
        created = 0
        scanned = 0
        skipped = 0
        telegram_ok = 0
        folders_scanned = 0
        for watch_root in folders:
            logger.info("loading_settings folder=%s", watch_root)
            try:
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
                    logger.info("scan_ended reason=folder_unavailable folder=%s", watch_root)
                    continue
                folders_scanned += 1
                logger.info("scanning_files folder=%s recursive=%s", watch_root, config.recursive)
                discovered = iter_image_files(Path(watch_root), config.recursive)
                scanned += len(discovered)
                added, folder_skipped, folder_telegram = self._scan_folder(
                    db,
                    repo,
                    watch_root=watch_root,
                    discovered=discovered,
                    send_text=send_text,
                )
                created += added
                skipped += folder_skipped
                telegram_ok += folder_telegram
                logger.info("scan_complete folder=%s files=%s", watch_root, len(discovered))
            except Exception:
                logger.exception("scan_ended reason=folder_exception folder=%s", watch_root)
        self.indexed_files = scanned
        try:
            repo.prune(max_events=config.max_events, auto_delete_days=config.auto_delete_days)
        except Exception:
            logger.exception("photo_watcher_prune_failed")
        if created:
            db.commit()
            hub.notify_ingest(reason="photo_monitor", agent_id=None, alerts_changed=False)
        else:
            db.commit()
        self._persist()
        logger.info("Folders scanned: %s", folders_scanned)
        logger.info("Files discovered: %s", scanned)
        logger.info("Files skipped: %s", skipped)
        logger.info("New files detected: %s", created)
        logger.info("Events inserted: %s", created)
        logger.info("Telegram sent: %s", telegram_ok)
        logger.info("scan_ended reason=cycle_complete created=%s", created)
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
    ) -> tuple[int, int, int]:
        seen = self._seen.setdefault(watch_root, set())
        logger.info("seen_cache folder=%s size=%s", watch_root, len(seen))
        if watch_root not in self._primed:
            self._seen[watch_root] = {_file_key(path) for path in discovered}
            self._primed.add(watch_root)
            self._dirty = True
            logger.info("baseline_created folder=%s files=%s", watch_root, len(discovered))
            logger.info("scan_ended reason=baseline folder=%s files=%s", watch_root, len(discovered))
            return 0, len(discovered), 0
        created = 0
        skipped = 0
        telegram_ok = 0
        for path in discovered:
            try:
                added, was_skip, sent = self._handle_discovered(
                    db, repo, seen, watch_root, path, send_text
                )
            except Exception:
                logger.exception("SKIP: candidate_failed file=%s", path.name)
                skipped += 1
                continue
            created += added
            skipped += was_skip
            telegram_ok += sent
        return created, skipped, telegram_ok

    def _handle_discovered(
        self,
        db: Session,
        repo: PhotoEventRepository,
        seen: set[tuple[str, str]],
        watch_root: str,
        path: Path,
        send_text: Callable[[str], dict] | None,
    ) -> tuple[int, int, int]:
        folder, filename = _file_key(path)
        key = (folder, filename)
        in_seen = key in seen
        logger.debug(
            "candidate folder=%s file=%s seen_cache_size=%s in_seen=%s",
            watch_root,
            filename,
            len(seen),
            in_seen,
        )
        if in_seen:
            _skip("already in _seen", path, folder=watch_root)
            return 0, 1, 0
        exists = repo.exists(folder, filename)
        logger.debug("repo.exists=%s folder=%s file=%s", exists, folder, filename)
        if exists:
            _skip("repo.exists=True", path, folder=watch_root)
            seen.add(key)
            self._dirty = True
            return 0, 1, 0
        try:
            stat_result = path.stat()
            size_bytes = stat_result.st_size
            created_at = datetime.fromtimestamp(stat_result.st_mtime, tz=UTC)
            logger.debug(
                "file_stat file=%s size=%s mtime=%s",
                filename,
                size_bytes,
                created_at.isoformat(),
            )
        except OSError as exc:
            _skip("stat failed", path, reason=exc.strerror or str(exc))
            return 0, 1, 0
        telegram_sent = self._notify(
            send_text,
            filename=filename,
            folder=watch_root,
            size_bytes=size_bytes,
            created_at=created_at,
        )
        logger.info("insert_begin folder=%s file=%s", folder, filename)
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
            _skip("repo.exists=True", path, reason="integrity_error")
            seen.add(key)
            self._dirty = True
            return 0, 1, 0
        logger.info("insert_complete folder=%s file=%s", folder, filename)
        logger.info("new_photo_detected folder=%s file=%s", watch_root, filename)
        if telegram_sent:
            logger.info("telegram_sent folder=%s file=%s", watch_root, filename)
            sent = 1
        else:
            logger.warning("telegram_failed folder=%s file=%s", watch_root, filename)
            sent = 0
        seen.add(key)
        self._dirty = True
        return 1, 0, sent

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
        logger.info("telegram_send_begin folder=%s file=%s", folder, filename)
        try:
            sender(message)
        except TelegramNotificationError:
            logger.exception("photo_telegram_failed")
            return False
        except Exception:
            logger.exception("photo_telegram_failed")
            return False
        logger.info("telegram_send_complete folder=%s file=%s", folder, filename)
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
        logger.info("scan_ended reason=process_disabled")
        return

    service = get_photo_watcher_service(settings)
    while True:
        interval = 10
        try:
            interval = await asyncio.to_thread(_scan_and_interval, settings, service)
            logger.info("photo_watcher_scan_finished interval=%s", interval)
        except asyncio.CancelledError:
            logger.info("photo_watcher_cancelled")
            logger.info("scan_ended reason=cancelled")
            raise
        except Exception:
            logger.exception("photo_watcher_failed")
            logger.info("scan_ended reason=scan_exception")
            interval = 10
        delay = max(_next_interval(interval), 5)
        logger.info("photo_watcher_sleep seconds=%s", delay)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            logger.info("photo_watcher_cancelled")
            logger.info("scan_ended reason=cancelled")
            raise


def _scan_and_interval(settings: Settings, service: PhotoWatcherService) -> int:
    del settings
    with Session(get_engine()) as db:
        service.scan_once(db)
        if db.in_transaction():
            db.commit()
        row = PhotoEventRepository(db).get_settings()
        if row is None:
            logger.info("scan_ended reason=settings_missing")
            return 10
        return _next_interval(row.scan_interval_seconds)
