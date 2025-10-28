import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud
from app.auth import schemas as auth_schemas
from app.db.session import Base, get_db
from app.main import app

# Use in-memory SQLite for isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def _install_db_override():
    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        if original is not None:
            app.dependency_overrides[get_db] = original
        else:
            app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


def _unique_email(prefix: str) -> str:
    return f"{prefix}.{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(scope="function")
def admin_creds():
    return {
        "email": _unique_email("admin"),
        "password": "adminpass123",
        "role": "admin",
    }


@pytest.fixture(scope="function")
def admin_headers(admin_creds):
    # Register admin
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": admin_creds["email"],
            "password": admin_creds["password"],
            "nombre": "Admin",
            "apellidos": "User",
            "role": admin_creds["role"],
        },
    )
    assert resp.status_code in (200, 201, 400)
    # Login
    login = client.post(
        "/api/v1/auth/login",
        data={"username": admin_creds["email"], "password": admin_creds["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRBACSecurity:
    def test_training_session_exercises_requires_auth(self):
        # Unauth should be 401
        r = client.get("/api/v1/training-sessions/1/exercises")
        assert r.status_code == 401

    def test_training_session_exercises_with_admin(self, admin_headers):
        r = client.get("/api/v1/training-sessions/1/exercises", headers=admin_headers)
        assert r.status_code in (200, 404)

    def test_client_progress_requires_auth(self):
        r = client.get("/api/v1/training-sessions/progress/client/1")
        assert r.status_code == 401

    def test_client_progress_with_admin(self, admin_headers):
        r = client.get(
            "/api/v1/training-sessions/progress/client/1", headers=admin_headers
        )
        assert r.status_code in (200, 404)

    def test_client_exercise_progress_requires_auth(self):
        r = client.get("/api/v1/training-sessions/progress/client/1/exercise/1")
        assert r.status_code == 401

    def test_client_exercise_progress_with_admin(self, admin_headers):
        r = client.get(
            "/api/v1/training-sessions/progress/client/1/exercise/1",
            headers=admin_headers,
        )
        assert r.status_code in (200, 404)

    def test_progress_by_id_requires_auth(self):
        r = client.get("/api/v1/training-sessions/progress/1")
        assert r.status_code == 401

    def test_progress_by_id_with_admin(self, admin_headers):
        r = client.get("/api/v1/training-sessions/progress/1", headers=admin_headers)
        assert r.status_code in (200, 404)

    def test_standalone_session_exercises_requires_auth(self):
        r = client.get("/api/v1/standalone-sessions/1/exercises")
        assert r.status_code == 401

    def test_standalone_session_exercises_with_admin(self, admin_headers):
        r = client.get("/api/v1/standalone-sessions/1/exercises", headers=admin_headers)
        assert r.status_code in (200, 404)
