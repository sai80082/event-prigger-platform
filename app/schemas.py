from pydantic import BaseModel
from typing import Optional
from datetime import datetime
class TriggerBase(BaseModel):
    name: str
    trigger_type: str  # "scheduled" or "api"
    payload: Optional[str] = None
    schedule: Optional[datetime] = None
    is_recurring: Optional[bool] = False
    interval_seconds: Optional[int] = None

class TriggerCreate(TriggerBase):
    pass

class TriggerUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    payload: Optional[str] = None
    schedule: Optional[str] = None
    is_recurring: Optional[bool] = None

class TriggerResponse(TriggerBase):
    id: int

    class Config:
        orm_mode = True


from pydantic import BaseModel
from datetime import datetime

class EventLogResponse(BaseModel):
    id: int
    trigger_id: int
    name: str
    trigger_type: str
    triggered_at: datetime
    payload: str
    is_test: bool

    class Config:
        orm_mode = True
