"""
The customer-facing chat assistant, via LangChain + Grok (xAI) + RAG.

Scope, deliberately narrowed: this assistant is informational only. It can
tell a customer about services, check what times are open, describe the
business (hours, address, policies), and surface reviews — but it cannot
create, change, or cancel a booking. Booking itself happens through the
calendar UI (see the public /api/book endpoint), which gives the customer
a real date picker with taken slots visibly greyed out, rather than
negotiating a time slot through prose. That split — chat for discovery,
calendar for the actual transaction — mirrors how the strongest booking
products (Fresha, Cal.com) separate "help me decide" from "lock in a time."

If XAI_API_KEY is not configured, nlu_fallback.py answers the same kinds of
questions with direct lookups (no LLM) instead of a multi-turn flow, since
there's no longer a multi-step booking transaction to walk through.
"""
from __future__ import annotations

import json
from datetime import datetime

from dateutil import parser as dateparser
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_xai import ChatXAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.booking import Customer, Service
from app.models.business import Review
from app.models.chat import ChatMessage, ChatSession
from app.services import business_settings as biz
from app.services import rag, scheduler
from app.services.nlu_fallback import fallback_reply

settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """You are Aria, the friendly assistant for {business_name}.

Today's date and time is {now} ({timezone}).

Your job is to help customers DECIDE what and when to book — not to book for them. Booking
itself happens on the website's calendar, not here.

You can:
- Describe services, pricing, and what to expect (use search_knowledge_base for policy/prep
  questions like cancellation policy, deposits, what to bring)
- Check what times are open for a service on a date (check_availability)
- Share what customers say (get_reviews)
- Describe the business itself — hours, address, phone (get_business_info)
- Look up a customer's own upcoming appointments by email (list_my_appointments) — read-only

If someone asks you to book, reschedule, or cancel something, tell them warmly to use the
calendar on the page (or their "My Appointments" section to reschedule/cancel) — you're here to
help them figure out what to pick, not to make the change yourself.

Keep replies short and conversational.
"""


def _services_block(db: Session) -> str:
    services = db.query(Service).filter(Service.active == True).all()  # noqa: E712
    if not services:
        return "(no services configured)"
    return "\n".join(
        f"- {s.name}: {s.duration_minutes} min, ${s.price} — {s.description}" for s in services
    )


def _find_service(db: Session, name: str) -> Service | None:
    if not name:
        return None
    services = db.query(Service).filter(Service.active == True).all()  # noqa: E712
    name_low = name.lower().strip()
    for s in services:
        if s.name.lower() == name_low:
            return s
    for s in services:
        if name_low in s.name.lower() or s.name.lower() in name_low:
            return s
    return None


def _do_list_services(db: Session) -> dict:
    services = db.query(Service).filter(Service.active == True).all()  # noqa: E712
    return {
        "ok": True,
        "services": [
            {"name": s.name, "duration_minutes": s.duration_minutes, "price": float(s.price), "description": s.description}
            for s in services
        ],
    }


def _do_check_availability(db: Session, service_name: str, date: str) -> dict:
    service = _find_service(db, service_name)
    if not service:
        return {"ok": False, "error": "unknown_service", "message": "I don't recognize that service."}
    day = dateparser.parse(date)
    slots = scheduler.get_available_slots(db, service, day)
    open_slots = [s.start.strftime("%H:%M") for s in slots if s.available]
    return {"ok": True, "date": date, "available_times": open_slots}


def _do_list_my_appointments(db: Session, customer_email: str) -> dict:
    customer = db.query(Customer).filter(Customer.email == customer_email).first()
    if not customer:
        return {"ok": True, "appointments": []}
    upcoming = [
        a for a in customer.appointments
        if a.status.value == "confirmed" and a.start_time >= datetime.utcnow()
    ]
    return {
        "ok": True,
        "appointments": [
            {"id": a.id, "service": a.service.name, "start": a.start_time.isoformat()}
            for a in sorted(upcoming, key=lambda a: a.start_time)
        ],
    }


def _do_get_reviews(db: Session) -> dict:
    reviews = db.query(Review).order_by(Review.created_at.desc()).limit(6).all()
    if not reviews:
        return {"ok": True, "reviews": [], "average_rating": None}
    avg = sum(r.rating for r in reviews) / len(reviews)
    return {
        "ok": True,
        "average_rating": round(avg, 1),
        "reviews": [
            {"customer_name": r.customer_name, "rating": r.rating, "comment": r.comment} for r in reviews
        ],
    }


