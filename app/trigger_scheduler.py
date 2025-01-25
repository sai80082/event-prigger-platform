import json
import logging
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import asyncio
from app.cache import cache_client

from app.db import SessionLocal
from app.models import EventLog, Trigger
from app.schemas import TriggerCreate

class TriggerScheduler:
    """Advanced scheduler for managing and executing triggers."""
    _instance: Optional['TriggerScheduler'] = None

    @classmethod
    def get_instance(cls):
        """Thread-safe singleton method."""
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.scheduler = AsyncIOScheduler()
        self.active_jobs: Dict[int, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)
        self._initialized = True

    async def add_trigger(self, trigger: TriggerCreate, test: bool = False):
        """
        Add a new trigger to the scheduler with optional test mode.
        
        :param trigger: Trigger object with scheduling details
        :param test: Flag to indicate if this is a test trigger
        """
        try:
            job_id = str(trigger.id)
            
            # Remove existing job if it exists
            if job_id in self.active_jobs:
                self.remove_trigger(trigger.id)
            
            # Create appropriate trigger
            job_trigger = None
            if trigger.trigger_type == 'scheduled':
                if trigger.is_recurring:
                    job_trigger = IntervalTrigger(seconds=trigger.interval_seconds)
                elif trigger.schedule:
                    # Safely handle schedule string
                    if isinstance(trigger.schedule, str):
                        job_trigger = CronTrigger.from_crontab(trigger.schedule)
                    elif isinstance(trigger.schedule, datetime):
                        # Convert datetime to cron-like string if needed
                        job_trigger = CronTrigger(
                            year=trigger.schedule.year,
                            month=trigger.schedule.month,
                            day=trigger.schedule.day,
                            hour=trigger.schedule.hour,
                            minute=trigger.schedule.minute
                        )
            
            # Handle API triggers
            if trigger.trigger_type == 'api':
                await self._handle_http_request(trigger.payload, test)
                return
            
            # Schedule the job if a trigger is created
            if job_trigger:
                job = self.scheduler.add_job(
                    self._execute_trigger,
                    trigger=job_trigger,
                    id=job_id,
                    args=[trigger, test],
                    max_instances=1,
                    misfire_grace_time=None,
                    coalesce=True
                )
                
                # Store job details
                self.active_jobs[trigger.id] = {
                    'job': job,
                    'trigger': trigger,
                    'is_test': test
                }
            
        except Exception as e:
            log_method = self._logger.debug if test else self._logger.error
            log_method(f"{'Test ' if test else ''}Trigger scheduling failed: {e}")
        
    async def _handle_http_request(self, payload, test):
        """Handle HTTP request payload."""
        import aiohttp
        
        url = payload.get('url')
        method = payload.get('method', 'GET')
        headers = payload.get('headers', {})
        data = payload.get('data')
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=data) as response:
                    self._logger.info(f"HTTP Request to {url} completed with status {response.status}")
        except Exception as e:
            self._logger.error(f"HTTP Request failed: {e}")

    async def _cleanup_test_trigger(self, trigger_id: int) -> bool:
        """Clean up test trigger from both cache and scheduler."""
        try:
            # First clean up from cache
            test_triggers = await cache_client.get("test_triggers")
            self._logger.debug(f"Fetched test_triggers: {test_triggers}")
            if test_triggers:
                if isinstance(test_triggers, bytes):
                    test_triggers = test_triggers.decode('utf-8')
                triggers_list = json.loads(test_triggers)
                self._logger.debug(f"Decoded test_triggers: {triggers_list}")
                triggers_list = [t for t in triggers_list if t['id'] != trigger_id]
                await cache_client.set("test_triggers", json.dumps(triggers_list))
                self._logger.debug(f"Updated test_triggers: {triggers_list}")
            
            await cache_client.delete(f"test_trigger:{trigger_id}")
            self._logger.debug(f"Deleted cache entry for test_trigger:{trigger_id}")
            self.remove_trigger(trigger_id)
            # Then clean up from scheduler
            return True
        except Exception as e:
            self._logger.error(f"Failed to clean up test trigger {trigger_id}: {e}")
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
                    is_test=test
                )
                
                db.add(event_log)
                db.commit()
                
                log_method = self._logger.debug if test else self._logger.info
                log_method(f"{'Test ' if test else ''}Trigger {trigger.id} executed")

                if test:
                    await self._cleanup_test_trigger(trigger.id)
                
        except Exception as e:
            log_method = self._logger.warning if test else self._logger.error
            log_method(f"{'Test ' if test else ''}Trigger {trigger.id} failed: {e}")

    def remove_trigger(self, trigger_id: int):
        """Remove a scheduled trigger."""
        if trigger_id in self.active_jobs:
            job = self.active_jobs[trigger_id]['job']
            job.remove()
            del self.active_jobs[trigger_id]
            self._logger.info(f"Trigger {trigger_id} removed")

    def remove_old_logs(self):
        """Remove event logs older than 48 hours."""
        with SessionLocal() as db:
            db.query(EventLog).filter(
                EventLog.triggered_at < datetime.utcnow() - timedelta(hours=48)
            ).delete()
            db.commit()
        self._logger.info("Old logs removed")

    async def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.scheduler.add_job(
                self.remove_old_logs, 
                trigger=CronTrigger.from_crontab("*/5 * * * *")
            )
            
            with SessionLocal() as db:
                to_schedule = db.query(Trigger).all()
                for trigger in to_schedule:
                    await self.add_trigger(trigger)
            
            self._logger.info("Added older triggers and Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self._logger.info("Scheduler shutdown")

# Global scheduler instance
scheduler = TriggerScheduler.get_instance()

def initialize_scheduler():
    """Initialize and start the scheduler."""
    asyncio.create_task(scheduler.start())

def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()

# Simplified logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)