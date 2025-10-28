#!/usr/bin/env python3
"""
Tests for fatigue analysis RBAC and CRUD functionality
"""

import os
import sys
import uuid
from datetime import date

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)


def get_trainer_headers() -> dict:
    """Get authorization headers for a trainer user"""
    unique_email = f"trainer.{uuid.uuid4().hex[:8]}@example.com"

    # Register trainer
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TrainerPass123",
            "nombre": "Test",
            "apellidos": "Trainer",
            "role": "trainer",
        },
    )
    assert reg.status_code in (200, 201, 400)

    # Login trainer
    login = client.post(
        "/api/v1/auth/login",
        data={"username": unique_email, "password": "TrainerPass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, unique_email


def get_another_trainer_headers() -> dict:
    """Get authorization headers for another trainer user"""
    unique_email = f"trainer2.{uuid.uuid4().hex[:8]}@example.com"

    # Register trainer
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TrainerPass123",
            "nombre": "Test",
            "apellidos": "Trainer2",
            "role": "trainer",
        },
    )
    assert reg.status_code in (200, 201, 400)

    # Login trainer
    login = client.post(
        "/api/v1/auth/login",
        data={"username": unique_email, "password": "TrainerPass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, unique_email


def create_test_client(headers: dict) -> int:
    """Create a test client and return its ID"""
    client_data = {
        "nombre": "Test",
        "apellidos": "Client",
        "mail": f"client.{uuid.uuid4().hex[:8]}@example.com",
        "edad": 25,
        "sexo": "Masculino",
        "peso": 70.0,
        "altura": 1.75,
    }

    response = client.post("/api/v1/clients/", json=client_data, headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


# Test Functions
def test_create_fatigue_analysis():
    """Test creating a fatigue analysis record"""
    headers, _ = get_trainer_headers()
    client_id = create_test_client(headers)

    fatigue_data = {
        "client_id": client_id,
        "analysis_date": date.today().isoformat(),
        "pre_fatigue_level": 3,
        "post_fatigue_level": 6,
        "pre_energy_level": 7,
        "post_energy_level": 4,
        "session_type": "training",
        "session_duration": 60,
        "notes": "Test session",
    }

    response = client.post(
        "/api/v1/fatigue/fatigue-analysis/", json=fatigue_data, headers=headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["client_id"] == client_id
    assert data["pre_fatigue_level"] == 3
    assert data["post_fatigue_level"] == 6
    assert data["fatigue_delta"] == 3  # 6 - 3
    assert data["energy_delta"] == -3  # 4 - 7
    assert data["risk_level"] in ["low", "medium", "high"]
    assert data["recommendations"] is not None


def test_fatigue_analysis_rbac():
    """Test that trainers cannot access other trainers' client fatigue analysis"""
    headers1, _ = get_trainer_headers()
    headers2, _ = get_another_trainer_headers()

    # Create clients for both trainers
    client_id1 = create_test_client(headers1)
    create_test_client(headers2)  # Create client for trainer 2 (not used in this test)

    # Get trainer IDs (we need to get the actual trainer IDs from the database)
    # For now, let's assume trainer 1 links their client to themselves
    # In a real scenario, we'd need to get the trainer ID from the JWT token

    # Create fatigue analysis for trainer 1's client
    fatigue_data = {
        "client_id": client_id1,
        "analysis_date": date.today().isoformat(),
        "pre_fatigue_level": 3,
        "post_fatigue_level": 6,
        "session_type": "training",
        "session_duration": 60,
    }
    response = client.post(
        "/api/v1/fatigue/fatigue-analysis/", json=fatigue_data, headers=headers1
    )
    assert response.status_code == 200

    # Without linking, trainer 1 should NOT be able to access their client's fatigue analysis
    response = client.get(
        f"/api/v1/fatigue/clients/{client_id1}/fatigue-analysis/", headers=headers1
    )
    assert response.status_code == 403  # Forbidden - client not linked to trainer

    # Trainer 2 also cannot access trainer 1's client fatigue analysis
    response = client.get(
        f"/api/v1/fatigue/clients/{client_id1}/fatigue-analysis/", headers=headers2
    )
    assert response.status_code == 403  # Forbidden


def test_workload_tracking_rbac():
    """Test that trainers cannot access other trainers' client workload tracking"""
    headers1, _ = get_trainer_headers()
    headers2, _ = get_another_trainer_headers()

    client_id1 = create_test_client(headers1)

    # Create workload tracking for trainer 1's client
    workload_data = {
        "client_id": client_id1,
        "tracking_date": date.today().isoformat(),
        "session_type": "training",
        "duration_minutes": 60,
        "perceived_intensity": 7,
    }
    response = client.post(
        "/api/v1/fatigue/workload-tracking/", json=workload_data, headers=headers1
    )
    assert response.status_code == 200

    # Without linking, trainer 1 should NOT be able to access their client's workload tracking
    response = client.get(
        f"/api/v1/fatigue/clients/{client_id1}/workload-tracking/", headers=headers1
    )
    assert response.status_code == 403  # Forbidden - client not linked to trainer

    # Trainer 2 also cannot access trainer 1's client workload tracking
    response = client.get(
        f"/api/v1/fatigue/clients/{client_id1}/workload-tracking/", headers=headers2
    )
    assert response.status_code == 403  # Forbidden
