import asyncio
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from homelab_monitor.database import get_engine
from homelab_monitor.photo_events import PhotoEventRepository, apply_watch_folders
from homelab_monitor.photo_folders import display_folder_name
from homelab_monitor.photo_telegram import format_new_photo_message, format_photo_size
from homelab_monitor.photo_watcher import PhotoWatcherService, is_image_file, run_photo_watcher
from homelab_monitor.settings import get_settings


def _monitor_settings(**updates: object):
    if "photo_watch_folder" in updates and "photo_watch_folders" not in updates:
        updates = {**updates, "photo_watch_folders": [updates["photo_watch_folder"]]}
    return get_settings().model_copy(update=updates)


def test_is_image_file_accepts_supported_extensions(tmp_path: Path) -> None:
    assert is_image_file(tmp_path / "shot.jpg")
    assert is_image_file(tmp_path / "shot.HEIC")
    assert is_image_file(tmp_path / "shot.webp")
    assert not is_image_file(tmp_path / "shot.txt")
    assert not is_image_file(tmp_path / ".hidden.jpg")
    assert not is_image_file(tmp_path / "shot.jpg.tmp")
    assert not is_image_file(tmp_path / "shot.jpg.part")


def test_format_new_photo_message_uses_english_layout() -> None:
    created = datetime(2026, 9, 10, 7, 0, 12, tzinfo=UTC)
    message = format_new_photo_message(
        filename="IMG_20260910_140012.jpg",
        folder="/mnt/pictures-ss22",
        size_bytes=int(3.52 * 1024 * 1024),
        created_at=created,
    )
    assert "📸 New Photo" in message
    assert "Pictures-SS22" in message
    assert "/mnt/pictures-ss22" not in message
    assert "IMG_20260910_140012.jpg" in message
    assert format_photo_size(int(3.52 * 1024 * 1024)) in message
    assert "10 Sep 2026" in message
    assert "14:00:12" in message
    assert "QNAP NAS" in message


def test_first_initialization_creates_enabled_watcher(caplog) -> None:
    settings = _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/mnt/picture-all")
    with Session(get_engine()) as db:
        with caplog.at_level("INFO", logger="homelab_monitor.photo_monitor"):
            row = PhotoEventRepository(db).ensure_settings(settings)
            db.commit()
        assert row.enabled is True
        assert row.watch_folder == "/mnt/picture-all"
        assert row.watch_folders == ["/mnt/picture-all"]
        assert "Photo Monitor initialized" in caplog.text
        assert "Photo Monitor enabled" in caplog.text
        assert "Watching 1 folders" in caplog.text
        again = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=False, photo_watch_folder="/other")
        )
        assert again.enabled is True
        assert again.watch_folder == "/mnt/picture-all"
        assert again.id == row.id


def test_legacy_picture_all_settings_expand_to_all_nas_shares() -> None:
    from homelab_monitor.photo_folders import DEFAULT_WATCH_FOLDERS

    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/mnt/picture-all")
        )
        assert row.watch_folders == ["/mnt/picture-all"]
        expanded = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/mnt/picture-all")
        )
        assert expanded.watch_folders == list(DEFAULT_WATCH_FOLDERS)
        assert expanded.watch_folder == "/mnt/picture-all"


def test_existing_settings_are_preserved() -> None:
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/Picture-All")
        )
        row.enabled = False
        row.watch_folder = "/custom-photos"
        row.watch_folders = []
        row.scan_interval_seconds = 60
        db.commit()
        preserved = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/Picture-All")
        )
        assert preserved.enabled is False
        assert preserved.watch_folder == "/custom-photos"
        assert preserved.watch_folders == ["/custom-photos"]
        assert preserved.scan_interval_seconds == 60


