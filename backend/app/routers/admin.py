from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.booking import Appointment, AppointmentStatus, Customer, Service
from app.schemas.schemas import (
    AppointmentCreateAdmin,
    AppointmentOut,
    AppointmentReschedule,
    BusinessInfoOut,
    BusinessInfoUpdate,
    DashboardStats,
    ServiceCreate,
    ServiceOut,
    SetupChatRequest,
    SetupChatResponse,
)
from app.services import scheduler
from app.services import rag
from app.services import business_settings as biz
from app.services.setup_agent import run_setup_turn
from app.models.chat import ChatSession

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


# ---- Appointments ----

@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(
    status_filter: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Appointment)
    if status_filter:
        q = q.filter(Appointment.status == status_filter)
    if from_date:
        q = q.filter(Appointment.start_time >= from_date)
    if to_date:
        q = q.filter(Appointment.start_time <= to_date)
    return q.order_by(Appointment.start_time).all()


@router.post("/appointments", response_model=AppointmentOut)
def create_appointment(payload: AppointmentCreateAdmin, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    customer = db.query(Customer).filter(Customer.email == payload.customer_email).first()
    if not customer:
        customer = Customer(
            name=payload.customer_name, email=payload.customer_email, phone=payload.customer_phone
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    try:
        appt = scheduler.book_appointment(
            db,
            customer=customer,
            service=service,
            start_local=payload.start_time,
            created_via="admin",
            notes=payload.notes,
        )
    except scheduler.SchedulingError as e:
        raise HTTPException(status_code=409, detail={"code": e.code, "message": e.message})
    return appt


@router.patch("/appointments/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(appointment_id: str, payload: AppointmentReschedule, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        appt = scheduler.reschedule_appointment(db, appt, payload.new_start_time)
    except scheduler.SchedulingError as e:
        raise HTTPException(status_code=409, detail={"code": e.code, "message": e.message})
    return appt


@router.patch("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(appointment_id: str, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return scheduler.cancel_appointment(db, appt)


@router.patch("/appointments/{appointment_id}/complete", response_model=AppointmentOut)
def complete(appointment_id: str, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = AppointmentStatus.completed
    db.commit()
    db.refresh(appt)
    return appt


@router.patch("/appointments/{appointment_id}/no-show", response_model=AppointmentOut)
def mark_no_show(appointment_id: str, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = AppointmentStatus.no_show
    db.commit()
    db.refresh(appt)
    return appt


# ---- Services CRUD ----

@router.get("/services", response_model=list[ServiceOut])
def list_all_services(db: Session = Depends(get_db)):
    return db.query(Service).all()


@router.post("/services", response_model=ServiceOut)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
    service = Service(**payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.patch("/services/{service_id}/deactivate", response_model=ServiceOut)
def deactivate_service(service_id: str, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    service.active = False
    db.commit()
    db.refresh(service)
    return service


# ---- Analytics ----

@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    all_appts = db.query(Appointment).all()
    now = datetime.utcnow()
    today = now.date()

    upcoming = [a for a in all_appts if a.status == AppointmentStatus.confirmed and a.start_time >= now]
    cancelled = [a for a in all_appts if a.status == AppointmentStatus.cancelled]
    today_bookings = [a for a in all_appts if a.start_time.date() == today]

    hour_counter = Counter(a.start_time.hour for a in all_appts if a.status == AppointmentStatus.confirmed)
    busiest_hour = None
    if hour_counter:
        h = hour_counter.most_common(1)[0][0]
        busiest_hour = f"{h:02d}:00"

    by_day: Counter = Counter()
    by_service: Counter = Counter()
    for a in all_appts:
        if a.status != AppointmentStatus.cancelled:
            by_day[a.start_time.strftime("%Y-%m-%d")] += 1
            by_service[a.service.name] += 1

    return DashboardStats(
        total_appointments=len(all_appts),
        upcoming_appointments=len(upcoming),
        cancelled_appointments=len(cancelled),
        bookings_today=len(today_bookings),
        busiest_hour=busiest_hour,
        bookings_by_day=dict(by_day),
        bookings_by_service=dict(by_service),
    )


# ---- RAG / knowledge base ----

@router.get("/rag/status")
def rag_status():
    from app.core.config import get_settings
    from app.services.embeddings import embeddings_fingerprint

    settings = get_settings()
    docs = rag._load_source_documents()
    return {
        "backend": settings.vector_store_backend,
        "embedding_source": "openai" if settings.openai_api_key else "local-hashing",
        "embedding_fingerprint": embeddings_fingerprint(),
        "source_documents": [d.metadata["source"] for d in docs],
        "index_stale": rag._index_is_stale() if settings.vector_store_backend == "faiss" else None,
    }


@router.post("/rag/reindex")
def rag_reindex():
    n = rag.build_index(force=True)
    return {"ok": True, "chunks_indexed": n}


@router.get("/rag/search")
def rag_search(query: str, k: int = 4):
    """Lets an admin sanity-check retrieval quality directly, without going
    through the chat agent — useful when tuning the knowledge base."""
    return {"results": rag.retrieve(query, k=k)}


# ---- Business settings (manual form — reliable path alongside the chat) ----

@router.get("/business", response_model=BusinessInfoOut)
def get_business_settings(db: Session = Depends(get_db)):
    return biz.get_settings(db)


@router.patch("/business", response_model=BusinessInfoOut)
def update_business_settings(payload: BusinessInfoUpdate, db: Session = Depends(get_db)):
    fields = payload.model_dump(exclude_unset=True)
    return biz.update_settings(db, **fields)


# ---- Staff setup chat (conversational configuration) ----

@router.post("/setup-chat", response_model=SetupChatResponse)
def setup_chat(payload: SetupChatRequest, db: Session = Depends(get_db)):
    from app.core.config import get_settings as get_app_settings

    app_settings = get_app_settings()
    session = None
    if payload.session_id:
        session = db.get(ChatSession, payload.session_id)
    if session is None:
        session = ChatSession()
        db.add(session)
        db.commit()
        db.refresh(session)

    reply = run_setup_turn(db, session, payload.message)
    engine = "grok" if app_settings.xai_api_key else "fallback"
    return SetupChatResponse(session_id=session.id, reply=reply, engine=engine)
