from datetime import datetime

from dateutil import parser as dateparser
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.booking import Service
from app.schemas.schemas import AvailabilitySlot
from app.services import scheduler

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("", response_model=list[AvailabilitySlot])
def get_availability(
    service_id: str = Query(...),
    date: str = Query(..., description="ISO date, e.g. 2026-08-10"),
    db: Session = Depends(get_db),
):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    try:
        day = dateparser.parse(date)
    except (ValueError, OverflowError):
        raise HTTPException(status_code=400, detail="Invalid date")

    slots = scheduler.get_available_slots(db, service, day)
    return [
        AvailabilitySlot(start=s.start, end=s.end, available=s.available) for s in slots
    ]
