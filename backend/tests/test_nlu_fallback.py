from app.models.booking import Service
from app.services.nlu_fallback import _find_service


def test_exact_service_name_in_text(db_session):
    db_session.add(Service(name="Haircut", duration_minutes=30, price=20))
    db_session.commit()
    assert _find_service(db_session, "I want a Haircut").name == "Haircut"


def test_partial_word_overlap_matches_multiword_service(db_session):
    db_session.add(Service(name="Deep Tissue Massage", duration_minutes=60, price=80))
    db_session.commit()
    # The full service name is NOT a substring of the input — only "massage" is.
    result = _find_service(db_session, "book me a massage please")
    assert result is not None
    assert result.name == "Deep Tissue Massage"


def test_no_match_returns_none(db_session):
    db_session.add(Service(name="Haircut", duration_minutes=30, price=20))
    db_session.commit()
    assert _find_service(db_session, "what's the weather today") is None


def test_ambiguous_generic_word_does_not_false_match(db_session):
    db_session.add(Service(name="Skin Facial", duration_minutes=45, price=60))
    db_session.commit()
    # "the" and short filler words shouldn't cause a spurious match
    assert _find_service(db_session, "hello there how are you") is None
