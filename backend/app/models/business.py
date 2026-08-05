import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class BusinessSettings(Base):
    """Singleton row (id is always 'default') holding the business's
    editable identity and operating hours. Previously these lived only in
    static env config; moving them here is what makes the staff setup
    chatbot possible — the assistant can actually change what the
    scheduler enforces, not just talk about it."""

    __tablename__ = "business_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: "default")
    business_name: Mapped[str] = mapped_column(String(120), default="Bright Studio")
    tagline: Mapped[str] = mapped_column(String(200), default="Booking, the way it should feel.")
    description: Mapped[str] = mapped_column(Text, default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")

    open_hour: Mapped[int] = mapped_column(Integer, default=9)
    close_hour: Mapped[int] = mapped_column(Integer, default=18)
    # Days open, 0=Monday .. 6=Sunday. Defaults to Mon-Fri.
    open_days: Mapped[list] = mapped_column(JSON, default=lambda: [0, 1, 2, 3, 4])

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Review(Base):
    """Lightweight customer review, surfaced on the landing page and via
    the informational chat assistant ("what do people say about you?")."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    service_id: Mapped[str | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    service = relationship("Service")
