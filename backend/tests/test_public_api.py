import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.booking import Service
from app.models.business import BusinessSettings, Review
from tests.test_scheduler import _next_weekday


@pytest.fixture()
def client(db_session, monkeypatch):
    """Wires the FastAPI app's get_db dependency to the test's in-memory
    session, so API tests share the same isolated SQLite DB as unit tests."""
    from app.core.database import get_db

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db_session):
    db_session.add(BusinessSettings(id="default"))
    service = Service(name="Haircut", duration_minutes=30, price=35, description="Classic cut")
    db_session.add(service)
    db_session.add(Review(customer_name="Ana", rating=5, comment="Loved it", service_id=None))
    db_session.commit()
    db_session.refresh(service)
    return service


def test_get_business_info(client, seeded):
    r = client.get("/api/business")
    assert r.status_code == 200
    assert r.json()["business_name"] == "Bright Studio"


def test_list_reviews(client, seeded):
    r = client.get("/api/reviews")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["customer_name"] == "Ana"


def test_public_booking_success(client, seeded):
    when = _next_weekday(0, hour=10)
    r = client.post(
        "/api/book",
        json={
            "service_id": seeded.id,
            "start_time": when.isoformat(),
            "customer_name": "Sam",
            "customer_email": "sam@example.com",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"


def test_public_booking_conflict_returns_409(client, seeded):
    when = _next_weekday(1, hour=10)
    payload = {
        "service_id": seeded.id,
        "start_time": when.isoformat(),
        "customer_name": "Sam",
        "customer_email": "sam@example.com",
    }
    first = client.post("/api/book", json=payload)
    assert first.status_code == 200

    second = client.post(
        "/api/book",
        json={**payload, "customer_email": "other@example.com", "customer_name": "Other"},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "slot_conflict"


def test_public_cancel_and_reschedule(client, seeded):
    when = _next_weekday(2, hour=10)
    booked = client.post(
        "/api/book",
        json={
            "service_id": seeded.id,
            "start_time": when.isoformat(),
            "customer_name": "Sam",
            "customer_email": "sam2@example.com",
        },
    ).json()

    new_when = _next_weekday(2, hour=14)
    rescheduled = client.patch(
        f"/api/book/{booked['id']}/reschedule",
        json={
            "service_id": seeded.id,
            "start_time": new_when.isoformat(),
            "customer_name": "Sam",
            "customer_email": "sam2@example.com",
        },
    )
    assert rescheduled.status_code == 200

    cancelled = client.patch(f"/api/book/{booked['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_user_login_by_name_only(client, seeded):
    r = client.post("/api/users/login", json={"name": "Priya"})
    assert r.status_code == 200
    assert r.json()["name"] == "Priya"


def test_user_login_finds_existing_customer_by_email(client, seeded):
    when = _next_weekday(3, hour=10)
    client.post(
        "/api/book",
        json={
            "service_id": seeded.id,
            "start_time": when.isoformat(),
            "customer_name": "Priya Nair",
            "customer_email": "priya@example.com",
        },
    )
    r = client.post("/api/users/login", json={"name": "Priya", "email": "priya@example.com"})
    assert r.status_code == 200
    assert r.json()["name"] == "Priya Nair" or r.json()["name"] == "Priya"

    appts = client.get("/api/users/appointments", params={"email": "priya@example.com"})
    assert appts.status_code == 200
    assert len(appts.json()) == 1
