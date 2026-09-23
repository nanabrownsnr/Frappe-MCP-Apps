"""Verify Twynity's public manifest and health custom routes.

Extend this module when adding or changing custom HTTP routes in twynity.py.
"""

import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

import app.twynity as twynity
from app.twynity import register_routes


@pytest.fixture
def unauthenticated_app():
    """No auth attached — manifest/health should work without a token."""
    mcp = FastMCP("test_server")
    register_routes(mcp)
    return mcp.http_app()


def test_manifest_returns_expected_shape(unauthenticated_app):
    client = TestClient(unauthenticated_app)
    response = client.get("/api/v1/.well-known/mcp.json")

    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "version" in body

def test_health_endpoint_returns_ok(unauthenticated_app):
    client = TestClient(unauthenticated_app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_configuration_schema_describes_required_connection_fields(unauthenticated_app):
    response = TestClient(unauthenticated_app).get("/api/v1/schema")

    assert response.status_code == 200
    assert response.json() == {
        "name": "frappe_configuration",
        "endpoint": "/api/v1/configuration",
        "method": "POST",
        "schema": {
            "frappe_base_url": "string",
            "api_key": "string",
            "api_secret": "string",
        },
    }


def test_configuration_preflight_is_public_and_returns_no_content(unauthenticated_app, monkeypatch):
    monkeypatch.setattr(
        twynity,
        "get_current_user",
        lambda: pytest.fail("OPTIONS must not require a user token"),
    )

    response = TestClient(unauthenticated_app).options("/api/v1/configuration")

    assert response.status_code == 204
    assert response.content == b""


def test_configuration_saves_valid_credentials_for_authenticated_user(
    unauthenticated_app, monkeypatch
):
    saved = {}

    def current_user():
        return {"id": "user-123", "email": "person@example.com"}

    async def save_connection(user_id, base_url, api_key, api_secret):
        saved.update(
            user_id=user_id,
            base_url=base_url,
            api_key=api_key,
            api_secret=api_secret,
        )

    monkeypatch.setattr(twynity, "get_current_user", current_user)
    monkeypatch.setattr(twynity, "save_connection", save_connection)
    response = TestClient(unauthenticated_app).post(
        "/api/v1/configuration",
        json={
            "frappe_base_url": "https://erp.example.com",
            "api_key": "api-key-value",
            "api_secret": "api-secret-value",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"configured": True}
    assert saved == {
        "user_id": "user-123",
        "base_url": "https://erp.example.com/",
        "api_key": "api-key-value",
        "api_secret": "api-secret-value",
    }
    assert "api-secret-value" not in response.text


def test_configuration_returns_field_specific_validation_errors(
    unauthenticated_app, monkeypatch
):
    monkeypatch.setattr(
        twynity,
        "get_current_user",
        lambda: {"id": "user-123", "email": "person@example.com"},
    )
    response = TestClient(unauthenticated_app).post(
        "/api/v1/configuration",
        json={"frappe_base_url": "not-a-url", "api_key": ""},
    )

    assert response.status_code == 422
    details = response.json()["detail"]
    assert {item["field"] for item in details} == {"frappe_base_url", "api_key", "api_secret"}
    assert "not-a-url" not in response.text


def test_configuration_rejects_malformed_json(unauthenticated_app, monkeypatch):
    monkeypatch.setattr(
        twynity,
        "get_current_user",
        lambda: {"id": "user-123", "email": "person@example.com"},
    )

    response = TestClient(unauthenticated_app).post(
        "/api/v1/configuration",
        content="{invalid json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Request body must contain valid JSON."}


def test_configuration_and_connection_status_require_authentication(
    unauthenticated_app, monkeypatch
):
    monkeypatch.setattr(
        twynity,
        "get_current_user",
        lambda: (_ for _ in ()).throw(ValueError("User is not authenticated.")),
    )
    client = TestClient(unauthenticated_app)
    payload = {
        "frappe_base_url": "https://erp.example.com",
        "api_key": "api-key-value",
        "api_secret": "api-secret-value",
    }

    configure_response = client.post("/api/v1/configuration", json=payload)
    status_response = client.get("/api/v1/external-connection/me")

    assert configure_response.status_code == 401
    assert status_response.status_code == 401
    assert configure_response.json() == {"detail": "Authentication required."}
    assert status_response.json() == {"detail": "Authentication required."}


@pytest.mark.parametrize(
    ("connection", "expected"),
    [
        (None, {"connected": False}),
        (("https://erp.example.com", "key", "secret"), {"connected": True}),
    ],
)
def test_connection_status_returns_per_user_state(
    unauthenticated_app, monkeypatch, connection, expected
):
    monkeypatch.setattr(
        twynity,
        "get_current_user",
        lambda: {"id": "user-123", "email": "person@example.com"},
    )
    seen_user_ids = []

    async def get_connection(user_id):
        seen_user_ids.append(user_id)
        return connection

    monkeypatch.setattr(twynity, "get_connection", get_connection)
    response = TestClient(unauthenticated_app).get("/api/v1/external-connection/me")

    assert response.status_code == 200
    assert response.json() == expected
    assert seen_user_ids == ["user-123"]
