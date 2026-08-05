from datetime import timedelta

from app.services import scheduler
from tests.test_scheduler import _next_weekday


def test_available_slots_exclude_booked_slot(db_session, sample_service, sample_customer):
    day = _next_weekday(0, hour=10)
    scheduler.book_appointment(
        db_session, customer=sample_customer, service=sample_service, start_local=day
    )
    slots = scheduler.get_available_slots(db_session, sample_service, day)
    booked_slot = next(s for s in slots if s.start.hour == 10 and s.start.minute == 0)
    assert booked_slot.available is False


def test_available_slots_respect_business_hours(db_session, sample_service):
    day = _next_weekday(1)
    slots = scheduler.get_available_slots(db_session, sample_service, day)
    assert all(9 <= s.start.hour < 18 for s in slots)


def test_available_slots_all_open_when_no_bookings(db_session, sample_service):
    day = _next_weekday(2)
    slots = scheduler.get_available_slots(db_session, sample_service, day)
    assert len(slots) > 0
    assert all(s.available for s in slots)
