"""Black-box HTTP probes against an owned real Uvicorn process on loopback."""

import json
import os
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest


def send(port, path="/api/v1/health", method="GET", headers=None):
    request = Request(f"http://127.0.0.1:{port}{path}", method=method, headers=headers or {})
    try:
        response = urlopen(request, timeout=3)
    except HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers.items()), response.read()


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    runtime = tmp_path_factory.mktemp("blackbox-runtime")
    # Pass the bound descriptor to Uvicorn instead of racing another process for a free port.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "gridbricks.main:app",
            "--fd",
            str(listener.fileno()),
            "--no-access-log",
            "--log-level",
            "warning",
        ],
        pass_fds=(listener.fileno(),),
        cwd=runtime,
        env={**os.environ, "GRIDBRICKS_DATA_DIR": str(runtime / "not-created")},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    listener.close()
    try:
        deadline = time.monotonic() + 5
        while True:
            if process.poll() is not None:
                raise AssertionError(f"Uvicorn exited before startup: {process.communicate()}")
            try:
                if send(port)[0] == 200:
                    break
            except (URLError, TimeoutError, ConnectionError):
                pass
            if time.monotonic() >= deadline:
                raise AssertionError("Uvicorn did not become ready within five seconds")
            time.sleep(0.02)
        yield port, runtime
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_real_server_health_and_headers(server):
    status, headers, body = send(server[0])
    assert status == 200
    assert json.loads(body) == {"status": "ok"}
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["content-security-policy"].startswith("default-src 'none'")
    assert headers["x-frame-options"] == "DENY"
    assert "Strict-Transport-Security" not in headers


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT", "HEAD"])
def test_real_server_rejects_non_read_methods(server, method):
    status, _, _ = send(server[0], method=method)
    assert status == 405


@pytest.mark.parametrize("host", ["attacker.example", "localhost.attacker.example"])
def test_real_server_rejects_foreign_hosts(server, host):
    status, headers, _ = send(server[0], headers={"Host": host})
    assert status == 400
    assert headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "origin", ["https://attacker.example", "null", "http://localhost:5173.attacker.example"]
)
def test_real_server_never_grants_unlisted_browser_origins(server, origin):
    status, headers, _ = send(server[0], headers={"Origin": origin})
    assert status == 200
    assert "access-control-allow-origin" not in headers


def test_real_server_local_origin_and_forbidden_preflight(server):
    status, headers, _ = send(server[0], headers={"Origin": "http://127.0.0.1:5173"})
    assert status == 200
    assert headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    status, _, _ = send(
        server[0],
        method="OPTIONS",
        headers={"Origin": "https://attacker.example", "Access-Control-Request-Method": "GET"},
    )
    assert status == 400


@pytest.mark.parametrize(
    "path",
    ["/.env", "/docs", "/openapi.json", "/..%2f..%2fetc/passwd", "/api/v1/ingest"],
)
def test_real_server_does_not_expose_files_docs_or_writes(server, path):
    status, headers, body = send(server[0], path)
    assert status == 404
    assert headers["x-content-type-options"] == "nosniff"
    assert b"Traceback" not in body
    assert b"root:" not in body


def test_real_server_bounds_query_and_rejects_injection_without_side_effects(server):
    probes = ["<script>alert(1)</script>", "' OR 1=1 --", "$(touch injected)", "../../.env"]
    for probe in probes:
        status, _, body = send(server[0], "/api/v1/health?" + urlencode({"probe": probe}))
        assert status == 422
        assert json.loads(body)["error"]["details"] == {"unknown_parameters": ["probe"]}
        assert probe.encode() not in body
    status, _, body = send(server[0], "/api/v1/health?" + "x" * 4096)
    assert status == 422
    assert json.loads(body)["error"]["code"] == "query_too_large"
    assert len(body) < 300
    assert list(server[1].iterdir()) == []


def test_real_http_parser_rejects_malformed_headers(server):
    with socket.create_connection(("127.0.0.1", server[0]), timeout=3) as connection:
        connection.sendall(b"GET /api/v1/health HTTP/1.1\r\nHost: 127.0.0.1\r\nX-Bad: \x00\r\n\r\n")
        response = connection.recv(4096)
    assert response.startswith(b"HTTP/1.1 400 ")


@pytest.mark.parametrize(
    "path", ["/api/v1/data-status", "/api/v1/forecast", "/api/v1/accuracy", "/api/v1/export"]
)
def test_analytical_routes_cannot_be_used_as_write_endpoints(server, path):
    status, headers, body = send(server[0], path, method="POST")
    assert status == 405
    assert headers["x-content-type-options"] == "nosniff"
    assert b"Traceback" not in body
    assert list(server[1].iterdir()) == []


@pytest.mark.parametrize("path", ["data-status", "forecast", "accuracy", "export"])
def test_analytical_routes_bound_query_size_before_work(server, path):
    status, _, body = send(server[0], f"/api/v1/{path}?" + "x" * 3000)
    assert status == 422
    assert json.loads(body)["error"]["code"] == "query_too_large"
    assert len(body) < 300
    assert list(server[1].iterdir()) == []


@pytest.mark.parametrize("value", ["' OR 1=1 --", "../../.env", "<script>alert(1)</script>"])
def test_analytical_snapshot_probes_are_rejected_without_echo_or_storage_creation(server, value):
    status, _, body = send(server[0], "/api/v1/data-status?" + urlencode({"snapshot_id": value}))
    assert status == 422
    assert value.encode() not in body
    assert list(server[1].iterdir()) == []


def test_missing_analytical_dataset_is_not_a_source_download_or_write(server):
    status, _, body = send(server[0], "/api/v1/forecast?decision_date=2026-01-15&cutoff=09:30")
    assert status == 503
    assert json.loads(body)["error"]["code"] == "dataset_unavailable"
    assert list(server[1].iterdir()) == []
