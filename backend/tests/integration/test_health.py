import pytest
from fastapi.testclient import TestClient

from gridbricks.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app(), base_url="http://127.0.0.1") as test_client:
        yield test_client


def test_health_reports_process_status_without_data_claims(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_root_points_to_frontend_and_short_health_alias_works(client):
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307
    assert root.headers["location"] == "http://127.0.0.1:5173/"
    assert root.headers["x-content-type-options"] == "nosniff"
    alias = client.get("/health")
    assert alias.status_code == 200
    assert alias.json() == {"status": "ok"}
    invalid = client.get("/health?unexpected=1")
    assert invalid.status_code == 422


def test_health_rejects_unknown_query_parameters(client):
    response = client.get("/api/v1/health?unexpected=1")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_query",
            "message": "The health endpoint does not accept query parameters.",
            "details": {"unknown_parameters": ["unexpected"]},
        }
    }


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173"])
def test_health_allows_explicit_development_origins(client, origin):
    response = client.get("/api/v1/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers


def test_health_does_not_allow_an_unlisted_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_health_is_read_only(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405


def test_cors_preflight_does_not_authorize_writes(client):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert response.headers["access-control-allow-methods"] == "GET"
