from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.db import get_db
from app.schemas import EventLogResponse
from app.crud.event import get_recent_logs, get_archived_logs, get_event_stats

router = APIRouter()


@router.get("/", response_model=list[EventLogResponse])
async def list_recent_logs(db: Session = Depends(get_db)):
    """Fetch event logs from the last 2 hours."""
    logs = await get_recent_logs(db)
    return [EventLogResponse.from_orm(log) for log in logs]


@router.get("/archived", response_model=list[EventLogResponse])
async def list_archived_logs(db: Session = Depends(get_db)):
    """Fetch archived event logs."""
    logs = await get_archived_logs(db)
    return [EventLogResponse.from_orm(log) for log in logs]


@router.get("/stats")
async def list_event_stats(db: Session = Depends(get_db)):
    """Fetch event log statistics."""
    return await get_event_stats(db)
