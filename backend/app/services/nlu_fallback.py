"""
Deterministic fallback for the customer chat when no XAI_API_KEY is set.

Much simpler than it used to be: since chat no longer handles booking (that
moved to the calendar UI), there's no multi-turn state machine to maintain
here anymore — just single-turn keyword routing to the same lookups the
Grok agent's tools would call, ending with a RAG search as the catch-all.
"""
from __future__ import annotations

import re

from dateutil import parser as dateparser
from sqlalchemy.orm import Session

from app.models.booking import Service
from app.models.business import Review
from app.services import business_settings as biz
from app.services import rag, scheduler

HOURS_TRIGGER = re.compile(r"\bhour|open|close|when.*(open|closed)\b", re.IGNORECASE)
REVIEW_TRIGGER = re.compile(r"\breview|rating|feedback|what.*(people|customers).*(say|think)\b", re.IGNORECASE)
AVAILABILITY_TRIGGER = re.compile(r"\bavailab|slot|free|open time|when can\b", re.IGNORECASE)
SERVICES_TRIGGER = re.compile(r"\bservice|offer|what do you do|price|cost\b", re.IGNORECASE)


def _find_service(db: Session, text: str) -> Service | None:
    services = db.query(Service).filter(Service.active == True).all()  # noqa: E712
    text_low = text.lower()
    text_words = set(re.findall(r"[a-z']+", text_low))
    for s in services:
        if s.name.lower() in text_low:
            return s
    best, best_overlap = None, 0
    for s in services:
        words = {w for w in re.findall(r"[a-z']+", s.name.lower()) if len(w) > 3}
        overlap = len(words & text_words)
        if overlap > best_overlap:
            best, best_overlap = s, overlap
    return best


def _hours_reply(db: Session) -> str:
    s = biz.get_settings(db)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    days = ", ".join(day_names[d] for d in (s.open_days or []))
    return f"{s.business_name} is open {s.open_hour}:00–{s.close_hour}:00 on {days}."


def _reviews_reply(db: Session) -> str:
    reviews = db.query(Review).order_by(Review.created_at.desc()).limit(3).all()
    if not reviews:
        return "We don't have any reviews yet."
    avg = sum(r.rating for r in db.query(Review).all()) / db.query(Review).count()
    lines = [f"Average rating: {avg:.1f}/5 stars."]
    for r in reviews:
        lines.append(f'"{r.comment}" — {r.customer_name} ({r.rating}★)')
    return "\n".join(lines)


def _services_reply(db: Session) -> str:
    services = db.query(Service).filter(Service.active == True).all()  # noqa: E712
    if not services:
        return "We don't have any services listed right now."
    return "\n".join(f"{s.name}: {s.duration_minutes} min, ${s.price}" for s in services)


def _availability_reply(db: Session, text: str) -> str:
    service = _find_service(db, text)
    if not service:
        return "Which service would you like to check? " + _services_reply(db)
    try:
        day = dateparser.parse(text, fuzzy=True)
    except (ValueError, OverflowError):
        day = None
    if not day:
        return f"What date would you like to check for {service.name}?"
    slots = scheduler.get_available_slots(db, service, day)
    open_times = [s.start.strftime("%H:%M") for s in slots if s.available]
    if not open_times:
        return f"No open slots for {service.name} on {day.strftime('%b %d')}. Try another day on the booking calendar."
    return f"Open times for {service.name} on {day.strftime('%b %d')}: {', '.join(open_times)}. Book any of these on the calendar."


def fallback_reply(db: Session, user_text: str) -> str:
    if AVAILABILITY_TRIGGER.search(user_text):
        return _availability_reply(db, user_text)
    if HOURS_TRIGGER.search(user_text):
        return _hours_reply(db)
    if REVIEW_TRIGGER.search(user_text):
        return _reviews_reply(db)
    if SERVICES_TRIGGER.search(user_text):
        return _services_reply(db)

    chunks = rag.retrieve(user_text, k=2)
    if chunks:
        snippet = chunks[0]["text"].strip()
        if len(snippet) > 400:
            snippet = snippet[:400].rsplit(" ", 1)[0] + "..."
        return snippet

    return (
        "I can tell you about our services, hours, availability, or reviews — "
        "or you can book directly on the calendar above. What would you like to know?"
    )