def test_watcher_baselines_existing_files_then_records_new_ones(
    tmp_path: Path,
    caplog,
) -> None:
    watch = tmp_path / "Picture-All"
    watch.mkdir()
    (watch / "existing.jpg").write_bytes(b"old")
    settings = _monitor_settings(photo_watcher_enabled=True, photo_watch_folder=str(watch))
    service = PhotoWatcherService(settings)
    sent: list[str] = []

    with Session(get_engine()) as db:
        repo = PhotoEventRepository(db)
        row = repo.ensure_settings(settings)
        row.recursive = False
        db.commit()
        assert row.enabled is True
        with caplog.at_level("INFO", logger="homelab_monitor.photo_watcher"):
            assert service.scan_once(db, send_text=sent.append) == 0
        assert repo.latest() is None
        assert "photo_watcher_tick" in caplog.text
        assert "loading_settings" in caplog.text
        assert "checking_folder" in caplog.text
        assert "scanning_files" in caplog.text
        assert "baseline_created" in caplog.text
        assert "scan_complete" in caplog.text
        assert "Photo Monitor enabled" in caplog.text
        assert "Watching 1 folders" in caplog.text
        assert f"✓ {watch}" in caplog.text

    (watch / "IMG_new.png").write_bytes(b"1234")
    with Session(get_engine()) as db:
        with caplog.at_level("INFO", logger="homelab_monitor.photo_watcher"):
            created = service.scan_once(db, send_text=sent.append)
        repo = PhotoEventRepository(db)
        latest = repo.latest()
        assert created == 1
        assert latest is not None
        assert latest.filename == "IMG_new.png"
        assert latest.size_bytes == 4
        assert latest.telegram_sent is True
        assert len(sent) == 1
        assert "new_photo_detected" in caplog.text
        assert "telegram_sent" in caplog.text
        assert str(watch) in caplog.text
        assert service.scan_once(db, send_text=sent.append) == 0
        assert repo.today_count() == 1


def test_telegram_sent_flag_is_false_when_notify_fails(tmp_path: Path) -> None:
    watch = tmp_path / "Picture-All"
    watch.mkdir()
    settings = _monitor_settings(photo_watcher_enabled=True, photo_watch_folder=str(watch))
    service = PhotoWatcherService(settings)

    def fail_send(_text: str) -> dict:
        raise RuntimeError("telegram down")

    with Session(get_engine()) as db:
        PhotoEventRepository(db).ensure_settings(settings)
        db.commit()
        assert service.scan_once(db, send_text=fail_send) == 0
    (watch / "shot.jpg").write_bytes(b"img")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=fail_send)
        latest = PhotoEventRepository(db).latest()
        assert created == 1
        assert latest is not None
        assert latest.telegram_sent is False


