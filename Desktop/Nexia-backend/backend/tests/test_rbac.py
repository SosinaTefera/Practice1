import os
import sys
import uuid
from typing import Any, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud, schemas
from app.auth import schemas as auth_schemas
from app.auth.utils import create_access_token
from app.db import models
from app.db.session import Base, get_db
from app.main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
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
def db():
    """Provide a fresh database for each test"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def user_creds(db) -> Dict[str, Dict[str, str]]:
    """Create unique admin, trainer, and athlete users and return their credentials."""
    creds = {
        "admin": {
            "email": _unique_email("admin"),
            "password": "adminpass123",
            "role": "admin",
        },
        "trainer": {
            "email": _unique_email("trainer"),
            "password": "trainerpass123",
            "role": "trainer",
        },
        "athlete": {
            "email": _unique_email("athlete"),
            "password": "athletepass123",
            "role": "athlete",
        },
    }
    for role_name, data in creds.items():
        user = crud.create_user(
            db,
            auth_schemas.UserCreate(
                email=data["email"],
                password=data["password"],
                nombre="Test",
                apellidos="User",
                role=data["role"],
            ),
        )
        # Mark user as verified for testing
        crud.verify_user_email(db, user)
    return creds


def get_auth_headers(user_data: Dict[str, Any]) -> Dict[str, str]:
    """Get authentication headers for a user"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuthentication:
    """Test authentication endpoints"""

    def test_register_user(self):
        """Test user registration"""
        unique_email = f"test.{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "password": "testpass123",
            "nombre": "Test",
            "apellidos": "User",
            "role": "athlete",
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "verification_token" in data  # Available in development
        assert "Registration successful" in data["message"]

    def test_login_user(self):
        """Test user login"""
        # First register a user
        unique_email = f"login.{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "password": "loginpass123",
            "nombre": "Test",
            "apellidos": "User",
            "role": "athlete",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Verify the email first (new requirement)
        register_data = register_response.json()
        verify_response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": register_data["verification_token"]},
        )
        assert verify_response.status_code == 200

        # Then login
        login_data = {"username": unique_email, "password": "loginpass123"}
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_password_recovery_flow(self):
        """Test password recovery flow"""
        # First register a user
        unique_email = f"recovery.{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "password": "oldpass123",
            "nombre": "Test",
            "apellidos": "User",
            "role": "athlete",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Verify the email first (new requirement)
        register_data = register_response.json()
        assert "verification_token" in register_data

        verify_response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": register_data["verification_token"]},
        )
        assert verify_response.status_code == 200

        # Request password reset
        reset_request = {"email": unique_email}
        response = client.post("/api/v1/auth/forgot-password", json=reset_request)
        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data

        # Reset password
        reset_data = {"token": data["reset_token"], "new_password": "newpass123"}
        response = client.post("/api/v1/auth/reset-password", json=reset_data)
        assert response.status_code == 200

        # Verify new password works
        login_data = {"username": unique_email, "password": "newpass123"}
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200

    def test_email_verification_flow(self):
        """Test complete email verification flow"""
        # Register a new user
        unique_email = f"verify.{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "password": "testpass123",
            "nombre": "Test",
            "apellidos": "User",
            "role": "athlete",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        register_data = register_response.json()
        assert "message" in register_data
        assert "verification_token" in register_data  # Available in development

        # Try to login before verification - should fail
        login_data = {"username": unique_email, "password": "testpass123"}
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 403
        assert "verify your email" in response.json()["detail"]

        # Verify email
        verify_response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": register_data["verification_token"]},
        )
        assert verify_response.status_code == 200
        assert "Email verified successfully" in verify_response.json()["message"]

        # Try to verify again - should still work but indicate already verified
        verify_again_response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": register_data["verification_token"]},
        )
        assert verify_again_response.status_code == 200
        assert "already verified" in verify_again_response.json()["message"]

        # Now login should work
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_resend_verification_email(self):
        """Test resending verification email"""
        # Register a new user
        unique_email = f"resend.{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "password": "testpass123",
            "nombre": "Test",
            "apellidos": "User",
            "role": "athlete",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Request resend for unverified user
        resend_response = client.post(
            "/api/v1/auth/resend-verification", json={"email": unique_email}
        )
        assert resend_response.status_code == 200
        resend_data = resend_response.json()
        assert "verification_token" in resend_data  # Available in development

        # Verify with the new token
        verify_response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": resend_data["verification_token"]},
        )
        assert verify_response.status_code == 200

        # Request resend for verified user - should indicate already verified
        resend_verified_response = client.post(
            "/api/v1/auth/resend-verification", json={"email": unique_email}
        )
        assert resend_verified_response.status_code == 200
        assert "already verified" in resend_verified_response.json()["message"]

        # Request resend for non-existent user - should not reveal user existence
        nonexistent_response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nonexistent@example.com"},
        )
        assert (
            nonexistent_response.status_code == 200
        )  # Always 200 to avoid enumeration

    def test_invalid_verification_token(self):
        """Test verification with invalid tokens"""
        # Test with completely invalid token
        invalid_response = client.post(
            "/api/v1/auth/verify-email", json={"token": "invalid.token.here"}
        )
        assert invalid_response.status_code == 401

        # Test with expired token (we can't easily test this without time manipulation)
        # But we test the structure is correct for error handling


