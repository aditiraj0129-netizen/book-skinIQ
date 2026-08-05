from datetime import datetime, timedelta

import pytest

from app.services import scheduler


def _next_weekday(target_weekday: int, hour: int = 11) -> datetime:
    """Helper: next occurrence of a given weekday (0=Mon) at a fixed hour,
    guaranteed in the future relative to 'now'."""
    now = datetime.now(scheduler.TZ)
    days_ahead = (target_weekday - now.weekday()) % 7
    days_ahead = days_ahead or 7  # always strictly future
    day = now + timedelta(days=days_ahead)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


class TestBusinessRules:
    def test_rejects_past_time(self, db_session):
        past = datetime.now(scheduler.TZ) - timedelta(days=1)
        with pytest.raises(scheduler.InThePastError):
            scheduler.validate_business_rules(db_session, past)

    def test_rejects_weekend(self, db_session):
        saturday = _next_weekday(5)  # Saturday
        with pytest.raises(scheduler.OutsideBusinessHoursError):
            scheduler.validate_business_rules(db_session, saturday)

    def test_rejects_before_open(self, db_session):
        monday = _next_weekday(0, hour=7)  # 7 AM, before 9 AM open
        with pytest.raises(scheduler.OutsideBusinessHoursError):
            scheduler.validate_business_rules(db_session, monday)

    def test_rejects_after_close(self, db_session):
        monday = _next_weekday(0, hour=19)  # 7 PM, after 6 PM close
        with pytest.raises(scheduler.OutsideBusinessHoursError):
            scheduler.validate_business_rules(db_session, monday)

    def test_rejects_too_far_in_future(self, db_session):
        far = datetime.now(scheduler.TZ) + timedelta(days=999)
        with pytest.raises(scheduler.TooFarInFutureError):
            scheduler.validate_business_rules(db_session, far)

    def test_accepts_valid_weekday_slot(self, db_session):
        monday = _next_weekday(0, hour=11)
        scheduler.validate_business_rules(db_session, monday)  # should not raise


class TestBooking:
    def test_successful_booking(self, db_session, sample_service, sample_customer):
        when = _next_weekday(0, hour=10)
        appt = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=when
        )
        assert appt.id is not None
        assert appt.status.value == "confirmed"

    def test_double_booking_same_slot_rejected(self, db_session, sample_service, sample_customer):
        when = _next_weekday(1, hour=10)
        scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=when
        )
        with pytest.raises(scheduler.SlotConflictError):
            scheduler.book_appointment(
                db_session, customer=sample_customer, service=sample_service, start_local=when
            )

    def test_overlapping_but_not_identical_slot_rejected(
        self, db_session, sample_service, sample_customer
    ):
        # sample_service is 30 minutes long
        base = _next_weekday(2, hour=10)
        scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=base
        )
        overlapping = base + timedelta(minutes=15)  # overlaps 10:15-10:45 vs 10:00-10:30
        with pytest.raises(scheduler.SlotConflictError):
            scheduler.book_appointment(
                db_session, customer=sample_customer, service=sample_service, start_local=overlapping
            )

    def test_adjacent_slot_is_allowed(self, db_session, sample_service, sample_customer):
        base = _next_weekday(3, hour=10)
        scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=base
        )
        adjacent = base + timedelta(minutes=30)  # starts exactly when the first ends
        appt2 = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=adjacent
        )
        assert appt2.id is not None

    def test_cancelled_slot_can_be_rebooked(self, db_session, sample_service, sample_customer):
        when = _next_weekday(4, hour=10)
        appt = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=when
        )
        scheduler.cancel_appointment(db_session, appt)
        appt2 = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=when
        )
        assert appt2.id != appt.id
        assert appt2.status.value == "confirmed"


class TestReschedule:
    def test_reschedule_to_open_slot_succeeds(self, db_session, sample_service, sample_customer):
        when = _next_weekday(0, hour=10)
        appt = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=when
        )
        new_when = _next_weekday(0, hour=14)
        rescheduled = scheduler.reschedule_appointment(db_session, appt, new_when)
        # start_time is stored in UTC; convert back to business tz to check correctness
        import pytz

        local_result = pytz.utc.localize(rescheduled.start_time).astimezone(scheduler.TZ)
        assert local_result.hour == 14

    def test_reschedule_into_conflict_rejected(self, db_session, sample_service, sample_customer):
        slot_a = _next_weekday(1, hour=10)
        slot_b = _next_weekday(1, hour=11)
        scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=slot_a
        )
        appt_b = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=slot_b
        )
        with pytest.raises(scheduler.SlotConflictError):
            scheduler.reschedule_appointment(db_session, appt_b, slot_a)

    def test_reschedule_into_own_original_slot_is_a_noop_success(
        self, db_session, sample_service, sample_customer
    ):
        when = _next_weekday(2, hour=10)
        appt = scheduler.book_appointment(
            db_session, customer=sample_customer, service=sample_service, start_local=when
        )
        # Rescheduling "into itself" must not be blocked by its own row.
        result = scheduler.reschedule_appointment(db_session, appt, when)
        assert result.id == appt.id

