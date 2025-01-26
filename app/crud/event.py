import logging
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import EventLog
from app.services.cache import cache_client
from app.utils.eventlogs import deserialize_logs, serialize_logs
import datetime

logger = logging.getLogger(__name__)


async def get_recent_logs(db: Session, hours: int = 2):
    cache_key = "recent_logs"

    try:
        cached_logs = await cache_client.get(cache_key)
        if cached_logs:
            return deserialize_logs(cached_logs)
    except Exception as e:
        logger.warning(f"Cache read failed: {str(e)}")

    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    logs = db.query(EventLog).filter(EventLog.triggered_at >= two_hours_ago).all()

    try:
        await cache_client.set(cache_key, serialize_logs(logs), expire=10)
    except Exception as e:
        logger.warning(f"Cache write failed: {str(e)}")

    return logs


async def get_archived_logs(db: Session, hours: int = 2):
    cache_key = "archived_logs"

    try:
        cached_logs = await cache_client.get(cache_key)
        if cached_logs:
            return deserialize_logs(cached_logs)
    except Exception as e:
        logger.warning(f"Cache read failed: {str(e)}")

    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    logs = db.query(EventLog).filter(EventLog.triggered_at < two_hours_ago).all()

    try:
        await cache_client.set(cache_key, serialize_logs(logs), expire=600)
    except Exception as e:
        logger.warning(f"Cache write failed: {str(e)}")

    return logs


async def get_event_stats(db: Session):
    cache_key = "event-log-stats"

    try:
        cached_logs = await cache_client.get(cache_key)
        if cached_logs:
            return json.loads(cached_logs)
    except Exception as e:
        logger.warning(f"Cache read failed: {str(e)}")

    logs = (
        db.query(EventLog.name, func.count(EventLog.id).label("event_count"))
        .group_by(EventLog.name)
        .all()
    )
    response_logs = [{"name": log[0], "event_count": log[1]} for log in logs]
    try:
        await cache_client.set(cache_key, json.dumps(response_logs), expire=300)
    except Exception as e:
        logger.warning(f"Cache write failed: {str(e)}")

    return response_logs