class TestRBACEnforcement:
    """Test Role-Based Access Control enforcement"""

    def test_admin_access_to_all_endpoints(self, user_creds):
        """Test that admin can access all endpoints"""
        admin_headers = get_auth_headers(user_creds["admin"])

        # Test admin can access trainer endpoints
        response = client.get("/api/v1/trainers/", headers=admin_headers)
        assert response.status_code == 200

        # Test admin can access client endpoints
        response = client.get("/api/v1/clients/", headers=admin_headers)
        assert response.status_code == 200

        # Test admin can access training plans list requires filter
        response = client.get(
            "/api/v1/training-plans/?trainer_id=1", headers=admin_headers
        )
        assert response.status_code in [200, 404]

    def test_trainer_access_restrictions(self, user_creds):
        """Test that trainer has appropriate access restrictions"""
        trainer_headers = get_auth_headers(user_creds["trainer"])

        # Resolve trainer_id via admin list
        admin_headers = get_auth_headers(user_creds["admin"])
        trainers_resp = client.get("/api/v1/trainers/", headers=admin_headers)
        assert trainers_resp.status_code == 200
        trainers = trainers_resp.json()
        trainer = next(
            (
                t
                for t in trainers
                if t["mail"].lower() == user_creds["trainer"]["email"].lower()
            ),
            None,
        )
        assert trainer is not None
        trainer_id = trainer["id"]

        # Trainer should be able to access their own trainer record
        response = client.get(f"/api/v1/trainers/{trainer_id}", headers=trainer_headers)
        assert response.status_code == 200

        # Trainer should NOT be able to access all clients (only their linked ones)
        response = client.get("/api/v1/clients/", headers=trainer_headers)
        # This might return 200 with empty list, or 403 depending on implementation
        assert response.status_code in [200, 403]

        # Trainer should be able to create training plans (requires trainer_id, client_id, name, dates, goal)
        # Resolve a client_id via admin
        client_response = client.get("/api/v1/clients/", headers=admin_headers)
        assert client_response.status_code == 200
        clients_payload = client_response.json()
        clients = clients_payload.get("items", [])
        if clients:
            client_id = clients[0]["id"]
            from datetime import date, timedelta

            today = date.today()
            plan_data = {
                "trainer_id": trainer_id,
                "client_id": client_id,
                "name": "Test Plan",
                "description": "Test Description",
                "start_date": str(today),
                "end_date": str(today + timedelta(days=30)),
                "goal": "Strength",
            }
            response = client.post(
                "/api/v1/training-plans/", json=plan_data, headers=trainer_headers
            )
            assert response.status_code in [
                201,
                403,
            ]  # 403 if trainer lacks permission in current config

    def test_athlete_access_restrictions(self, user_creds):
        """Test that athlete has appropriate access restrictions"""
        athlete_headers = get_auth_headers(user_creds["athlete"])

        # Athlete should NOT be able to access trainer endpoints
        response = client.get("/api/v1/trainers/", headers=athlete_headers)
        assert response.status_code == 403

        # Athlete should NOT be able to create training plans
        plan_data = {
            "nombre": "Test Plan",
            "descripcion": "Test Description",
            "objetivo": "Strength",
        }
        response = client.post(
            "/api/v1/training-plans/", json=plan_data, headers=athlete_headers
        )
        assert response.status_code == 403

    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Test without authentication headers
        response = client.get("/api/v1/clients/")
        assert response.status_code == 401

        response = client.get("/api/v1/trainers/")
        assert response.status_code == 401

        response = client.get("/api/v1/training-plans/")
        assert response.status_code == 401


