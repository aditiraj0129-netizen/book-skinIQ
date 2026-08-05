"""
The staff-only setup assistant: lets a business configure its operating
hours, identity, and service menu conversationally instead of filling out
forms one field at a time. Deliberately a separate agent from the
customer-facing one (ai_agent.py) — different tools, different system
prompt, different trust level (this one can change what the scheduler
enforces for everyone, so it's only reachable behind the admin JWT).

Like the customer agent, this has a deterministic fallback for when no
XAI_API_KEY is set — a single-turn regex parser rather than a multi-turn
slot-filling flow, since staff commands are naturally more atomic
("we're open 9 to 6, Monday to Saturday") than a customer booking
conversation.
"""
from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_xai import ChatXAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.booking import Service
from app.models.chat import ChatMessage, ChatSession
from app.services import business_settings as biz

settings = get_settings()

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

SYSTEM_PROMPT = """You are the setup assistant for a small business using the Bright Studio
booking platform. You're talking to STAFF, not customers — help them configure their business
in plain language instead of making them fill out forms.

You can:
- Update operating hours and which days are open
- Update the business name, tagline, description, address, phone
- Add, update, or deactivate services (name, duration, price, description)

Always confirm what you changed in a short sentence after calling a tool. If a request is
ambiguous (e.g. "we're open late on Fridays" with no specific hour), ask for the specific
number before calling a tool — never guess at operating hours, since that directly controls
what customers can book.
"""


def _do_get_settings(db: Session) -> dict:
    s = biz.get_settings(db)
    return {
        "business_name": s.business_name,
        "tagline": s.tagline,
        "description": s.description,
        "address": s.address,
        "phone": s.phone,
        "open_hour": s.open_hour,
        "close_hour": s.close_hour,
        "open_days": [DAY_NAMES[d] for d in (s.open_days or [])],
    }


def _parse_days(day_names: list[str]) -> list[int]:
    out = []
    for name in day_names:
        name_low = name.lower().strip()
        if name_low in DAY_NAMES:
            out.append(DAY_NAMES.index(name_low))
    return sorted(set(out))


def _do_update_hours(db: Session, open_hour: int, close_hour: int, open_days: list[str] | None) -> dict:
    if not (0 <= open_hour < 24 and 0 <= close_hour <= 24 and open_hour < close_hour):
        return {"ok": False, "error": "invalid_hours", "message": "Hours must be a valid 0-24 range with open before close."}
    fields = {"open_hour": open_hour, "close_hour": close_hour}
    if open_days:
        parsed = _parse_days(open_days)
        if parsed:
            fields["open_days"] = parsed
    s = biz.update_settings(db, **fields)
    return {"ok": True, "open_hour": s.open_hour, "close_hour": s.close_hour, "open_days": [DAY_NAMES[d] for d in s.open_days]}


def _do_update_info(db: Session, **fields) -> dict:
    clean = {k: v for k, v in fields.items() if v}
    s = biz.update_settings(db, **clean)
    return {"ok": True, "business_name": s.business_name, "tagline": s.tagline, "address": s.address, "phone": s.phone}


def _do_add_service(db: Session, name: str, duration_minutes: int, price: float, description: str = "") -> dict:
    existing = db.query(Service).filter(Service.name.ilike(name)).first()
    if existing:
        existing.duration_minutes = duration_minutes
        existing.price = price
        existing.description = description or existing.description
        existing.active = True
        db.commit()
        return {"ok": True, "updated": True, "name": existing.name}
    service = Service(name=name, duration_minutes=duration_minutes, price=price, description=description)
    db.add(service)
    db.commit()
    return {"ok": True, "created": True, "name": name}


def _do_deactivate_service(db: Session, name: str) -> dict:
    service = db.query(Service).filter(Service.name.ilike(name)).first()
    if not service:
        return {"ok": False, "error": "not_found", "message": f"No service called '{name}'."}
    service.active = False
    db.commit()
    return {"ok": True, "deactivated": service.name}


