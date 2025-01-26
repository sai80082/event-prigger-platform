from datetime import datetime
from json import dumps, loads
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from json import loads

from app.models import Trigger
from app.schemas import TriggerCreate
from app.utils.trigger import generate_test_id, serialize_trigger
from app.services.trigger_scheduler import scheduler
from app.services.cache import cache_client


def get_all_triggers(db: Session):
    return db.query(Trigger).all()


def get_trigger_by_id(db: Session, trigger_id: int):
    return db.query(Trigger).filter(Trigger.id == trigger_id).first()


async def create_trigger_in_db(trigger: TriggerCreate, db: Session) -> Trigger:
    try:
        new_trigger = Trigger(
            name=trigger.name,
            trigger_type=trigger.trigger_type,
            schedule=trigger.schedule,
            interval_seconds=trigger.interval_seconds,
            is_recurring=trigger.is_recurring,
            payload=trigger.payload,
        )
        new_trigger.validate_trigger()
        db.add(new_trigger)
        db.commit()
        db.refresh(new_trigger)
        await scheduler.add_trigger(new_trigger)
        return new_trigger
    except SQLAlchemyError as e:
        db.rollback()
        raise e


async def update_trigger(db: Session, trigger_id: int, trigger_data: dict):
    existing_trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not existing_trigger:
        return None
    for key, value in trigger_data.items():
        setattr(existing_trigger, key, value)
    existing_trigger.updated_at = datetime.utcnow()
    existing_trigger.validate_trigger()
    scheduler.remove_trigger(trigger_id)

    await scheduler.add_trigger(existing_trigger)

    db.commit()
    db.refresh(existing_trigger)
    return existing_trigger


async def delete_trigger_from_db(db: Session, trigger_id: int):
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not trigger:
        return None
    try:
        db.delete(trigger)
        db.commit()
        scheduler.remove_trigger(trigger_id)
        return trigger
    except SQLAlchemyError:
        db.rollback()
        raise


async def update_trigger_in_db(db: Session, trigger_id: int, trigger_data: dict):
    try:
        existing_trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not existing_trigger:
            return None

        for key, value in trigger_data.items():
            setattr(existing_trigger, key, value)

        existing_trigger.updated_at = datetime.utcnow()
        existing_trigger.validate_trigger()

        db.commit()
        db.refresh(existing_trigger)
        scheduler.remove_trigger(trigger_id)
        await scheduler.add_trigger(existing_trigger)
        return existing_trigger
    except SQLAlchemyError:
        db.rollback()
        raise


async def create_test_trigger(trigger_data: TriggerCreate):
    # Create trigger object
    new_trigger = Trigger(
        name=trigger_data.name,
        trigger_type=trigger_data.trigger_type,
        schedule=trigger_data.schedule,
        interval_seconds=trigger_data.interval_seconds,
        is_recurring=trigger_data.is_recurring,
        payload=trigger_data.payload,
    )
    new_trigger.validate_trigger()
    test_id = generate_test_id()
    new_trigger.id = test_id

    # Serialize trigger before adding to scheduler
    trigger_data = serialize_trigger(new_trigger, new_trigger.id)

    # Initialize cache if empty
    cached_triggers = await fetch_cached_triggers()
    test_triggers = []
    if cached_triggers:
        if isinstance(cached_triggers, bytes):
            cached_triggers = cached_triggers.decode("utf-8")
        test_triggers = json.loads(cached_triggers)

    # Add to cache
    test_triggers.append(trigger_data)
    await cache_client.set("test_triggers", json.dumps(test_triggers), expire=3600)
    await cache_client.set(
        f"test_trigger:{new_trigger.id}", json.dumps(trigger_data), expire=3600
    )

    # Add to scheduler after caching
    await scheduler.add_trigger(new_trigger, test=True)

    return new_trigger


async def fetch_cached_triggers():
    """Fetch test triggers from cache with proper error handling"""
    try:
        cached_triggers = await cache_client.get("test_triggers")
        if cached_triggers is None:
            return json.dumps([])  # Return empty array if no cached triggers
        return cached_triggers
    except Exception as e:
        logging.error(f"Error fetching cached triggers: {e}")
        return json.dumps([])


def deserialize_triggers(cached_triggers):
    """Deserialize cached triggers"""
    try:
        if isinstance(cached_triggers, bytes):
            cached_triggers = cached_triggers.decode("utf-8")
        return loads(cached_triggers) if cached_triggers else []
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        return []