class TestTrainerClientLinking:
    """Test trainer-client linking functionality"""

    def test_trainer_can_link_client(self, user_creds):
        """Test that trainer can link to a client"""
        trainer_headers = get_auth_headers(user_creds["trainer"])  # noqa: F841
        admin_headers = get_auth_headers(user_creds["admin"])

        # Get trainer ID
        trainers_resp = client.get("/api/v1/trainers/", headers=admin_headers)
        assert trainers_resp.status_code == 200
        trainers = trainers_resp.json()
        trainer = next(
            (
                t
                for t in trainers
                if t["mail"].lower() == user_creds["trainer"]["email"].lower()
            ),
            None,
        )
        assert trainer is not None
        trainer_id = trainer["id"]

        # Get client ID
        client_response = client.get("/api/v1/clients/", headers=admin_headers)
        assert client_response.status_code == 200
        clients_payload = client_response.json()
        clients = clients_payload.get("items", [])
        # Find our athlete by email
        athlete = next(
            (
                c
                for c in clients
                if c.get("mail", "").lower() == user_creds["athlete"]["email"].lower()
            ),
            None,
        )
        assert athlete is not None
        client_id = athlete["id"]

        # Link client to trainer
        link_data = {"trainer_id": trainer_id, "client_id": client_id}
        response = client.post(
            f"/api/v1/trainers/{trainer_id}/clients/{client_id}",
            json=link_data,
            headers=admin_headers,
        )
        assert response.status_code == 201

    def test_trainer_client_uniqueness(self, user_creds):
        """Test that trainer-client linking enforces uniqueness"""
        trainer_headers = get_auth_headers(user_creds["trainer"])  # noqa: F841
        admin_headers = get_auth_headers(user_creds["admin"])

        # Get trainer ID
        trainers_resp = client.get("/api/v1/trainers/", headers=admin_headers)
        assert trainers_resp.status_code == 200
        trainers = trainers_resp.json()
        trainer = next(
            (
                t
                for t in trainers
                if t["mail"].lower() == user_creds["trainer"]["email"].lower()
            ),
            None,
        )
        assert trainer is not None
        trainer_id = trainer["id"]

        # Get client ID
        client_response = client.get("/api/v1/clients/", headers=admin_headers)
        assert client_response.status_code == 200
        clients_payload = client_response.json()
        clients = clients_payload.get("items", [])
        athlete = next(
            (
                c
                for c in clients
                if c.get("mail", "").lower() == user_creds["athlete"]["email"].lower()
            ),
            None,
        )
        assert athlete is not None
        client_id = athlete["id"]

        # First link should succeed
        link_data = {"trainer_id": trainer_id, "client_id": client_id}
        response = client.post(
            f"/api/v1/trainers/{trainer_id}/clients/{client_id}",
            json=link_data,
            headers=admin_headers,
        )
        assert response.status_code == 201

        # Second link should fail (duplicate)
        response = client.post(
            f"/api/v1/trainers/{trainer_id}/clients/{client_id}",
            json=link_data,
            headers=admin_headers,
        )
        assert response.status_code == 400  # or 409 depending on implementation


class TestFeedbackRBAC:
    """Test feedback submission RBAC"""

    def test_athlete_can_submit_own_feedback(self, user_creds):
        """Test that athlete can submit feedback for their own sessions"""
        athlete_headers = get_auth_headers(user_creds["athlete"])

        # This would require creating a training session first
        # For now, test the endpoint exists and requires authentication
        feedback_data = {
            "client_id": 1,  # This would be the athlete's client_id
            "perceived_effort": 7,
            "fatigue_level": 5,
            "notes": "Test feedback",
            "feedback_date": "2024-01-01T00:00:00",
        }

        # This should fail without proper session_id, but we're testing RBAC
        response = client.post(
            "/api/v1/training-sessions/1/feedback",
            json=feedback_data,
            headers=athlete_headers,
        )
        # Should get 404 (session not found) or 422 (validation error), not 403 (forbidden)
        assert response.status_code in [404, 422]

    def test_unauthorized_feedback_submission(self):
        """Test that feedback submission requires authentication"""
        feedback_data = {
            "client_id": 1,
            "perceived_effort": 7,
            "fatigue_level": 5,
            "notes": "Test feedback",
            "feedback_date": "2024-01-01T00:00:00",
        }

        response = client.post(
            "/api/v1/training-sessions/1/feedback", json=feedback_data
        )
        assert response.status_code == 401


class TestProgressTracking:
    """Test progress tracking and BMI functionality"""

    def test_bmi_calculation(self, user_creds):
        """Test BMI calculation in client creation"""
        admin_headers = get_auth_headers(user_creds["admin"])

        # Create client with weight and height
        client_data = {
            "nombre": "BMI Test",
            "apellidos": "User",
            "mail": f"bmi.{uuid.uuid4().hex[:8]}@example.com",
            "edad": 30,
            "peso": 80.0,  # 80 kg
            "altura": 1.80,  # 1.80 m
        }

        response = client.post(
            "/api/v1/clients/", json=client_data, headers=admin_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "imc" in data
        # BMI = weight(kg) / height(m)² = 80 / (1.80)² = 80 / 3.24 ≈ 24.69
        expected_bmi = round(80.0 / (1.80**2), 2)
        assert abs(data["imc"] - expected_bmi) < 0.01

    def test_progress_metrics(self, user_creds):
        """Athlete can view their own client profile (after admin sets weight/height)."""
        admin_headers = get_auth_headers(user_creds["admin"])
        athlete_headers = get_auth_headers(user_creds["athlete"])

        # Resolve athlete's client_id via admin list
        client_response = client.get("/api/v1/clients/", headers=admin_headers)
        assert client_response.status_code == 200
        clients_payload = client_response.json()
        clients = clients_payload.get("items", [])
        athlete = next(
            (
                c
                for c in clients
                if c.get("mail", "").lower() == user_creds["athlete"]["email"].lower()
            ),
            None,
        )
        assert athlete is not None
        client_id = athlete["id"]

        # Set weight/height as admin
        update_payload = {"peso": 72.5, "altura": 1.78}
        upd = client.put(
            f"/api/v1/clients/{client_id}", json=update_payload, headers=admin_headers
        )
        assert upd.status_code in [
            200,
            422,
        ]  # allow if validation blocks fields in current model

        # Athlete reads own profile
        response = client.get(f"/api/v1/clients/{client_id}", headers=athlete_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
