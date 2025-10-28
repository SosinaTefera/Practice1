import os
import sys
import uuid
from datetime import date, timedelta
from typing import Any, Dict

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

# Test database setup
DB_URL = os.getenv("DATABASE_URL")

if DB_URL and DB_URL.startswith("postgresql"):
    engine = create_engine(DB_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Assume Alembic migrations have been applied; do not create_all on Postgres
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Create tables only for in-memory sqlite
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


@pytest.fixture(scope="function")
def db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def admin_user(db) -> Dict[str, Any]:
    """Create an admin user for testing."""
    email = f"admin.{uuid.uuid4().hex[:8]}@example.com"
    user = crud.create_user(
        db,
        auth_schemas.UserCreate(
            email=email,
            password="adminpass123",
            nombre="Admin",
            apellidos="User",
            role="admin",
        ),
    )
    return {"email": email, "password": "adminpass123", "id": user.id}


@pytest.fixture(scope="function")
def admin_headers(admin_user) -> Dict[str, str]:
    """Get admin authentication headers."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user["email"], "password": admin_user["password"]},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestClientProfileValidations:
    """Test client profile range validations"""

    def test_age_validation_boundaries(self, admin_headers):
        """Test age validation at boundaries and edge cases"""
        # Valid age range: 13-100
        valid_ages = [13, 25, 50, 75, 100]
        for age in valid_ages:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Test{age}",
                    "apellidos": "User",
                    "mail": f"test{age}.{uuid.uuid4().hex[:8]}@example.com",
                    "edad": age,
                    "peso": 70,
                    "altura": 1.75,
                },
            )
            assert response.status_code in {200, 201}, f"Age {age} should be valid"

        # Invalid ages (should return 422)
        invalid_ages = [0, 5, 12, 101, 120, 200]
        for age in invalid_ages:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Test{age}",
                    "apellidos": "User",
                    "mail": f"test{age}.{uuid.uuid4().hex[:8]}@example.com",
                    "edad": age,
                    "peso": 70,
                    "altura": 1.75,
                },
            )
            assert response.status_code == 422, f"Age {age} should be invalid"
            errors = response.json()["errors"]
            assert any("edad" in str(error.get("loc", [])) for error in errors)

    def test_weight_validation_boundaries(self, admin_headers):
        """Test weight validation at boundaries and edge cases"""
        # Valid weight range: 20-300 kg
        valid_weights = [20, 50, 100, 150, 200, 250, 300]
        for weight in valid_weights:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Weight{weight}",
                    "apellidos": "User",
                    "mail": f"weight{weight}.{uuid.uuid4().hex[:8]}@example.com",
                    "edad": 25,
                    "peso": weight,
                    "altura": 1.75,
                },
            )
            assert response.status_code in {
                200,
                201,
            }, f"Weight {weight} should be valid"

        # Invalid weights (should return 422)
        invalid_weights = [0, 10, 19, 301, 400, 500, 1000]
        for weight in invalid_weights:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Weight{weight}",
                    "apellidos": "User",
                    "mail": f"weight{weight}.{uuid.uuid4().hex[:8]}@example.com",
                    "edad": 25,
                    "peso": weight,
                    "altura": 1.75,
                },
            )
            assert response.status_code == 422, f"Weight {weight} should be invalid"
            errors = response.json()["errors"]
            assert any("peso" in str(error.get("loc", [])) for error in errors)

    def test_height_validation_boundaries(self, admin_headers):
        """Test height validation at boundaries and edge cases"""
        # Valid height range: 1.0-2.5 meters
        valid_heights = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]
        for height in valid_heights:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Height{height}",
                    "apellidos": "User",
                    "mail": f"height{height}.{uuid.uuid4().hex[:8]}@example.com",
                    "edad": 25,
                    "peso": 70,
                    "altura": height,
                },
            )
            assert response.status_code in {
                200,
                201,
            }, f"Height {height} should be valid"

        # Invalid heights (should return 422)
        invalid_heights = [0, 0.5, 0.9, 0.99, 2.51, 2.6, 3.0, 4.0]
        for height in invalid_heights:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Height{height}",
                    "apellidos": "User",
                    "mail": f"height{height}.{uuid.uuid4().hex[:8]}@example.com",
                    "edad": 25,
                    "peso": 70,
                    "altura": height,
                },
            )
            assert response.status_code == 422, f"Height {height} should be invalid"
            errors = response.json()["errors"]
            assert any("altura" in str(error.get("loc", [])) for error in errors)

    def test_phone_validation_edge_cases(self, admin_headers):
        """Test phone validation with various formats and edge cases"""
        # Valid phone numbers (7-15 digits after stripping non-digits)
        valid_phones = [
            "1234567",  # 7 digits
            "123456789",  # 9 digits
            "+1-555-123-4567",  # International format
            "(555) 123-4567",  # US format
            "555.123.4567",  # Dotted format
            "555 123 4567",  # Spaced format
            "123456789012345",  # 15 digits
        ]

        for phone in valid_phones:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Phone{len(phone)}",
                    "apellidos": "User",
                    "mail": f"phone{len(phone)}.{uuid.uuid4().hex[:8]}@example.com",
                    "telefono": phone,
                    "edad": 25,
                    "peso": 70,
                    "altura": 1.75,
                },
            )
            assert response.status_code in {200, 201}, f"Phone {phone} should be valid"

        # Invalid phone numbers
        invalid_phones = [
            "123",  # Too short (3 digits)
            "123456",  # Too short (6 digits)
            "1234567890123456",  # Too long (16 digits)
            "abc",  # No digits
            "+",  # Just plus sign
            "()",  # Just parentheses
            "",  # Empty string
        ]

        for phone in invalid_phones:
            response = client.post(
                "/api/v1/clients/",
                headers=admin_headers,
                json={
                    "nombre": f"Phone{len(phone)}",
                    "apellidos": "User",
                    "mail": f"phone{len(phone)}.{uuid.uuid4().hex[:8]}@example.com",
                    "telefono": phone,
                    "edad": 25,
                    "peso": 70,
                    "altura": 1.75,
                },
            )
            assert response.status_code == 422, f"Phone {phone} should be invalid"
            errors = response.json()["errors"]
            assert any("telefono" in str(error.get("loc", [])) for error in errors)

    def test_multiple_validation_errors(self, admin_headers):
        """Test that multiple validation errors are returned together"""
        response = client.post(
            "/api/v1/clients/",
            headers=admin_headers,
            json={
                "nombre": "Test",
                "apellidos": "User",
                "mail": f"test.{uuid.uuid4().hex[:8]}@example.com",
                "edad": 5,  # Invalid: too young
                "peso": 400,  # Invalid: too heavy
                "altura": 2.6,  # Invalid: too tall
                "telefono": "123",  # Invalid: too short
            },
        )

        assert response.status_code == 422
        errors = response.json()["errors"]

        # Should have multiple validation errors
        assert len(errors) >= 3

        # Check that all invalid fields are mentioned
        error_locs = [str(error.get("loc", [])) for error in errors]
        assert any("edad" in loc for loc in error_locs)
        assert any("peso" in loc for loc in error_locs)
        assert any("altura" in loc for loc in error_locs)
        assert any("telefono" in loc for loc in error_locs)


class TestSessionDurationValidations:
    """Test session duration validations"""

    def test_standalone_session_duration_validation(self, admin_headers):
        """Test standalone session duration validation (1-480 minutes)"""
        # First create a client and trainer
        client_response = client.post(
            "/api/v1/clients/",
            headers=admin_headers,
            json={
                "nombre": "Session",
                "apellidos": "Test",
                "mail": f"session.{uuid.uuid4().hex[:8]}@example.com",
                "edad": 25,
                "peso": 70,
                "altura": 1.75,
            },
        )
        client_id = client_response.json()["id"]

        trainer_response = client.post(
            "/api/v1/trainers/",
            headers=admin_headers,
            json={
                "nombre": "Session",
                "apellidos": "Trainer",
                "mail": f"session.trainer.{uuid.uuid4().hex[:8]}@example.com",
                "telefono": "1234567890",
            },
        )
        trainer_id = trainer_response.json()["id"]

        # Valid durations
        valid_durations = [1, 15, 30, 45, 60, 120, 240, 480]
        for duration in valid_durations:
            response = client.post(
                "/api/v1/standalone-sessions/",
                headers=admin_headers,
                json={
                    "trainer_id": trainer_id,
                    "client_id": client_id,
                    "session_date": "2025-08-21",
                    "session_name": f"Test {duration}min",
                    "session_type": "cardio",
                    "planned_duration": duration,
                },
            )
            assert response.status_code in {
                200,
                201,
            }, f"Duration {duration} should be valid"

        # Invalid durations
        invalid_durations = [0, 481, 500, 600, 1000, 1440]
        for duration in invalid_durations:
            response = client.post(
                "/api/v1/standalone-sessions/",
                headers=admin_headers,
                json={
                    "trainer_id": trainer_id,
                    "client_id": client_id,
                    "session_date": "2025-08-21",
                    "session_name": f"Test {duration}min",
                    "session_type": "cardio",
                    "planned_duration": duration,
                },
            )
            assert response.status_code == 422, f"Duration {duration} should be invalid"
            errors = response.json()["errors"]
            assert any(
                "planned_duration" in str(error.get("loc", [])) for error in errors
            )


class TestProgressTrackingValidations:
    """Test progress tracking validations"""

    def test_progress_tracking_weight_validation(self, admin_headers):
        """Test progress tracking weight validation (0-1000 kg)"""
        # First create a client and exercise
        client_response = client.post(
            "/api/v1/clients/",
            headers=admin_headers,
            json={
                "nombre": "Progress",
                "apellidos": "Test",
                "mail": f"progress.{uuid.uuid4().hex[:8]}@example.com",
                "edad": 25,
                "peso": 70,
                "altura": 1.75,
            },
        )
        client_id = client_response.json()["id"]

        exercise_response = client.post(
            "/api/v1/exercises/",
            headers=admin_headers,
            json={
                "exercise_id": f"PROG_{uuid.uuid4().hex[:6]}",
                "nombre": "Progress Test Exercise",
                "nombre_ingles": "Progress Test Exercise",
                "tipo": "strength",
                "categoria": "upper_body",
                "nivel": "beginner",
                "equipo": "barbell",
                "patron_movimiento": "push",
                "tipo_carga": "free_weight",
                "musculatura_principal": "chest",
                "descripcion": "Test exercise for progress tracking",
            },
        )
        exercise_id = exercise_response.json()["id"]

        # Valid weights (use unique tracking_date per insert to satisfy unique constraint)
        valid_weights = [0, 50, 100, 200, 500, 750, 1000]
        base_date = date.today()
        for idx, weight in enumerate(valid_weights):
            tracking_date = (base_date + timedelta(days=idx)).isoformat()
            response = client.post(
                "/api/v1/training-sessions/progress",
                headers=admin_headers,
                json={
                    "client_id": client_id,
                    "exercise_id": exercise_id,
                    "tracking_date": tracking_date,
                    "max_weight": weight,
                },
            )
            assert response.status_code in {
                200,
                201,
            }, f"Weight {weight} should be valid"

        # Invalid weights (also use unique tracking_date values)
        invalid_weights = [-1, 1001, 1500, 2000]
        for idx, weight in enumerate(invalid_weights, start=100):
            tracking_date = (base_date + timedelta(days=idx)).isoformat()
            response = client.post(
                "/api/v1/training-sessions/progress",
                headers=admin_headers,
                json={
                    "client_id": client_id,
                    "exercise_id": exercise_id,
                    "tracking_date": tracking_date,
                    "max_weight": weight,
                },
            )
            assert response.status_code == 422, f"Weight {weight} should be invalid"
            errors = response.json()["errors"]
            assert any("max_weight" in str(error.get("loc", [])) for error in errors)


class TestFeedbackScoreValidations:
    """Test feedback score validations (1-10 scale)"""

    def test_feedback_score_validation(self, admin_headers):
        """Test that feedback scores are properly validated"""
        # First create a standalone session
        client_response = client.post(
            "/api/v1/clients/",
            headers=admin_headers,
            json={
                "nombre": "Feedback",
                "apellidos": "Test",
                "mail": f"feedback.{uuid.uuid4().hex[:8]}@example.com",
                "edad": 25,
                "peso": 70,
                "altura": 1.75,
            },
        )
        client_id = client_response.json()["id"]

        trainer_response = client.post(
            "/api/v1/trainers/",
            headers=admin_headers,
            json={
                "nombre": "Feedback",
                "apellidos": "Trainer",
                "mail": f"feedback.trainer.{uuid.uuid4().hex[:8]}@example.com",
                "telefono": "1234567890",
            },
        )
        trainer_id = trainer_response.json()["id"]

        session_response = client.post(
            "/api/v1/standalone-sessions/",
            headers=admin_headers,
            json={
                "trainer_id": trainer_id,
                "client_id": client_id,
                "session_date": "2025-08-21",
                "session_name": "Feedback Test",
                "session_type": "cardio",
                "planned_duration": 45,
            },
        )
        session_id = session_response.json()["id"]

        # Valid scores (1-10)
        valid_scores = [1, 3, 5, 7, 10]
        for score in valid_scores:
            response = client.post(
                f"/api/v1/standalone-sessions/{session_id}/feedback",
                headers=admin_headers,
                json={
                    "standalone_session_id": session_id,
                    "client_id": client_id,
                    "perceived_effort": score,
                    "fatigue_level": score,
                    "sleep_quality": score,
                    "stress_level": score,
                    "motivation_level": score,
                    "energy_level": score,
                    "feedback_date": "2025-08-21T12:00:00",
                },
            )
            assert response.status_code in {200, 201}, f"Score {score} should be valid"

        # Invalid scores
        invalid_scores = [0, 11, -1, 15, 100]
        for score in invalid_scores:
            response = client.post(
                f"/api/v1/standalone-sessions/{session_id}/feedback",
                headers=admin_headers,
                json={
                    "standalone_session_id": session_id,
                    "client_id": client_id,
                    "perceived_effort": score,
                    "fatigue_level": score,
                    "sleep_quality": score,
                    "stress_level": score,
                    "motivation_level": score,
                    "energy_level": score,
                    "feedback_date": "2025-08-21T12:00:00",
                },
            )
            assert response.status_code == 422, f"Score {score} should be invalid"
            errors = response.json()["errors"]
            assert any(
                "perceived_effort" in str(error.get("loc", [])) for error in errors
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
