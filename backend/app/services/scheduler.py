"""
Scheduling engine: the single source of truth for "is this slot bookable".

Kept deliberately independent of the AI layer — the LLM only ever *proposes*
a booking; this module is what actually accepts or rejects it. That
separation matters for correctness (an LLM should never be the last line of
defense against double-booking) and it's a good thing to call out explicitly
in an interview: the AI is a UX layer over a deterministic system, not a
replacement for one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytz
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.booking import Appointment, AppointmentStatus, Service
from app.services import business_settings as biz

settings = get_settings()
TZ = pytz.timezone(settings.business_timezone)


class SchedulingError(Exception):
    """Base class for all booking-rejection reasons. The `code` field lets
    the API and the chat layer give the user a precise, actionable reason
    instead of a generic 'something went wrong'."""

    code: str = "scheduling_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class OutsideBusinessHoursError(SchedulingError):
    code = "outside_business_hours"


class InThePastError(SchedulingError):
    code = "in_the_past"


class TooFarInFutureError(SchedulingError):
    code = "too_far_in_future"


class SlotConflictError(SchedulingError):
    code = "slot_conflict"


class ServiceNotFoundError(SchedulingError):
    code = "service_not_found"


@dataclass
class Slot:
    start: datetime  # timezone-aware, business timezone
    end: datetime
    available: bool


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = TZ.localize(dt)
    return dt.astimezone(pytz.utc).replace(tzinfo=None)


def validate_business_rules(
    db: Session, start_local: datetime, now_local: datetime | None = None
) -> None:
    """Raises a SchedulingError subclass if the requested start time breaks
    a business rule. Hours/open-days are read from BusinessSettings (staff-
    editable, live) rather than static config, so a staff member changing
    hours via the setup assistant takes effect immediately for every
    booking check without a restart."""
    now_local = now_local or datetime.now(TZ)
    biz_settings = biz.get_settings(db)

    if start_local < now_local:
        raise InThePastError("That time has already passed.")

    if start_local > now_local + timedelta(days=settings.booking_horizon_days):
        raise TooFarInFutureError(
            f"We only take bookings up to {settings.booking_horizon_days} days ahead."
        )

    if start_local.weekday() not in (biz_settings.open_days or []):
        raise OutsideBusinessHoursError("We're closed that day.")

    open_time = start_local.replace(
        hour=biz_settings.open_hour, minute=0, second=0, microsecond=0
    )
    close_time = start_local.replace(
        hour=biz_settings.close_hour, minute=0, second=0, microsecond=0
    )
    if start_local < open_time or start_local >= close_time:
        raise OutsideBusinessHoursError(
            f"We're open {biz_settings.open_hour}:00–{biz_settings.close_hour}:00 on our open days."
        )


def find_conflict(
    db: Session, start_utc: datetime, end_utc: datetime, exclude_appointment_id: str | None = None
) -> Appointment | None:
    """Returns the conflicting appointment, if any. Overlap test:
    existing.start < new.end AND existing.end > new.start."""
    stmt = select(Appointment).where(
        and_(
            Appointment.status == AppointmentStatus.confirmed,
            Appointment.start_time < end_utc,
            Appointment.end_time > start_utc,
        )
    )
    if exclude_appointment_id:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    return db.execute(stmt).scalars().first()


def book_appointment(
    db: Session,
    *,
    customer,
    service: Service,
    start_local: datetime,
    created_via: str = "chat",
    notes: str = "",
) -> Appointment:
    """The one function that actually writes an appointment. Everything else
    (chat tool handler, admin API) funnels through this."""
    if start_local.tzinfo is None:
        start_local = TZ.localize(start_local)

    validate_business_rules(db, start_local)

    start_utc = _to_utc(start_local)
    end_utc = start_utc + timedelta(minutes=service.duration_minutes)

    conflict = find_conflict(db, start_utc, end_utc)
    if conflict:
        conflict_local = pytz.utc.localize(conflict.start_time).astimezone(TZ)
        raise SlotConflictError(
            f"That slot is already booked ({conflict_local.strftime('%-I:%M %p')} is taken)."
        )

    appt = Appointment(
        customer_id=customer.id,
        service_id=service.id,
        start_time=start_utc,
        end_time=end_utc,
        status=AppointmentStatus.confirmed,
        created_via=created_via,
        notes=notes,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def reschedule_appointment(
    db: Session, appointment: Appointment, new_start_local: datetime
) -> Appointment:
    if new_start_local.tzinfo is None:
        new_start_local = TZ.localize(new_start_local)

    validate_business_rules(db, new_start_local)

    service = appointment.service
    start_utc = _to_utc(new_start_local)
    end_utc = start_utc + timedelta(minutes=service.duration_minutes)

    conflict = find_conflict(db, start_utc, end_utc, exclude_appointment_id=appointment.id)
    if conflict:
        raise SlotConflictError("That new time is already booked.")

    appointment.start_time = start_utc
    appointment.end_time = end_utc
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(db: Session, appointment: Appointment) -> Appointment:
    appointment.status = AppointmentStatus.cancelled
    db.commit()
    db.refresh(appointment)
    return appointment


def get_available_slots(
    db: Session, service: Service, day_local: datetime
) -> list[Slot]:
    """Returns every slot for a given business day, marked available/not.
    Used by the customer-facing calendar, the admin calendar, and the chat
    assistant when it needs to describe availability."""
    if day_local.tzinfo is None:
        day_local = TZ.localize(day_local)

    biz_settings = biz.get_settings(db)
    day_start = day_local.replace(
        hour=biz_settings.open_hour, minute=0, second=0, microsecond=0
    )
    day_end = day_local.replace(
        hour=biz_settings.close_hour, minute=0, second=0, microsecond=0
    )

    slots: list[Slot] = []
    cursor = day_start
    step = timedelta(minutes=settings.slot_duration_minutes)

    # Pull all confirmed appointments for the day once, rather than querying
    # per-slot (N+1 avoidance).
    day_start_utc = _to_utc(day_start)
    day_end_utc = _to_utc(day_end)
    existing = db.execute(
        select(Appointment).where(
            and_(
                Appointment.status == AppointmentStatus.confirmed,
                Appointment.start_time < day_end_utc,
                Appointment.end_time > day_start_utc,
            )
        )
    ).scalars().all()

    while cursor + timedelta(minutes=service.duration_minutes) <= day_end:
        slot_start_utc = _to_utc(cursor)
        slot_end_utc = slot_start_utc + timedelta(minutes=service.duration_minutes)
        is_taken = any(
            e.start_time < slot_end_utc and e.end_time > slot_start_utc for e in existing
        )
        try:
            validate_business_rules(db, cursor)
            in_rules = True
        except SchedulingError:
            in_rules = False
        slots.append(Slot(start=cursor, end=cursor + step, available=in_rules and not is_taken))
        cursor += step

    return slots