def build_tools(db: Session) -> list:
    @tool
    def get_business_settings() -> dict:
        """Get the current business name, hours, open days, and contact info."""
        return _do_get_settings(db)

    @tool
    def update_business_hours(open_hour: int, close_hour: int, open_days: list[str] | None = None) -> dict:
        """Set operating hours (24h, e.g. 9 and 18) and optionally which days are open
        (list of day names like ["monday", "tuesday"]). Omit open_days to leave days unchanged."""
        return _do_update_hours(db, open_hour, close_hour, open_days)

    @tool
    def update_business_info(
        business_name: str = "",
        tagline: str = "",
        description: str = "",
        address: str = "",
        phone: str = "",
    ) -> dict:
        """Update the business's name, tagline, description, address, or phone.
        Only non-empty fields are changed."""
        return _do_update_info(
            db,
            business_name=business_name,
            tagline=tagline,
            description=description,
            address=address,
            phone=phone,
        )

    @tool
    def add_or_update_service(name: str, duration_minutes: int, price: float, description: str = "") -> dict:
        """Add a new service, or update it if a service with that name already exists."""
        return _do_add_service(db, name, duration_minutes, price, description)

    @tool
    def deactivate_service(name: str) -> dict:
        """Remove a service from the bookable menu (customers can no longer book it)."""
        return _do_deactivate_service(db, name)

    return [
        get_business_settings,
        update_business_hours,
        update_business_info,
        add_or_update_service,
        deactivate_service,
    ]


def _client() -> ChatXAI | None:
    if not settings.xai_api_key:
        return None
    return ChatXAI(
        model=settings.xai_model,
        api_key=settings.xai_api_key,
        base_url=settings.xai_base_url,
        max_tokens=1024,
    )


# ---------------------------------------------------------------------------
# Fallback: single-turn regex parser for common setup commands
# ---------------------------------------------------------------------------

HOURS_RE = re.compile(
    r"(\d{1,2})\s*(?:am|:00)?\s*(?:to|-|until|till)\s*(\d{1,2})\s*(?:pm|:00)?", re.IGNORECASE
)
SERVICE_RE = re.compile(
    r"add\s+(?:a\s+)?service\s+(?P<name>[\w\s]+?),\s*(?P<duration>\d+)\s*min\w*,\s*\$?(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def fallback_setup_reply(db: Session, user_text: str) -> str:
    text = user_text.strip()

    service_match = SERVICE_RE.search(text)
    if service_match:
        result = _do_add_service(
            db,
            service_match.group("name").strip(),
            int(service_match.group("duration")),
            float(service_match.group("price")),
        )
        return f"Done — {'updated' if result.get('updated') else 'added'} '{result['name']}'."

    hours_match = HOURS_RE.search(text)
    if hours_match:
        open_h, close_h = int(hours_match.group(1)), int(hours_match.group(2))
        text_low = text.lower()
        # Prefer explicit am/pm markers when present. Otherwise, apply the
        # common-sense reading of casual business-hours phrasing: a closing
        # hour typed as "6" (not "18") almost always means 6 PM when it's
        # smaller than the opening hour — nobody opens at 8 and closes at
        # 6 AM. Without this, "we're open 8 to 6" (no am/pm said) is
        # rejected as invalid (8 >= 6) instead of understood as 8-18.
        if "pm" in text_low and close_h < 12:
            close_h += 12
        elif close_h < open_h and close_h <= 12:
            close_h += 12
        days = [d for d in DAY_NAMES if d in text_low] or None
        result = _do_update_hours(db, open_h, close_h, days)
        if result["ok"]:
            return f"Updated hours: {result['open_hour']}:00–{result['close_hour']}:00."
        return result["message"]

    if "current" in text.lower() or "what are" in text.lower() or "settings" in text.lower():
        s = _do_get_settings(db)
        return (
            f"{s['business_name']}: open {s['open_hour']}:00–{s['close_hour']}:00 on "
            f"{', '.join(s['open_days']) or 'no days set'}."
        )

    return (
        "I can update hours (e.g. \"open 9 to 6, monday to friday\") or add a service "
        "(e.g. \"add service Yoga Class, 60 min, $40\") in this rule-based mode. "
        "Set XAI_API_KEY for full natural-language setup, or use the manual settings form."
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def run_setup_turn(db: Session, session: ChatSession, user_text: str) -> str:
    db.add(ChatMessage(session_id=session.id, role="user", content=user_text))
    db.commit()

    llm = _client()
    if llm is None:
        reply = fallback_setup_reply(db, user_text)
        db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
        db.commit()
        return reply

    tools = build_tools(db)
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(
        ChatMessage.created_at
    ).all()
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in history:
        if m.role == "user" and m.content:
            messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant" and m.content:
            messages.append(AIMessage(content=m.content))

    for _ in range(4):
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
            result_str = json.dumps(result)
            db.add(
                ChatMessage(
                    session_id=session.id, role="tool", content=result_str,
                    tool_calls={"name": tc["name"], "input": tc.get("args", {})},
                )
            )
            messages.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))
        db.commit()

    fallback = "Sorry, I couldn't complete that — could you rephrase?"
    db.add(ChatMessage(session_id=session.id, role="assistant", content=fallback))
    db.commit()
    return fallback
