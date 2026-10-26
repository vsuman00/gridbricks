"""Source-aware security checks for the current read-only API surface."""

import socket
from urllib import request

import pytest
from fastapi.testclient import TestClient

from gridbricks.main import create_app

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "cache-control": "no-store",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
}


@pytest.fixture
def client():
    with TestClient(create_app(), base_url="http://127.0.0.1") as test_client:
        yield test_client


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.1:8000", "localhost:8000"])
def test_explicit_loopback_hosts_are_allowed(client, host):
    assert client.get("/api/v1/health", headers={"Host": host}).status_code == 200


@pytest.mark.parametrize("host", ["attacker.example", "localhost.attacker.example", "evil:8000"])
def test_other_hosts_are_rejected_before_route_execution(client, host):
    response = client.get("/api/v1/health", headers={"Host": host})
    assert response.status_code == 400
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("GET", "/api/v1/health", 200),
        ("GET", "/api/v1/health?unknown=1", 422),
        ("POST", "/api/v1/health", 405),
        ("GET", "/missing", 404),
    ],
)
def test_security_headers_cover_success_and_client_errors(client, method, path, expected):
    response = client.request(method, path)
    assert response.status_code == expected
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_unused_schema_and_docs_routes_are_not_exposed(client, path):
    assert client.get(path).status_code == 404


def test_oversized_query_is_rejected_before_parsing_or_reflection(client):
    response = client.get("/api/v1/health?" + "x" * 2049)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "query_too_large"
    assert len(response.content) < 300


def test_query_at_limit_remains_a_normal_unknown_parameter_error(client):
    response = client.get("/api/v1/health?" + "x" * 2048)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_query"


@pytest.mark.parametrize(
    "probe",
    ["<script>alert(1)</script>", "' OR 1=1 --", "$(touch injected)", "../../.env"],
)
def test_query_probe_values_are_rejected_without_being_echoed(client, probe):
    response = client.get("/api/v1/health", params={"probe": probe})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    assert probe not in response.text
    assert response.json()["error"]["details"] == {"unknown_parameters": ["probe"]}


def test_process_health_has_no_network_or_runtime_file_side_effects(monkeypatch, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("A health request attempted an outbound network operation")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(request, "urlopen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert list(tmp_path.iterdir()) == []


def test_unhandled_failure_is_generic_and_keeps_security_headers():
    app = create_app()

    @app.get("/__test__/failure")
    def failure():
        raise RuntimeError("private-test-error-detail")

    with TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False) as client:
        response = client.get("/__test__/failure")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An internal error occurred.", "details": {}}
    }
    assert "private-test-error-detail" not in response.text
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value
