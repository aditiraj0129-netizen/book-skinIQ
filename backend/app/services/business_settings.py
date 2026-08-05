"""
Reads and writes the singleton BusinessSettings row. Falls back to sane
defaults (matching the old static config) if no row exists yet, so a fresh
database doesn't need a special migration step before the app is usable.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.business import BusinessSettings

DEFAULT_ID = "default"


def get_settings(db: Session) -> BusinessSettings:
    settings = db.get(BusinessSettings, DEFAULT_ID)
    if settings is None:
        settings = BusinessSettings(id=DEFAULT_ID)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, **fields) -> BusinessSettings:
    settings = get_settings(db)
    for key, value in fields.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings
