from fastapi import APIRouter, Depends, HTTPException, logger
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EventLog
from app.schemas import EventLogResponse
import datetime
import json

from app.cache import cache_client
router = APIRouter()



def cache_key_for_recent_logs():
    """
    Generate a cache key for recent logs.
    """
    return "recent_logs"

def cache_key_for_archived_logs():
    """
    Generate a cache key for archived logs.
    """
    return "archived_logs"

def serialize_logs(logs):
    """
    Serialize logs to JSON for caching, handling datetime objects.
    """
    def custom_serializer(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()  # Convert datetime to ISO 8601 string
        raise TypeError(f"Type {type(obj)} not serializable")

    return json.dumps([log.dict() for log in logs], default=custom_serializer)


def deserialize_logs(cached_data):
    """
    Deserialize logs from cached JSON data.
    """
    return [EventLogResponse(**log) for log in json.loads(cached_data)]

@router.get("/", response_model=list[EventLogResponse])
async def get_recent_logs(db: Session = Depends(get_db)):
    """
    Fetch event logs from the last 2 hours with caching.
    """
    cache_key = cache_key_for_recent_logs()
    try:
        cached_logs = await cache_client.get(cache_key)
        if cached_logs:
            return deserialize_logs(cached_logs)
    except Exception as e:
        logger.warning(f"Cache read failed: {str(e)}")

    # Database fallback
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    logs = db.query(EventLog).filter(EventLog.triggered_at >= two_hours_ago).all()
    response_logs = [EventLogResponse.from_orm(log) for log in logs]

    # Try to cache but don't block if it fails
    try:
        await cache_client.set(cache_key, serialize_logs(response_logs), expire=300)
    except Exception as e:
        logger.warning(f"Cache write failed: {str(e)}")

    return response_logs

@router.get("/archived", response_model=list[EventLogResponse])
def get_archived_logs(db: Session = Depends(get_db)):
    """
    Fetch archived event logs (older than 2 hours) with caching.
    """
    cache_key = cache_key_for_archived_logs()
    cached_logs = cache_client.get(cache_key)

    if cached_logs:
        # If cached data is found, deserialize and return it
        return deserialize_logs(cached_logs)

    # If no cache, query the database
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    logs = db.query(EventLog).filter(EventLog.triggered_at < two_hours_ago).all()
    response_logs = [EventLogResponse.from_orm(log) for log in logs]

    # Cache the result for 10 minutes
    cache_client.set(cache_key, serialize_logs(response_logs), expire=600)

    return response_logs
