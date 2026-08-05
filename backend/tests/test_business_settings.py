from datetime import timedelta

import pytest

from app.services import business_settings as biz
from app.services import scheduler
from tests.test_scheduler import _next_weekday


def test_default_settings_created_on_first_access(db_session):
    s = biz.get_settings(db_session)
    assert s.open_hour == 9
    assert s.close_hour == 18
    assert s.open_days == [0, 1, 2, 3, 4]


def test_updating_hours_changes_what_scheduler_accepts(db_session, sample_service, sample_customer):
    # 8 AM is rejected under default hours (open at 9)
    monday_8am = _next_weekday(0, hour=8)
    with pytest.raises(scheduler.OutsideBusinessHoursError):
        scheduler.validate_business_rules(db_session, monday_8am)

    # Staff extends hours to open at 7 AM
    biz.update_settings(db_session, open_hour=7)

    # Now the same 8 AM slot is accepted — no restart, no redeploy
    scheduler.validate_business_rules(db_session, monday_8am)


def test_updating_open_days_changes_what_scheduler_accepts(db_session):
    saturday = _next_weekday(5, hour=11)
    with pytest.raises(scheduler.OutsideBusinessHoursError):
        scheduler.validate_business_rules(db_session, saturday)

    biz.update_settings(db_session, open_days=[0, 1, 2, 3, 4, 5])  # add Saturday
    scheduler.validate_business_rules(db_session, saturday)  # should not raise


def test_available_slots_reflect_updated_hours(db_session, sample_service):
    biz.update_settings(db_session, open_hour=9, close_hour=11)  # narrow window
    day = _next_weekday(1)
    slots = scheduler.get_available_slots(db_session, sample_service, day)
    hours_present = {s.start.hour for s in slots}
    assert max(hours_present) < 11
    assert min(hours_present) >= 9
