import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

API_PREFIX = "/api/v1"

client = TestClient(app)


def _get_admin_headers():
    # Minimal header factory for endpoints requiring auth
    # Use rbcauth from tests if available; otherwise try a quick register/login
    import uuid

    email = f"smoke.{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": email,
            "password": "AdminPass123",
            "nombre": "Smoke",
            "apellidos": "Test",
            "role": "admin",
        },
    )
    r = client.post(
        f"{API_PREFIX}/auth/login",
        data={"username": email, "password": "AdminPass123"},
    )
    if r.status_code != 200:
        return {}
    token = r.json().get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _augment_params(path: str, params: dict) -> dict:
    if path.startswith(f"{API_PREFIX}/clients"):
        params.setdefault("page", 1)
        params.setdefault("page_size", 20)
    elif path.startswith(f"{API_PREFIX}/exercises"):
        params.setdefault("limit", 5)
        params.setdefault("skip", 0)
    elif path.startswith(f"{API_PREFIX}/training-sessions"):
        params.setdefault("limit", 5)
        params.setdefault("skip", 0)
    elif path.startswith(f"{API_PREFIX}/standalone-sessions"):
        params.setdefault("limit", 5)
        params.setdefault("skip", 0)
    elif path.startswith(f"{API_PREFIX}/progress"):
        params.setdefault("limit", 5)
        params.setdefault("skip", 0)
    return params


def test_openapi_get_smoke():
    # Fetch OpenAPI spec via in-process app
    spec_resp = client.get(f"{API_PREFIX}/openapi.json")
    assert spec_resp.status_code == 200, spec_resp.text
    spec = spec_resp.json()

    auth_headers = _get_admin_headers()

    failures = []
    for path, methods in spec.get("paths", {}).items():
        op = methods.get("get")
        if not op:
            continue

        params = {}
        for p in op.get("parameters", []):
            if p.get("in") == "query":
                name = p.get("name")
                schema = p.get("schema") or {}
                if "default" in schema:
                    params[name] = schema["default"]

        params = _augment_params(path, params)
        headers = auth_headers if op.get("security") else {}
        resp = client.get(path, params=params, headers=headers)
        if resp.status_code >= 500:
            failures.append((path, resp.status_code, resp.text[:300]))

    assert not failures, "Server errors on GET endpoints: " + json.dumps(
        failures, ensure_ascii=False
    )
