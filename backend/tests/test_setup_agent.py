from app.models.booking import Service
from app.services import business_settings as biz
from app.services.setup_agent import fallback_setup_reply


def test_update_hours_via_natural_language(db_session):
    reply = fallback_setup_reply(db_session, "we're open 8 to 6, monday to friday")
    s = biz.get_settings(db_session)
    assert s.open_hour == 8
    assert "8" in reply and "18" in reply


def test_add_service_via_natural_language(db_session):
    reply = fallback_setup_reply(db_session, "add service Yoga Class, 60 min, $40")
    service = db_session.query(Service).filter(Service.name == "Yoga Class").first()
    assert service is not None
    assert service.duration_minutes == 60
    assert float(service.price) == 40.0
    assert "Yoga Class" in reply


def test_update_existing_service_via_natural_language(db_session):
    db_session.add(Service(name="Haircut", duration_minutes=30, price=20))
    db_session.commit()
    fallback_setup_reply(db_session, "add service Haircut, 45 min, $35")
    service = db_session.query(Service).filter(Service.name == "Haircut").first()
    assert service.duration_minutes == 45
    assert float(service.price) == 35.0


def test_unrecognized_command_gives_helpful_message(db_session):
    reply = fallback_setup_reply(db_session, "make everything better please")
    assert "hours" in reply.lower() or "service" in reply.lower()


def test_get_current_settings_via_natural_language(db_session):
    reply = fallback_setup_reply(db_session, "what are our current settings?")
    assert "open" in reply.lower()
