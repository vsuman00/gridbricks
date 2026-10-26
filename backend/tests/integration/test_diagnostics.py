import json

import pytest
from fastapi.testclient import TestClient

from gridbricks.config import Settings
from gridbricks.diagnostics import safe_code
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import import_scope
from gridbricks.main import create_app
from gridbricks.sources.elexon import SourceError


def recorded(caplog):
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "gridbricks.events"
    ]


def test_http_event_correlates_response_with_validated_snapshot_and_bounds(tmp_path, caplog):
    settings = Settings(tmp_path)
    snapshot = import_scope(settings, FixtureSource(), source_mode="fixture")
    caplog.clear()
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        response = client.get(
            "/api/v1/forecast",
            params={
                "decision_date": "2026-01-15",
                "cutoff": "09:30",
                "snapshot_id": snapshot["id"],
            },
        )
    assert response.status_code == 200
    [event] = [event for event in recorded(caplog) if event["event"] == "http_request"]
    assert event["request_id"] == response.headers["x-request-id"]
    assert event["route"] == "/api/v1/forecast"
    assert event["snapshot_id"] == snapshot["id"]
    assert (event["decision_from"], event["decision_to"], event["cutoff_local"]) == (
        "2026-01-15",
        "2026-01-15",
        "09:30",
    )
    assert event["status_code"] == 200 and event["error_code"] is None
    assert event["duration_ms"] >= 0


def test_http_error_event_omits_untrusted_query_text(tmp_path, caplog):
    with TestClient(create_app(Settings(tmp_path)), base_url="http://127.0.0.1") as client:
        response = client.get("/api/v1/data-status?snapshot_id=secret-token=<script>")
        oversized = client.get("/api/v1/health?" + "SENSITIVE" * 400)
    assert response.status_code == 422 and oversized.status_code == 422
    output = "\n".join(record.message for record in caplog.records)
    assert "secret-token" not in output
    assert "<script>" not in output
    assert "SENSITIVE" not in output
    events = recorded(caplog)
    assert [event["error_code"] for event in events] == ["invalid_query", "query_too_large"]
    assert all(event["snapshot_id"] is None for event in events)
    assert all(event["request_id"] for event in events)


def test_import_events_include_window_counts_and_published_manifest(tmp_path, caplog):
    snapshot = import_scope(Settings(tmp_path), FixtureSource(), source_mode="fixture")
    events = recorded(caplog)
    started = next(event for event in events if event["event"] == "import_started")
    windows = [event for event in events if event["event"] == "import_window_finished"]
    published = next(event for event in events if event["event"] == "import_published")
    assert len(windows) == started["planned_windows"]
    assert all(event["run_id"] == started["run_id"] for event in events)
    assert all(event["dataset"] in {"WINDFOR", "FUELHH"} for event in windows)
    assert all(event["attempts"] == 1 and event["observed_count"] >= 0 for event in windows)
    assert published["snapshot_id"] == snapshot["id"]
    assert published["manifest_hash"] == snapshot["manifest_hash"]
    assert published["counts"]["completed_windows"] == len(windows)
    assert all("request_url" not in event and "body" not in event for event in events)


def test_failed_retrieval_is_logged_separately_from_missing_records(tmp_path, caplog):
    class FailingSource:
        last_attempt_count = 3

        def fetch(self, dataset, parameters):
            raise SourceError("source_retry_exhausted")

    with pytest.raises(SourceError):
        import_scope(Settings(tmp_path), FailingSource(), source_mode="fixture")
    events = recorded(caplog)
    failed_window = next(event for event in events if event["event"] == "import_window_failed")
    failed_run = next(event for event in events if event["event"] == "import_failed")
    assert failed_window["attempts"] == 3
    assert failed_window["window_from"] and failed_window["window_to"]
    assert failed_window["error_code"] == failed_run["error_code"] == "source_retry_exhausted"
    assert failed_run["completed_windows"] == 0
    assert not any(event["event"] == "import_published" for event in events)
    assert safe_code("token=secret") == "unclassified_error"
