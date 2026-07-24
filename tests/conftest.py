import base64
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool   # <-- add this

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.rate_limit import limiter
from fastapi.testclient import TestClient

TEST_DATABASE_URL = "sqlite://"

# admin_auth.verify_admin reads these fresh from the environment on every
# request (not cached at import time), so setting them here works without
# needing them in the CI workflow's env block.
os.environ.setdefault("ADMIN_USER", "test-admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")


def admin_auth_header():
    creds = f"{os.environ['ADMIN_USER']}:{os.environ['ADMIN_PASSWORD']}"
    return {"Authorization": "Basic " + base64.b64encode(creds.encode()).decode()}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # The limiter is a module-level singleton shared across the whole test
    # session — without resetting it, one test's requests count toward every
    # other test's quota (all TestClient requests share the same fake IP),
    # which would make rate-limit tests order-dependent and flaky.
    limiter.reset()
    yield

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # <-- forces one shared connection across all threads
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_agent(db_session):
    from app.models import Agent
    agent = Agent(
        slug="doctor-physician", number=1, industry="Healthcare", profession="Doctor / Physician",
        description="test", system_prompt="You are a doctor agent.",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture()
def second_agent(db_session):
    from app.models import Agent
    agent = Agent(
        slug="corporate-lawyer", number=2, industry="Legal", profession="Corporate Lawyer",
        description="test", system_prompt="You are a lawyer agent.",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent