import random

from app.models import Trigger
from typing import Optional
from datetime import datetime


def generate_test_id() -> int:
    return -random.randint(1, 100)


def serialize_trigger(trigger: Trigger, test_id: Optional[int] = None) -> dict:
    return {
        "id": test_id or generate_test_id(),
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "schedule": trigger.schedule.isoformat() if trigger.schedule else None,
        "interval_seconds": trigger.interval_seconds,
        "is_recurring": trigger.is_recurring,
        "payload": trigger.payload,
        "created_at": datetime.utcnow().isoformat(),
    }
