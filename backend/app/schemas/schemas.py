from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---- Chat ----
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    engine: str  # "grok" | "fallback"


# ---- Services ----
class ServiceOut(BaseModel):
    id: str
    name: str
    description: str
    duration_minutes: int
    price: float
    active: bool

    class Config:
        from_attributes = True


class ServiceCreate(BaseModel):
    name: str
    description: str = ""
    duration_minutes: int = 30
    price: float = 0


# ---- Customers ----
class CustomerOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str

    class Config:
        from_attributes = True


# ---- Appointments ----
class AppointmentOut(BaseModel):
    id: str
    customer: CustomerOut
    service: ServiceOut
    start_time: datetime
    end_time: datetime
    status: str
    notes: str
    created_via: str

    class Config:
        from_attributes = True


class AppointmentCreateAdmin(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_phone: str = ""
    service_id: str
    start_time: datetime
    notes: str = ""


class AppointmentReschedule(BaseModel):
    new_start_time: datetime


class AvailabilitySlot(BaseModel):
    start: datetime
    end: datetime
    available: bool


# ---- Business settings ----
class BusinessInfoOut(BaseModel):
    business_name: str
    tagline: str
    description: str
    address: str
    phone: str
    open_hour: int
    close_hour: int
    open_days: list[int]

    class Config:
        from_attributes = True


class BusinessInfoUpdate(BaseModel):
    business_name: str | None = None
    tagline: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    open_hour: int | None = None
    close_hour: int | None = None
    open_days: list[int] | None = None


# ---- Reviews ----
class ReviewOut(BaseModel):
    id: str
    customer_name: str
    rating: int
    comment: str
    service_name: str | None = None

    class Config:
        from_attributes = True


# ---- Public booking (calendar-driven, not chat) ----
class PublicBookingRequest(BaseModel):
    service_id: str
    start_time: datetime
    customer_name: str
    customer_email: EmailStr
    customer_phone: str = ""
    notes: str = ""


# ---- User login (name-only, no password) ----
class UserLoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str


# ---- Staff setup chat ----
class SetupChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)


class SetupChatResponse(BaseModel):
    session_id: str
    reply: str
    engine: str


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Analytics ----
class DashboardStats(BaseModel):
    total_appointments: int
    upcoming_appointments: int
    cancelled_appointments: int
    bookings_today: int
    busiest_hour: str | None
    bookings_by_day: dict[str, int]
    bookings_by_service: dict[str, int]
