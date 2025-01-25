from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pymemcache.client.base import Client
from app.db import get_db
from app.models import EventLog
from app.schemas import EventLogResponse
import datetime
import json

router = APIRouter()

# Memcached client
cache_client = Client(('localhost', 11211))

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
    Serialize logs to JSON for caching.
    """
    return json.dumps([log.dict() for log in logs])

def deserialize_logs(cached_data):
    """
    Deserialize logs from cached JSON data.
    """
    return [EventLogResponse(**log) for log in json.loads(cached_data)]

@router.get("/", response_model=list[EventLogResponse])
def get_recent_logs(db: Session = Depends(get_db)):
    """
    Fetch event logs from the last 2 hours with caching.
    """
    cache_key = cache_key_for_recent_logs()
    cached_logs = cache_client.get(cache_key)

    if cached_logs:
        # If cached data is found, deserialize and return it
        return deserialize_logs(cached_logs)

    # If no cache, query the database
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    logs = db.query(EventLog).filter(EventLog.triggered_at >= two_hours_ago).all()
    response_logs = [EventLogResponse.from_orm(log) for log in logs]

    # Cache the result for 5 minutes
    cache_client.set(cache_key, serialize_logs(response_logs), expire=300)

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
