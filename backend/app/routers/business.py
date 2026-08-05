from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.booking import Appointment, Customer, Service
from app.models.business import Review
from app.schemas.schemas import (
    AppointmentOut,
    BusinessInfoOut,
    PublicBookingRequest,
    ReviewOut,
    UserLoginRequest,
    UserOut,
)
from app.services import business_settings as biz
from app.services import scheduler

router = APIRouter(prefix="/api", tags=["public"])


# ---- Business info (used by landing page + the informational chat) ----

@router.get("/business", response_model=BusinessInfoOut)
def get_business_info(db: Session = Depends(get_db)):
    settings = biz.get_settings(db)
    return settings


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(db: Session = Depends(get_db)):
    reviews = db.query(Review).order_by(Review.created_at.desc()).all()
    return [
        ReviewOut(
            id=r.id,
            customer_name=r.customer_name,
            rating=r.rating,
            comment=r.comment,
            service_name=r.service.name if r.service else None,
        )
        for r in reviews
    ]


# ---- Calendar-driven booking (the primary booking path — not chat) ----

@router.post("/book", response_model=AppointmentOut)
def book_appointment(payload: PublicBookingRequest, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Service not found")

    customer = db.query(Customer).filter(Customer.email == payload.customer_email).first()
    if not customer:
        customer = Customer(
            name=payload.customer_name, email=payload.customer_email, phone=payload.customer_phone
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    elif payload.customer_name and payload.customer_name != customer.name:
        customer.name = payload.customer_name
        db.commit()

    try:
        appt = scheduler.book_appointment(
            db,
            customer=customer,
            service=service,
            start_local=payload.start_time,
            created_via="calendar",
            notes=payload.notes,
        )
    except scheduler.SchedulingError as e:
        # 409 Conflict is the right status for "someone already took this
        # slot" — lets the frontend distinguish from validation errors (422)
        # and re-fetch availability to show the user what's actually open.
        raise HTTPException(status_code=409, detail={"code": e.code, "message": e.message})
    return appt


@router.patch("/book/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_own_appointment(appointment_id: str, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return scheduler.cancel_appointment(db, appt)


@router.patch("/book/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule_own_appointment(
    appointment_id: str, payload: PublicBookingRequest, db: Session = Depends(get_db)
):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        appt = scheduler.reschedule_appointment(db, appt, payload.start_time)
    except scheduler.SchedulingError as e:
        raise HTTPException(status_code=409, detail={"code": e.code, "message": e.message})
    return appt


# ---- Name-only user login ----
# Deliberately not a real auth system: no password, no JWT. This is meant
# to be a low-friction "who's booking" identity for personalization
# ("Hi Priya, welcome back") and for looking up someone's own appointments
# — not an access-control boundary. Real account security lives on the
# staff/admin side (JWT-protected), which is the side that actually needs it.

@router.post("/users/login", response_model=UserOut)
def user_login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    customer = None
    if payload.email:
        customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if customer:
        if payload.name and payload.name != customer.name:
            customer.name = payload.name
            db.commit()
        return UserOut(id=customer.id, name=customer.name, email=customer.email)

    # No email given (or no match): return a lightweight, non-persisted
    # identity for greeting purposes only. Their first real booking is what
    # creates a durable Customer record, keyed on the email they give then.
    return UserOut(id="guest", name=payload.name, email=payload.email or "")


@router.get("/users/appointments", response_model=list[AppointmentOut])
def list_user_appointments(email: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.email == email).first()
    if not customer:
        return []
    return sorted(customer.appointments, key=lambda a: a.start_time, reverse=True)
