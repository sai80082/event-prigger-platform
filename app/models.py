import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db import Base
import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db import Base
import datetime

class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    trigger_type = Column(String, nullable=False)  # "scheduled" or "api"
    
    # For scheduled triggers
    schedule = Column(DateTime, nullable=True)  # Specific date/time for one-time trigger
    interval_seconds = Column(Integer, nullable=True)  # Interval in seconds for recurring
    is_recurring = Column(Boolean, default=False)  # Indicates if it is a recurring trigger
    payload = Column(String, nullable=False,default="{}")  # Payload for API triggers
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    def validate_trigger(self):
        # Validate trigger type
        if self.trigger_type not in ["scheduled", "api"]:
            raise ValueError("Trigger type must be either 'scheduled' or 'api'.")
        
        # Validation for scheduled triggers
        if self.trigger_type == "scheduled":
            # Check if it's recurring
            if self.is_recurring and not self.interval_seconds:
                raise ValueError("Recurring triggers must have 'interval_seconds' defined.")
            
            # Check schedule if it exists
            if self.schedule:
                now = datetime.datetime.now(datetime.timezone.utc)
                if self.schedule <= now:
                    raise ValueError("Scheduled time must be in the future.")
        
        # Validation for API triggers
        if self.trigger_type == "api":
            # Validate JSON payload
            if self.payload:
                try:
                    json.loads(self.payload)
                except json.JSONDecodeError:
                    raise ValueError("Payload must be valid JSON.")
            
            # Ensure no schedule for recurring API triggers
            if self.is_recurring and self.schedule:
                raise ValueError("Recurring triggers should not have a fixed 'schedule'.")

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db import Base
import datetime

class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id"))
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
    trigger_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    payload = Column(String, nullable=True)  # Stores payload for API triggers
    is_test = Column(Boolean, default=False)