def test_photos_api_requires_auth_and_returns_stats(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    assert client.get("/api/v1/photos").status_code == 401
    headers = auth_header()
    listed = client.get("/api/v1/photos", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"] == []
    latest = client.get("/api/v1/photos/latest", headers=headers)
    assert latest.status_code == 404
    stats = client.get("/api/v1/photos/stats", headers=headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["today_count"] == 0
    assert body["last_photo"] is None
    assert body["watch_folder"]
    assert "watch_folders" in body
    assert "watch_folder_labels" in body
    assert body["indexed_files"] == 0
    settings = client.get("/api/v1/photos/settings", headers=headers)
    assert settings.status_code == 200
    assert settings.json()["enabled"] is get_settings().photo_watcher_enabled


def test_photo_settings_admin_only(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    payload = {
        "enabled": True,
        "watch_folder": "/Picture-All",
        "recursive": True,
        "scan_interval_seconds": 30,
        "max_events": 100,
        "auto_delete_days": 30,
    }
    viewer = auth_header("viewer", "viewer123")
    denied = client.put("/api/v1/photos/settings", headers=viewer, json=payload)
    assert denied.status_code == 403
    saved = client.put("/api/v1/photos/settings", headers=auth_header(), json=payload)
    assert saved.status_code == 200
    assert saved.json()["scan_interval_seconds"] == 30
    assert saved.json()["auto_delete_days"] == 30
    assert saved.json()["watch_folders"] == ["/Picture-All"]
    assert saved.json()["watch_folder"] == "/Picture-All"


def test_photos_list_includes_recent_event(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
    tmp_path: Path,
) -> None:
    watch = tmp_path / "Picture-All"
    watch.mkdir()
    settings = _monitor_settings(photo_watcher_enabled=True, photo_watch_folder=str(watch))
    service = PhotoWatcherService(settings)
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        db.commit()
        assert row.enabled is True
        service.scan_once(db, send_text=lambda _text: {})
    (watch / "latest.gif").write_bytes(b"gifdata")
    with Session(get_engine()) as db:
        service.scan_once(db, send_text=lambda _text: {})
    headers = auth_header()
    listed = client.get("/api/v1/photos", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["filename"] == "latest.gif"
    latest = client.get("/api/v1/photos/latest", headers=headers)
    assert latest.status_code == 200
    stats = client.get("/api/v1/photos/stats", headers=headers)
    assert stats.json()["today_count"] == 1
    assert stats.json()["last_photo"] == "latest.gif"


def test_run_photo_watcher_keeps_looping_after_scan(monkeypatch) -> None:
    import homelab_monitor.photo_watcher as module

    scans = {"count": 0}

    def fake_scan(_settings: object, _service: object) -> int:
        scans["count"] += 1
        return 5

    async def fake_sleep(_seconds: float) -> None:
        if scans["count"] >= 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(module, "_scan_and_interval", fake_scan)
    monkeypatch.setattr(module.asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run_photo_watcher(_monitor_settings(photo_watcher_enabled=True)))
    assert scans["count"] >= 2


def test_legacy_watch_folder_migrates_into_watch_folders() -> None:
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/legacy")
        )
        row.watch_folders = None  # type: ignore[assignment]
        row.watch_folder = "/only-legacy"
        db.commit()
        migrated = PhotoEventRepository(db).ensure_settings(
            _monitor_settings(photo_watcher_enabled=True, photo_watch_folder="/ignored")
        )
        assert migrated.watch_folders == ["/only-legacy"]
        assert migrated.watch_folder == "/only-legacy"


def test_photo_settings_put_accepts_watch_folders_and_legacy_watch_folder(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    headers = auth_header()
    listed = client.put(
        "/api/v1/photos/settings",
        headers=headers,
        json={
            "enabled": True,
            "watch_folders": ["/photos-a", "/photos-b"],
            "recursive": False,
            "scan_interval_seconds": 10,
            "max_events": 500,
            "auto_delete_days": 0,
        },
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["watch_folders"] == ["/photos-a", "/photos-b"]
    assert body["watch_folder"] == "/photos-a"
    stats = client.get("/api/v1/photos/stats", headers=headers)
    assert stats.json()["watch_folders"] == ["/photos-a", "/photos-b"]
    legacy = client.put(
        "/api/v1/photos/settings",
        headers=headers,
        json={
            "enabled": True,
            "watch_folder": "/photos-legacy",
            "recursive": False,
            "scan_interval_seconds": 10,
            "max_events": 500,
            "auto_delete_days": 0,
        },
    )
    assert legacy.status_code == 200
    assert legacy.json()["watch_folders"] == ["/photos-legacy"]
    assert legacy.json()["watch_folder"] == "/photos-legacy"


def test_watcher_scans_multiple_folders_with_independent_baselines(tmp_path: Path) -> None:
    folder_a = tmp_path / "photos-a"
    folder_b = tmp_path / "photos-b"
    folder_a.mkdir()
    folder_b.mkdir()
    (folder_a / "old-a.jpg").write_bytes(b"a")
    (folder_b / "old-b.jpg").write_bytes(b"b")
    settings = _monitor_settings(photo_watcher_enabled=True, photo_watch_folder=str(folder_a))
    service = PhotoWatcherService(settings)
    sent: list[str] = []
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.watch_folders = [str(folder_a), str(folder_b)]
        row.watch_folder = str(folder_a)
        row.recursive = False
        db.commit()
        assert service.scan_once(db, send_text=sent.append) == 0
        assert PhotoEventRepository(db).latest() is None
    (folder_a / "new-a.png").write_bytes(b"aa")
    (folder_b / "new-b.png").write_bytes(b"bb")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=sent.append)
        repo = PhotoEventRepository(db)
        items = repo.list_latest(20)
        names = {item.filename for item in items}
        assert created == 2
        assert names == {"new-a.png", "new-b.png"}
        assert all(item.telegram_sent for item in items)
        assert any(display_folder_name(str(folder_a)) in message for message in sent)
        assert any(display_folder_name(str(folder_b)) in message for message in sent)
        assert service.scan_once(db, send_text=sent.append) == 0
        (folder_a / "second-a.gif").write_bytes(b"aaa")
        created_again = service.scan_once(db, send_text=sent.append)
        assert created_again == 1
        assert repo.latest() is not None
        assert repo.latest().filename == "second-a.gif"


def test_photo_settings_rejects_duplicate_folders(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    response = client.put(
        "/api/v1/photos/settings",
        headers=auth_header(),
        json={
            "enabled": True,
            "watch_folders": ["/photos-a", "/photos-a"],
            "recursive": True,
            "scan_interval_seconds": 10,
            "max_events": 500,
            "auto_delete_days": 0,
        },
    )
    assert response.status_code == 422


def test_watcher_continues_when_one_folder_is_unavailable(tmp_path: Path, caplog) -> None:
    available = tmp_path / "pictures-ss22"
    missing = tmp_path / "picture-mae"
    available.mkdir()
    (available / "old.jpg").write_bytes(b"old")
    settings = _monitor_settings(photo_watch_folders=[str(available), str(missing)])
    service = PhotoWatcherService(settings)
    sent: list[str] = []
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.enabled = True
        apply_watch_folders(row, [str(available), str(missing)])
        db.commit()
        with caplog.at_level("WARNING", logger="homelab_monitor.photo_watcher"):
            assert service.scan_once(db, send_text=sent.append) == 0
        assert "Cannot access" in caplog.text
        assert str(missing) in caplog.text
    (available / "new.jpg").write_bytes(b"new")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=sent.append)
        latest = PhotoEventRepository(db).latest()
        assert created == 1
        assert latest is not None
        assert latest.filename == "new.jpg"
        assert service.indexed_files == 2


def test_watcher_baselines_added_folder_and_drops_removed_folder(tmp_path: Path) -> None:
    first = tmp_path / "picture-all"
    second = tmp_path / "pictures-ae"
    first.mkdir()
    second.mkdir()
    (first / "keep.jpg").write_bytes(b"keep")
    (second / "existing-b.jpg").write_bytes(b"old")
    settings = _monitor_settings(photo_watch_folders=[str(first)])
    service = PhotoWatcherService(settings)
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.enabled = True
        apply_watch_folders(row, [str(first)])
        db.commit()
        assert service.scan_once(db, send_text=lambda _text: {}) == 0
        apply_watch_folders(row, [str(first), str(second)])
        db.commit()
        service.sync_watch_roots([str(first), str(second)])
        assert service.scan_once(db, send_text=lambda _text: {}) == 0
        assert PhotoEventRepository(db).latest() is None
    (second / "fresh-b.png").write_bytes(b"new")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=lambda _text: {})
        assert created == 1
        apply_watch_folders(PhotoEventRepository(db).ensure_settings(settings), [str(first)])
        db.commit()
        service.sync_watch_roots([str(first)])
        (second / "ignored.png").write_bytes(b"nope")
        assert service.scan_once(db, send_text=lambda _text: {}) == 0


def test_partial_upload_rename_creates_event(tmp_path: Path, caplog) -> None:
    watch = tmp_path / "picture-all"
    watch.mkdir()
    settings = _monitor_settings(photo_watch_folders=[str(watch)])
    service = PhotoWatcherService(settings)
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.enabled = True
        row.recursive = False
        apply_watch_folders(row, [str(watch)])
        db.commit()
        assert service.scan_once(db, send_text=lambda _text: {}) == 0
    partial = watch / "IMG_20260910_140012.jpg.tmp"
    partial.write_bytes(b"uploading")
    with Session(get_engine()) as db:
        with caplog.at_level("DEBUG", logger="homelab_monitor.photo_watcher"):
            assert service.scan_once(db, send_text=lambda _text: {}) == 0
        assert "SKIP: partial upload" in caplog.text
    partial.rename(watch / "IMG_20260910_140012.jpg")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=lambda _text: {})
        latest = PhotoEventRepository(db).latest()
        assert created == 1
        assert latest is not None
        assert latest.filename == "IMG_20260910_140012.jpg"


def test_recursive_scan_detects_new_file_in_subfolder(tmp_path: Path) -> None:
    watch = tmp_path / "picture-all"
    nested = watch / "2026" / "09"
    nested.mkdir(parents=True)
    (nested / "old.jpg").write_bytes(b"old")
    settings = _monitor_settings(photo_watch_folders=[str(watch)])
    service = PhotoWatcherService(settings)
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.enabled = True
        row.recursive = True
        apply_watch_folders(row, [str(watch)])
        db.commit()
        assert service.scan_once(db, send_text=lambda _text: {}) == 0
    (nested / "new.png").write_bytes(b"new")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=lambda _text: {})
        latest = PhotoEventRepository(db).latest()
        assert created == 1
        assert latest is not None
        assert latest.filename == "new.png"
        assert latest.folder == str(nested)


def test_json_formatter_includes_traceback() -> None:
    import json
    import logging as pylogging

    from homelab_monitor.logging import JsonFormatter

    formatter = JsonFormatter()
    record = pylogging.LogRecord(
        "homelab_monitor.photo_watcher",
        pylogging.ERROR,
        __file__,
        1,
        "photo_watcher_failed",
        (),
        None,
    )
    try:
        raise RuntimeError("scan exploded")
    except RuntimeError:
        record.exc_info = sys.exc_info()
    payload = json.loads(formatter.format(record))
    assert payload["message"] == "photo_watcher_failed"
    assert "scan exploded" in payload["exception"]


def test_json_formatter_accepts_surrogate_filenames() -> None:
    import json
    import logging as pylogging

    from homelab_monitor.logging import JsonFormatter

    formatter = JsonFormatter()
    record = pylogging.LogRecord(
        "homelab_monitor.photo_watcher",
        pylogging.INFO,
        __file__,
        1,
        "SKIP: unsupported extension file=%s",
        ("bad\udcff.jpg",),
        None,
    )
    payload = json.loads(formatter.format(record))
    assert "SKIP" in payload["message"]


def test_scan_continues_when_one_folder_raises(tmp_path: Path, monkeypatch) -> None:
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    good.mkdir()
    bad.mkdir()
    (good / "keep.jpg").write_bytes(b"old")
    settings = _monitor_settings(photo_watch_folders=[str(bad), str(good)])
    service = PhotoWatcherService(settings)

    import homelab_monitor.photo_watcher as watcher

    real_iter = watcher.iter_image_files

    def flaky_iter(folder, recursive):
        if folder == Path(bad):
            raise RuntimeError("cifs blew up")
        return real_iter(folder, recursive)

    monkeypatch.setattr(watcher, "iter_image_files", flaky_iter)
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.enabled = True
        row.recursive = False
        apply_watch_folders(row, [str(bad), str(good)])
        db.commit()
        assert service.scan_once(db, send_text=lambda _text: {}) == 0
    (good / "fresh.png").write_bytes(b"new")
    with Session(get_engine()) as db:
        created = service.scan_once(db, send_text=lambda _text: {})
        latest = PhotoEventRepository(db).latest()
        assert created == 1
        assert latest is not None
        assert latest.filename == "fresh.png"


def test_persisted_baseline_survives_restart_and_notifies_offline_photos(
    tmp_path: Path,
) -> None:
    watch = tmp_path / "pictures-ss22"
    watch.mkdir()
    (watch / "existing.jpg").write_bytes(b"old")
    baseline = tmp_path / "photo_baseline.json"
    settings = _monitor_settings(photo_watch_folders=[str(watch)])
    first = PhotoWatcherService(settings, baseline_path=baseline)
    with Session(get_engine()) as db:
        row = PhotoEventRepository(db).ensure_settings(settings)
        row.enabled = True
        row.recursive = False
        apply_watch_folders(row, [str(watch)])
        db.commit()
        assert first.scan_once(db, send_text=lambda _text: {}) == 0
    assert baseline.is_file()
    (watch / "while-off.png").write_bytes(b"new")
    restarted = PhotoWatcherService(settings, baseline_path=baseline)
    sent: list[str] = []
    with Session(get_engine()) as db:
        created = restarted.scan_once(db, send_text=sent.append)
        latest = PhotoEventRepository(db).latest()
        assert created == 1
        assert latest is not None
        assert latest.filename == "while-off.png"
        assert sent
        assert restarted.scan_once(db, send_text=sent.append) == 0
