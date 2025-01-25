import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Trigger
from app.schemas import TriggerCreate, TriggerUpdate, TriggerResponse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.trigger_scheduler import scheduler 
from app.cache import cache_client
from json import dumps, loads
from typing import Optional
import uuid
import random

logger = logging.getLogger(__name__)

router = APIRouter()

def generate_test_id() -> int:
    return -random.randint(1,100)

def serialize_trigger(trigger: Trigger, test_id: Optional[int] = None) -> dict:
    return {
        "id": test_id or generate_test_id(),
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "schedule": trigger.schedule.isoformat() if trigger.schedule else None,
        "interval_seconds": trigger.interval_seconds,
        "is_recurring": trigger.is_recurring,
        "payload": trigger.payload,
        "created_at": datetime.utcnow().isoformat()
    }

@router.post("/", response_model=TriggerResponse)
async def create_trigger(trigger: TriggerCreate, db: Session = Depends(get_db)):
    try:
        # Create a new Trigger instance
        new_trigger = Trigger(
            name=trigger.name,
            trigger_type=trigger.trigger_type,
            schedule=trigger.schedule,
            interval_seconds=trigger.interval_seconds,
            is_recurring=trigger.is_recurring,
            payload=trigger.payload,
        )
        
        # Validate the trigger
        try:
            new_trigger.validate_trigger()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Add and commit the trigger to the database
        db.add(new_trigger)
        db.commit()
        db.refresh(new_trigger)
        try:
            await scheduler.add_trigger(new_trigger)
        except ValueError as e:
            raise HTTPException(status_code=501, detail=str(e))
        return new_trigger
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating trigger")

@router.post("/test/", response_model=TriggerResponse)
async def test_trigger(trigger: TriggerCreate, db: Session = Depends(get_db)):
    try:
        new_trigger = Trigger(
            name=trigger.name,
            trigger_type=trigger.trigger_type, 
            schedule=trigger.schedule,
            interval_seconds=trigger.interval_seconds,
            is_recurring=trigger.is_recurring,
            payload=trigger.payload,
        )
        
        try:
            new_trigger.validate_trigger()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        try:
            test_id = generate_test_id()

            new_trigger.id = test_id
            await scheduler.add_trigger(new_trigger, test=True)
            
            # Cache test trigger
            trigger_data = serialize_trigger(new_trigger, test_id)
            
            # Get existing test triggers
            cached_triggers = await cache_client.get("test_triggers")
            test_triggers = loads(cached_triggers) if cached_triggers else []
            test_triggers.append(trigger_data)
            
            # Update cache with 1 hour expiration
            await cache_client.set("test_triggers", dumps(test_triggers), expire=3600)
            
            # Set individual trigger cache
            await cache_client.set(f"test_trigger:{test_id}", dumps(trigger_data), expire=3600)
            
            
            return new_trigger
            
        except ValueError as e:
            raise HTTPException(status_code=501, detail=str(e))
            
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error creating trigger")

@router.get("/test/", response_model=list[TriggerResponse])
async def get_test_triggers():
    """Get all test triggers from cache"""
    try:
        test_triggers = await cache_client.get("test_triggers")
        if not test_triggers:
            return []
        
        # Handle bytes/string conversion
        if isinstance(test_triggers, bytes):
            test_triggers = test_triggers.decode('utf-8')
            
        return loads(test_triggers)
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Error deserializing test triggers: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting test triggers: {str(e)}")
        return []

@router.get("/", response_model=list[TriggerResponse])
def get_all_triggers(db: Session = Depends(get_db)):
    """
    Fetch all triggers.
    """
    return db.query(Trigger).all()

@router.get("/{trigger_id}", response_model=TriggerResponse)
def get_trigger(trigger_id: int, db: Session = Depends(get_db)):
    """
    Fetch a specific trigger by ID.
    """
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return trigger

@router.put("/{trigger_id}", response_model=TriggerResponse)
def update_trigger(trigger_id: int, trigger: TriggerUpdate, db: Session = Depends(get_db)):
    """
    Update a trigger by ID.
    """
    existing_trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not existing_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    for key, value in trigger.dict(exclude_unset=True).items():
        setattr(existing_trigger, key, value)
    
    # Update the updated_at timestamp
    existing_trigger.updated_at = datetime.utcnow()
    try:
        existing_trigger.validate_trigger()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    scheduler.remove_trigger(trigger_id)

# Add updated trigger back to scheduler
    scheduler.add_trigger(existing_trigger)
    db.commit()
    db.refresh(existing_trigger)
    return existing_trigger

@router.delete("/{trigger_id}")
def delete_trigger(trigger_id: int, db: Session = Depends(get_db)):
    """
    Delete a trigger by ID.
    
    First removes the trigger from the scheduler,
    then deletes it from the database.
    """
    # Find the trigger in the database
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    try:
        # Remove from scheduler first
        scheduler_removal_result = scheduler.remove_trigger(trigger_id)
        
        # Remove from database
        db.delete(trigger)
        db.commit()
        
        # Log the result
        if not scheduler_removal_result:
            return {"detail": "Trigger deleted successfully from scheduler and database"}
        else:
            # Trigger not found in scheduler, but still deleted from database
            return {"detail": "Trigger deleted from database (not found in scheduler)"}
    
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting trigger from database")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")