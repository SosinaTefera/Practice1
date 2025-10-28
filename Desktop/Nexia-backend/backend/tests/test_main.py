import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_admin_headers() -> Dict[str, str]:
    unique_email = f"admin.{uuid.uuid4().hex[:8]}@example.com"
    # Register admin
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "AdminPass123",
            "nombre": "Admin",
            "apellidos": "User",
            "role": "admin",
        },
    )
    assert reg.status_code in (200, 201, 400)
    # Login admin
    login = client.post(
        "/api/v1/auth/login",
        data={"username": unique_email, "password": "AdminPass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Health Check Tests
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data


# Client Endpoint Tests
def test_create_client():
    # Generate unique email using UUID
    unique_email = f"john.doe.{uuid.uuid4().hex[:8]}@example.com"
    client_data = {
        "nombre": "John",
        "apellidos": "Doe",
        "mail": unique_email,
        "telefono": "123456789",
        "edad": 30,
        "peso": 70.5,
        "altura": 1.75,
    }
    headers = get_admin_headers()
    response = client.post("/api/v1/clients/", headers=headers, json=client_data)
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "John"
    assert data["apellidos"] == "Doe"
    assert data["mail"] == unique_email
    assert data["edad"] == 30
    assert data["peso"] == 70.5
    assert data["altura"] == 1.75
    assert "id" in data
    assert "fecha_alta" in data
    assert "imc" in data


def test_get_clients():
    headers = get_admin_headers()
    response = client.get("/api/v1/clients/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # API returns a paginated object
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    if len(data["items"]) > 0:
        first = data["items"][0]
        assert "id" in first
        assert "nombre" in first
        assert "apellidos" in first
        assert "mail" in first


def test_get_client_by_id():
    # First create a client
    unique_email = f"jane.smith.{uuid.uuid4().hex[:8]}@example.com"
    client_data = {
        "nombre": "Jane",
        "apellidos": "Smith",
        "mail": unique_email,
        "telefono": "987654321",
        "edad": 25,
    }
    headers = get_admin_headers()
    create_response = client.post("/api/v1/clients/", headers=headers, json=client_data)
    assert create_response.status_code == 200
    client_id = create_response.json()["id"]

    # Then get the client by ID
    response = client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == client_id
    assert data["nombre"] == "Jane"
    assert data["apellidos"] == "Smith"
    assert data["mail"] == unique_email


def test_update_client():
    # First create a client
    unique_email = f"bob.johnson.{uuid.uuid4().hex[:8]}@example.com"
    client_data = {
        "nombre": "Bob",
        "apellidos": "Johnson",
        "mail": unique_email,
        "edad": 35,
    }
    headers = get_admin_headers()
    create_response = client.post("/api/v1/clients/", headers=headers, json=client_data)
    assert create_response.status_code == 200
    client_id = create_response.json()["id"]

    # Then update the client
    update_data = {"edad": 36}
    response = client.put(
        f"/api/v1/clients/{client_id}", headers=headers, json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["edad"] == 36
    assert data["id"] == client_id


# Trainer Endpoint Tests
def test_create_trainer():
    unique_email = f"mike.wilson.{uuid.uuid4().hex[:8]}@example.com"
    trainer_data = {
        "nombre": "Mike",
        "apellidos": "Wilson",
        "mail": unique_email,
        "telefono": "555123456",
    }
    headers = get_admin_headers()
    response = client.post("/api/v1/trainers/", headers=headers, json=trainer_data)
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Mike"
    assert data["apellidos"] == "Wilson"
    assert data["mail"] == unique_email
    assert data["telefono"] == "555123456"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "is_active" in data


def test_get_trainers():
    headers = get_admin_headers()
    response = client.get("/api/v1/trainers/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "nombre" in data[0]
        assert "apellidos" in data[0]
        assert "mail" in data[0]


def test_get_trainer_by_id():
    # First create a trainer
    unique_email = f"sarah.davis.{uuid.uuid4().hex[:8]}@example.com"
    trainer_data = {"nombre": "Sarah", "apellidos": "Davis", "mail": unique_email}
    headers = get_admin_headers()
    create_response = client.post(
        "/api/v1/trainers/", headers=headers, json=trainer_data
    )
    assert create_response.status_code == 200
    trainer_id = create_response.json()["id"]

    # Then get the trainer by ID
    response = client.get(f"/api/v1/trainers/{trainer_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trainer_id
    assert data["nombre"] == "Sarah"
    assert data["apellidos"] == "Davis"
    assert data["mail"] == unique_email


def test_update_trainer():
    # First create a trainer
    unique_email = f"tom.miller.{uuid.uuid4().hex[:8]}@example.com"
    trainer_data = {"nombre": "Tom", "apellidos": "Miller", "mail": unique_email}
    headers = get_admin_headers()
    create_response = client.post(
        "/api/v1/trainers/", headers=headers, json=trainer_data
    )
    assert create_response.status_code == 200
    trainer_id = create_response.json()["id"]

    # Then update the trainer
    update_data = {"telefono": "555987654"}
    response = client.put(
        f"/api/v1/trainers/{trainer_id}", headers=headers, json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["telefono"] == "555987654"
    assert data["id"] == trainer_id


# Exercise Endpoint Tests
def test_create_exercise():
    unique_exercise_id = f"test_squat_{uuid.uuid4().hex[:8]}"
    exercise_data = {
        "exercise_id": unique_exercise_id,
        "nombre": "Test Squat",
        "nombre_ingles": "Test Squat",
        "tipo": "Multiarticular",
        "categoria": "Básico",
        "nivel": "beginner",
        "equipo": "barbell",
        "patron_movimiento": "dominante de rodilla",
        "tipo_carga": "external",
        "musculatura_principal": "Cuádriceps, Glúteos",
        "musculatura_secundaria": "Isquiotibiales, Core",
        "descripcion": "A test exercise for testing",
        "instrucciones": "Stand with feet shoulder-width apart...",
    }
    headers = get_admin_headers()
    response = client.post("/api/v1/exercises/", headers=headers, json=exercise_data)
    assert response.status_code == 201
    data = response.json()
    assert data["exercise_id"] == unique_exercise_id
    assert data["nombre"] == "Test Squat"
    assert data["tipo"] == "Multiarticular"
    assert data["nivel"] == "beginner"
    assert data["equipo"] == "barbell"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "is_active" in data


def test_get_exercises():
    headers = get_admin_headers()
    response = client.get("/api/v1/exercises/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "exercises" in data
    assert isinstance(data["exercises"], list)
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "has_more" in data


def test_get_exercise_by_id():
    # First create an exercise
    unique_exercise_id = f"test_deadlift_{uuid.uuid4().hex[:8]}"
    exercise_data = {
        "exercise_id": unique_exercise_id,
        "nombre": "Test Deadlift",
        "nombre_ingles": "Test Deadlift",
        "tipo": "Multiarticular",
        "categoria": "Básico",
        "nivel": "intermediate",
        "equipo": "barbell",
        "patron_movimiento": "bisagra de cadera",
        "tipo_carga": "external",
        "musculatura_principal": "Glúteos, Isquiotibiales",
        "musculatura_secundaria": "Espalda baja, Core",
    }
    headers = get_admin_headers()
    create_response = client.post(
        "/api/v1/exercises/", headers=headers, json=exercise_data
    )
    assert create_response.status_code == 201
    exercise_id = create_response.json()["id"]

    # Then get the exercise by ID
    response = client.get(f"/api/v1/exercises/{exercise_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exercise_id
    assert data["exercise_id"] == unique_exercise_id
    assert data["nombre"] == "Test Deadlift"


def test_update_exercise():
    # First create an exercise
    unique_exercise_id = f"test_bench_{uuid.uuid4().hex[:8]}"
    exercise_data = {
        "exercise_id": unique_exercise_id,
        "nombre": "Test Bench Press",
        "nombre_ingles": "Test Bench Press",
        "tipo": "Multiarticular",
        "categoria": "Básico",
        "nivel": "advanced",
        "equipo": "barbell",
        "patron_movimiento": "empuje",
        "tipo_carga": "external",
        "musculatura_principal": "Pecho",
        "musculatura_secundaria": "Tríceps, Hombros",
    }
    headers = get_admin_headers()
    create_response = client.post(
        "/api/v1/exercises/", headers=headers, json=exercise_data
    )
    assert create_response.status_code == 201
    exercise_id = create_response.json()["id"]

    # Then update the exercise
    update_data = {"nivel": "intermediate"}
    response = client.put(
        f"/api/v1/exercises/{exercise_id}", headers=headers, json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nivel"] == "intermediate"
    assert data["id"] == exercise_id


# Exercise Filter Tests
def test_get_exercises_by_muscle_group():
    headers = get_admin_headers()
    response = client.get(
        "/api/v1/exercises/by-muscle-group/Cuádriceps", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_exercises_by_equipment():
    headers = get_admin_headers()
    response = client.get("/api/v1/exercises/by-equipment/barbell", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_exercises_by_level():
    headers = get_admin_headers()
    response = client.get("/api/v1/exercises/by-level/beginner", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_exercise_by_exercise_id():
    # First create an exercise
    unique_exercise_id = f"back_squat_{uuid.uuid4().hex[:8]}"
    exercise_data = {
        "exercise_id": unique_exercise_id,
        "nombre": "Back Squat",
        "nombre_ingles": "Back Squat",
        "tipo": "Multiarticular",
        "categoria": "Básico",
        "nivel": "intermediate",
        "equipo": "barbell",
        "patron_movimiento": "dominante de rodilla",
        "tipo_carga": "external",
        "musculatura_principal": "Cuádriceps, Glúteos",
        "musculatura_secundaria": "Isquiotibiales, Core",
    }
    headers = get_admin_headers()
    create_response = client.post(
        "/api/v1/exercises/", headers=headers, json=exercise_data
    )
    assert create_response.status_code == 201

    # Then get the exercise by exercise_id
    response = client.get(
        f"/api/v1/exercises/by-exercise-id/{unique_exercise_id}", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exercise_id"] == unique_exercise_id
    assert data["nombre"] == "Back Squat"


def test_get_exercise_stats():
    headers = get_admin_headers()
    response = client.get("/api/v1/exercises/stats/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_exercises" in data
    assert "by_level" in data
    assert "by_equipment" in data
    assert "by_type" in data
    assert "by_category" in data
