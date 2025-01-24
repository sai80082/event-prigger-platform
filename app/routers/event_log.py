from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import EventLog
from app.schemas import EventLogResponse

router = APIRouter()

@router.get("/", response_model=list[EventLogResponse])
def get_recent_logs(db: Session = Depends(get_db)):
    """
    Fetch event logs from the last 2 hours.
    """
    import datetime
    from sqlalchemy import func
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    logs = db.query(EventLog).filter(EventLog.triggered_at >= two_hours_ago).all()
    return logs

@router.get("/archived", response_model=list[EventLogResponse])
def get_archived_logs(db: Session = Depends(get_db)):
    """
    Fetch archived event logs (older than 2 hours).
    """
    import datetime
    from sqlalchemy import func
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    logs = db.query(EventLog).filter(EventLog.triggered_at < two_hours_ago).all()
    return logs
