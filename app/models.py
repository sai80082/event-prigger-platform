import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from app.services.db import Base
import datetime


class Trigger(Base):
    __tablename__ = "triggers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    trigger_type = Column(String, nullable=False)
    schedule = Column(DateTime, nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    is_recurring = Column(Boolean, default=False)
    payload = Column(String, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    def validate_trigger(self):

        if self.trigger_type not in ["scheduled", "api"]:
            raise ValueError("Trigger type must be either 'scheduled' or 'api'.")
        if self.trigger_type == "scheduled":
            if self.is_recurring and not self.interval_seconds:
                raise ValueError(
                    "Recurring triggers must have 'interval_seconds' defined."
                )
            if not self.is_recurring and not self.schedule:
                raise ValueError(
                    "Scheduled triggers must have 'schedule' or recurring enabled."
                )
            if self.is_recurring and self.schedule:
                raise ValueError(
                    "Scheduled triggers must have only one 'schedule' or recurring enabled."
                )
            if self.schedule:
                now = datetime.datetime.now(datetime.timezone.utc)
                if self.schedule <= now:
                    raise ValueError("Scheduled time must be in the future.")
        if self.trigger_type == "api":
            if self.payload:
                try:
                    json.loads(self.payload)
                except json.JSONDecodeError:
                    raise ValueError("Payload must be valid JSON.")
            if self.is_recurring or self.schedule:
                raise ValueError(
                    "API triggers must not have 'schedule' or recurring enabled."
                )


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id"))
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
    trigger_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    payload = Column(String, nullable=True)
    is_test = Column(Boolean, default=False)
