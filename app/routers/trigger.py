from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Trigger
from app.schemas import TriggerCreate, TriggerUpdate, TriggerResponse
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

@router.post("/", response_model=TriggerResponse)
def create_trigger(trigger: TriggerCreate, db: Session = Depends(get_db)):
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
        return new_trigger
    except SQLAlchemyError:
        db.rollback()
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
    
    db.commit()
    db.refresh(existing_trigger)
    return existing_trigger

@router.delete("/{trigger_id}")
def delete_trigger(trigger_id: int, db: Session = Depends(get_db)):
    """
    Delete a trigger by ID.
    """
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    db.delete(trigger)
    db.commit()
    return {"detail": "Trigger deleted successfully"}
