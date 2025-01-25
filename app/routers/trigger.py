from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Trigger
from app.schemas import TriggerCreate, TriggerUpdate, TriggerResponse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.trigger_scheduler import scheduler 

router = APIRouter()

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
def test_trigger(trigger: TriggerCreate, db: Session = Depends(get_db)):
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
        
        try:
            scheduler.add_trigger(new_trigger,test=True)
        except ValueError as e:
            raise HTTPException(status_code=501, detail=str(e))
        return new_trigger
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error creating trigger")


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