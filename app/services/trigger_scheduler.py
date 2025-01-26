import json
import logging
import os
from typing import Dict, Any, Optional
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio

import requests
from fastapi.security import OAuth2
from app.services.cache import cache_client

from app.services.db import SessionLocal
from app.models import EventLog, Trigger
from app.schemas import TriggerCreate

url = os.getenv("HTTP_URL")

# Configure a more streamlined logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class TriggerScheduler:
    """Advanced scheduler for managing and executing triggers."""

    _instance: Optional["TriggerScheduler"] = None

    @classmethod
    def get_instance(cls):
        """Thread-safe singleton method."""
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.scheduler = AsyncIOScheduler()
        self.active_jobs: Dict[int, Dict[str, Any]] = {}
        self._initialized = True

    async def add_trigger(self, trigger: TriggerCreate, test: bool = False):
        """
        Add a new trigger to the scheduler with optional test mode.

        :param trigger: Trigger object with scheduling details
        :param test: Flag to indicate if this is a test trigger
        """
        try:
            job_id = str(trigger.id)

            if job_id in self.active_jobs:
                self.remove_trigger(trigger.id)

            job_trigger = None
            if trigger.trigger_type == "scheduled":
                if trigger.is_recurring:
                    job_trigger = IntervalTrigger(seconds=trigger.interval_seconds)
                elif trigger.schedule:
                    if isinstance(trigger.schedule, str):
                        job_trigger = CronTrigger.from_crontab(trigger.schedule)
                    elif isinstance(trigger.schedule, datetime):
                        job_trigger = CronTrigger(
                            year=trigger.schedule.year,
                            month=trigger.schedule.month,
                            day=trigger.schedule.day,
                            hour=trigger.schedule.hour,
                            minute=trigger.schedule.minute,
                        )

            if trigger.trigger_type == "api":
                await self._execute_trigger(trigger, test)
                return

            if job_trigger:
                job = self.scheduler.add_job(
                    self._execute_trigger,
                    trigger=job_trigger,
                    id=job_id,
                    args=[trigger, test],
                    max_instances=1,
                    misfire_grace_time=None,
                    coalesce=True,
                )

                self.active_jobs[trigger.id] = {
                    "job": job,
                    "trigger": trigger,
                    "is_test": test,
                }

        except Exception as e:
            log_method = logger.debug if test else logger.error
            log_method(f"{'Test ' if test else ''}Trigger scheduling failed: {e}")

    async def _handle_http_request(
        self, payload: Any, test: bool, trigger_id: int
    ) -> Dict[str, Any]:
        try:
            # Convert payload to dict if it's a string
            payload_dict = json.loads(payload) if isinstance(payload, str) else payload

            if test:
                payload_dict = (
                    {**payload_dict, "test": True}
                    if isinstance(payload_dict, dict)
                    else payload_dict
                )

            # Format payload for Discord webhook
            formatted_payload = {
                "content": (
                    json.dumps(payload_dict)
                    if isinstance(payload_dict, dict)
                    else str(payload_dict)
                )
            }

            headers = {"Content-Type": "application/json"}
            logger.info(f"Sending webhook request: {formatted_payload}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=formatted_payload, headers=headers
                ) as response:
                    logger.info(f"Webhook response status: {response.status}")

                    if response.status in [200, 204]:
                        logger.info("Webhook message sent successfully")
                        return {"success": True, "message": "Message sent successfully"}
                    else:
                        response_text = await response.text()
                        logger.error(f"Webhook send failed: {response_text}")
                        return {"success": False, "error": response_text}

        except json.JSONDecodeError as je:
            logger.error(f"Invalid JSON payload: {je}")
            return {"success": False, "error": str(je)}
        except Exception as e:
            logger.error(f"Webhook request error: {e}")
            return {"success": False, "error": str(e)}

    async def _cleanup_test_trigger(self, trigger_id: int) -> bool:
        """Clean up test trigger from both cache and scheduler."""
        try:
            test_triggers = await cache_client.get("test_triggers")
            if test_triggers:
                if isinstance(test_triggers, bytes):
                    test_triggers = test_triggers.decode("utf-8")
                triggers_list = json.loads(test_triggers)
                triggers_list = [t for t in triggers_list if t["id"] != trigger_id]
                await cache_client.set("test_triggers", json.dumps(triggers_list))

            await cache_client.delete(f"test_trigger:{trigger_id}")
            logger.debug(f"Cleaned up test trigger {trigger_id}")

            return True
        except Exception as e:
            logger.error(f"Test trigger cleanup failed: {e}")
            return False

    async def _execute_trigger(self, trigger: TriggerCreate, test: bool = False):
        """Execute the trigger's payload."""
        try:
            with SessionLocal() as db:
                event_log = EventLog(
                    trigger_id=trigger.id,
                    trigger_type=trigger.trigger_type,
                    name=trigger.name,
                    payload=trigger.payload,
                    is_test=test,
                )

                db.add(event_log)
                db.commit()

                logger.info(f"{'Test ' if test else ''}Trigger {trigger.id} executed")

            if trigger.trigger_type == "api":
                await self._handle_http_request(trigger.payload, test, trigger.id)

            if test:
                await self._cleanup_test_trigger(trigger.id)

                self.remove_trigger(trigger.id)

        except Exception as e:
            log_method = logger.warning if test else logger.error
            log_method(f"{'Test ' if test else ''}Trigger {trigger.id} failed: {e}")

    def remove_trigger(self, trigger_id: int):
        """Remove a scheduled trigger."""
        if trigger_id in self.active_jobs:
            job = self.active_jobs[trigger_id]["job"]
            job.remove()
            del self.active_jobs[trigger_id]
            logger.info(f"Trigger {trigger_id} removed")

    def remove_old_logs(self):
        """Remove event logs older than 48 hours."""
        with SessionLocal() as db:
            db.query(EventLog).filter(
                EventLog.triggered_at < datetime.utcnow() - timedelta(hours=48)
            ).delete()
            db.commit()
        logger.info("Old logs cleaned up")

    async def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.scheduler.add_job(
                self.remove_old_logs, trigger=CronTrigger.from_crontab("*/5 * * * *")
            )

            with SessionLocal() as db:
                to_schedule = db.query(Trigger).all()
                for trigger in to_schedule:
                    await self.add_trigger(trigger)

            logger.info("Scheduler started with existing triggers")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")


scheduler = TriggerScheduler.get_instance()


def initialize_scheduler():
    """Initialize and start the scheduler."""
    asyncio.create_task(scheduler.start())


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()
