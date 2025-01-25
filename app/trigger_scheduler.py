import asyncio
import logging
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

from app.db import get_db
from app.models import EventLog
from app.schemas import TriggerCreate

class TriggerScheduler:
    """Advanced scheduler for managing and executing triggers."""
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
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
            if trigger.trigger_type == 'scheduled':
                job_trigger = (IntervalTrigger(seconds=trigger.interval_seconds) 
                               if trigger.is_recurring 
                               else CronTrigger.from_crontab(trigger.schedule))
            elif trigger.trigger_type == 'api':
                await self._handle_http_request(trigger.payload, test)
                return
            
            # Schedule the job
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
            self._logger.error(f"Trigger scheduling failed: {e}")
        
    async def _handle_http_request(self, payload, test):
        """Handle HTTP request payload."""
        import aiohttp
        
        url = payload.get('url')
        method = payload.get('method', 'GET')
        headers = payload.get('headers', {})
        data = payload.get('data')
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=data) as response:
                self._logger.info(f"HTTP Request to {url} completed with status {response.status}")

    async def _execute_trigger(self, trigger: TriggerCreate, test: bool = False):
        """Execute the trigger's payload."""
        try:
            db = next(get_db())
            event_log = EventLog(
                trigger_id=trigger.id,
                trigger_type=trigger.trigger_type,
                name=trigger.name,
                payload=trigger.payload,
                is_test=test
            )
            
            db.add(event_log)
            db.commit()
            
            # Simplified logging
            log_method = self._logger.debug if test else self._logger.info
            log_method(f"{'Test ' if test else ''}Trigger {trigger.id} executed")
        except Exception as e:
            # Simplified error logging
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
        db = next(get_db())
        db.query(EventLog).filter(
            EventLog.triggered_at < datetime.utcnow() - timedelta(hours=48)
        ).delete()
        db.commit()
        self._logger.info("Old logs removed")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.scheduler.add_job(
                self.remove_old_logs, 
                trigger=CronTrigger.from_crontab("*/5 * * * *")
            )
            self._logger.info("Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self._logger.info("Scheduler shutdown")

# Global scheduler instance
scheduler = TriggerScheduler()

def initialize_scheduler():
    """Initialize and start the scheduler."""
    scheduler.start()

def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()

# Simplified logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)