def _do_get_business_info(db: Session) -> dict:
    s = biz.get_settings(db)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return {
        "ok": True,
        "business_name": s.business_name,
        "tagline": s.tagline,
        "description": s.description,
        "address": s.address,
        "phone": s.phone,
        "hours": f"{s.open_hour}:00–{s.close_hour}:00",
        "open_days": [day_names[d] for d in (s.open_days or [])],
    }


def _do_search_knowledge_base(query: str) -> str:
    return rag.format_context(rag.retrieve(query))


def build_tools(db: Session) -> list:
    @tool
    def list_services() -> dict:
        """List all bookable services with their duration and price."""
        return _do_list_services(db)

    @tool
    def check_availability(service_name: str, date: str) -> dict:
        """Check open time slots for a service on a date. date is ISO format, e.g. '2026-08-10'."""
        return _do_check_availability(db, service_name, date)

    @tool
    def list_my_appointments(customer_email: str) -> dict:
        """Look up a customer's own upcoming confirmed appointments by email. Read-only."""
        return _do_list_my_appointments(db, customer_email)

    @tool
    def get_reviews() -> dict:
        """Get recent customer reviews and the average rating."""
        return _do_get_reviews(db)

    @tool
    def get_business_info() -> dict:
        """Get the business's name, tagline, description, hours, address, and phone."""
        return _do_get_business_info(db)

    @tool
    def search_knowledge_base(query: str) -> str:
        """Search policy and service-prep documents (cancellation policy, deposits,
        what to bring, accessibility, etc). Use for any 'how does this work' question."""
        return _do_search_knowledge_base(query)

    return [
        list_services,
        check_availability,
        list_my_appointments,
        get_reviews,
        get_business_info,
        search_knowledge_base,
    ]


def _client() -> ChatXAI | None:
    if not settings.xai_api_key:
        return None
    return ChatXAI(model=settings.xai_model, api_key=settings.xai_api_key, base_url=settings.xai_base_url, max_tokens=1024)


def run_agent_turn(db: Session, session: ChatSession, user_text: str) -> str:
    """Runs one user turn and returns the assistant's reply text. Persists
    every message to the session's history. Purely informational — no
    booking side effects, by design (see module docstring)."""
    db.add(ChatMessage(session_id=session.id, role="user", content=user_text))
    db.commit()

    llm = _client()
    if llm is None:
        reply = fallback_reply(db, user_text)
        db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
        db.commit()
        return reply

    tools = build_tools(db)
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    business = biz.get_settings(db)
    now_local = datetime.now(scheduler.TZ)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        business_name=business.business_name,
        now=now_local.strftime("%A, %B %d %Y, %H:%M"),
        timezone=settings.business_timezone,
    )
    # Services list appended separately so it stays current across the loop
    system_prompt += f"\n\nCurrent services:\n{_services_block(db)}"

    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(
        ChatMessage.created_at
    ).all()
    messages = [SystemMessage(content=system_prompt)]
    for m in history:
        if m.role == "user" and m.content:
            messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant" and m.content:
            messages.append(AIMessage(content=m.content))

    for _ in range(5):
        ai_msg: AIMessage = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            final_text = (ai_msg.content or "").strip()
            db.add(ChatMessage(session_id=session.id, role="assistant", content=final_text))
            db.commit()
            return final_text

        for tc in ai_msg.tool_calls:
            tool_obj = tools_by_name.get(tc["name"])
            try:
                result = tool_obj.invoke(tc.get("args", {})) if tool_obj else {"ok": False, "error": "unknown_tool"}
            except Exception as e:
                result = {"ok": False, "error": "internal_error", "message": str(e)}
            result_str = result if isinstance(result, str) else json.dumps(result)
            db.add(
                ChatMessage(
                    session_id=session.id, role="tool", content=result_str,
                    tool_calls={"name": tc["name"], "input": tc.get("args", {})},
                )
            )
            messages.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))
        db.commit()

    fallback = "Sorry, I'm having trouble with that — could you try rephrasing?"
    db.add(ChatMessage(session_id=session.id, role="assistant", content=fallback))
    db.commit()
    return fallback
