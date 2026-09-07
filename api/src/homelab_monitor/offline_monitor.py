import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from homelab_monitor.alert_engine import AlertEngine
from homelab_monitor.database import get_engine
from homelab_monitor.settings import Settings
from homelab_monitor.telegram import dispatch_alert_events

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
        events = AlertEngine(settings).evaluate_offline_agents(db)
        db.commit()
    dispatch_alert_events(settings, events)
