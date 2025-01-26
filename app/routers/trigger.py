from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.crud.trigger import (
    create_test_trigger,
    create_trigger_in_db,
    delete_trigger_from_db,
    deserialize_triggers,
    fetch_cached_triggers,
    get_all_triggers,
    get_trigger_by_id,
    update_trigger_in_db,
)
from app.services.db import get_db
from app.schemas import TriggerCreate, TriggerUpdate, TriggerResponse
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()


@router.post("/", response_model=TriggerResponse)
async def create_trigger_view(trigger: TriggerCreate, db: Session = Depends(get_db)):
    try:
        new_trigger = await create_trigger_in_db(trigger, db)
        return new_trigger
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error creating trigger")
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.post("/test/", response_model=TriggerResponse)
async def test_trigger(trigger: TriggerCreate):
    try:
        new_trigger = await create_test_trigger(trigger)
        return new_trigger
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/", response_model=list[TriggerResponse])
async def get_test_triggers():
    try:
        cached_triggers = await fetch_cached_triggers()
        return deserialize_triggers(cached_triggers)
    except Exception as e:
        return []


@router.get("/", response_model=list[TriggerResponse])
def get_triggers(db: Session = Depends(get_db)):
    return get_all_triggers(db)


@router.get("/{trigger_id}", response_model=TriggerResponse)
def get_trigger_id(trigger_id: int, db: Session = Depends(get_db)):
    trigger = get_trigger_by_id(db, trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return trigger


@router.put("/{trigger_id}", response_model=TriggerResponse)
async def update_trigger(
    trigger_id: int, trigger: TriggerUpdate, db: Session = Depends(get_db)
):
    try:
        updated_trigger = await update_trigger_in_db(
            db, trigger_id, trigger.dict(exclude_unset=True)
        )
        if not updated_trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        return updated_trigger
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update trigger: {str(e)}"
        )


@router.delete("/{trigger_id}")
async def delete_trigger(trigger_id: int, db: Session = Depends(get_db)):
    try:
        deleted_trigger = await delete_trigger_from_db(db, trigger_id)
        if not deleted_trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        return {"detail": "Trigger deleted successfully"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error deleting trigger")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
