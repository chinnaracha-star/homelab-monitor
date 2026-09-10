import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from homelab_monitor.alert_engine import AlertEngine
from homelab_monitor.database import get_engine
from homelab_monitor.realtime import hub
from homelab_monitor.settings import Settings

logger = logging.getLogger("homelab_monitor.offline_monitor")


async def run_offline_monitor(settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.alert_evaluation_interval_seconds)
        try:
            await asyncio.to_thread(evaluate_offline_agents, settings)
        except SQLAlchemyError:
            logger.exception("offline_evaluation_failed")


def evaluate_offline_agents(settings: Settings) -> None:
    with Session(get_engine()) as db:
        events, status_changed = AlertEngine(settings).evaluate_offline_agents(db)
        db.commit()
    if events or status_changed:
        hub.notify_ingest(reason="offline_evaluation", agent_id=None)
