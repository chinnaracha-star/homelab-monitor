import asyncio
import logging

from homelab_monitor.infrastructure import get_infrastructure_service
from homelab_monitor.ops_history import record_backup_snapshot, record_photo_snapshot
from homelab_monitor.photo_stats import build_photo_stats
from homelab_monitor.realtime import hub
from homelab_monitor.settings import Settings

logger = logging.getLogger("homelab_monitor.infrastructure")


async def run_infrastructure_monitor(settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.infrastructure_refresh_seconds)
        try:
            await asyncio.to_thread(refresh_infrastructure)
        except Exception:
            logger.exception("infrastructure_refresh_failed")


def refresh_infrastructure() -> None:
    service = get_infrastructure_service()
    snapshots = service.refresh()
    by_name = {item.service: item for item in snapshots}
    record_photo_snapshot(build_photo_stats(by_name))
    backup = by_name.get("backup")
    if backup is not None:
        record_backup_snapshot(backup)
    hub.publish("overview_updated", reason="photo_services_updated")
    hub.publish("overview_updated", reason="backup_updated")
