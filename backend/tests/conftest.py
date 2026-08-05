import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.booking import Customer, Service

# SQLite in-memory for fast, isolated unit tests. StaticPool is required
# here: without it, each new connection checked out from the pool gets its
# own private :memory: database, so a second connection (e.g. one opened by
# a FastAPI request handler reusing this fixture via dependency_overrides)
# would see an empty, table-less database even though setup already ran.
# Postgres-only features (like server-side enum checks) aren't exercised
# here — that's what the Alembic migration + Postgres in docker-compose covers.
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def sample_service(db_session):
    service = Service(name="Haircut", description="test", duration_minutes=30, price=20)
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture()
def sample_customer(db_session):
    customer = Customer(name="Jane Doe", email="jane@example.com", phone="123")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer
