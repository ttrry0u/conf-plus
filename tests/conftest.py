import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

engine = create_engine(settings.test_database_url, pool_pre_ping=True, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Один раз создаёт схему для всей сессии тестов."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Транзакция + откат → чистая БД после каждого теста."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient с подменой get_db на тестовую сессию."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "testpass123",
            "role": "participant",
            "consent_152fz": True,
        },
    )
    return r.json()["access_token"]


@pytest.fixture
def speaker_token(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Speaker",
            "email": "speaker@example.com",
            "password": "speaker123",
            "role": "speaker",
            "consent_152fz": True,
        },
    )
    return r.json()["access_token"]


@pytest.fixture
def admin_token(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin@example.com",
            "password": "adminpass123",
            "role": "admin",
            "consent_152fz": True,
        },
    )
    return r.json()["access_token"]
