from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.booking import Service
from app.schemas.schemas import ServiceOut

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    return db.query(Service).filter(Service.active == True).all()  # noqa: E712
