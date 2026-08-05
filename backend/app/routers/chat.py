from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.chat import ChatSession
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.ai_agent import run_agent_turn

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    session = None
    if payload.session_id:
        session = db.get(ChatSession, payload.session_id)
    if session is None:
        session = ChatSession()
        db.add(session)
        db.commit()
        db.refresh(session)

    reply = run_agent_turn(db, session, payload.message)
    engine = "grok" if settings.xai_api_key else "fallback"
    return ChatResponse(session_id=session.id, reply=reply, engine=engine)
