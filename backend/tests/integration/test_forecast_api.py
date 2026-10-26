from fastapi.testclient import TestClient

from gridbricks.analytics.grid import timestamp
from gridbricks.config import Settings
from gridbricks.main import create_app


def test_no_dataset_reports_unavailable_without_creating_storage(tmp_path):
    settings = Settings(tmp_path / "not-created")
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        status = client.get("/api/v1/data-status")
        assert status.status_code == 200
        assert status.json()["snapshot"] is None
        response = client.get("/api/v1/forecast?decision_date=2026-01-15&cutoff=09:30")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dataset_unavailable"
    assert not settings.data_dir.exists()


def test_forecast_selects_cutoff_vintage_and_preserves_full_grid(analytical_dataset):
    client, _, snapshot = analytical_dataset
    query = {"decision_date": "2026-01-15", "cutoff": "09:30", "snapshot_id": snapshot["id"]}
    response = client.get("/api/v1/forecast", params=query)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["meta"]["snapshot_id"] == snapshot["id"]
    assert data["meta"]["source_mode"] == "fixture"
    assert data["meta"]["timezone"] == "Europe/London"
    assert data["meta"]["unit"] == "MW"
    assert len(data["rows"]) == data["coverage"]["expected_count"] == 24
    first = data["rows"][0]
    assert first["forecast_mw"] == 100
    assert timestamp(first["forecast_publish_time"]) < timestamp(first["cutoff_utc"])
    assert first["forecast_age_hours"] == 1
    assert first["forecast_lead_hours"] == 15.5
    assert first["forecast_sources"]
    assert all(
        source["content_hash"] and source["retrieved_at"] for source in first["forecast_sources"]
    )
    for row in data["rows"]:
        assert not {"actual_mw", "actual_constituents", "error_mw"}.intersection(row)
        if row["forecast_publish_time"]:
            assert timestamp(row["forecast_publish_time"]) <= timestamp(row["cutoff_utc"])
    assert sum(data["coverage"]["reason_counts"].values()) == 24


def test_changing_cutoff_uses_newer_revision_without_mutating_prior_query(analytical_dataset):
    client, _, snapshot = analytical_dataset
    query = {"decision_date": "2026-01-15", "snapshot_id": snapshot["id"]}
    earlier = client.get("/api/v1/forecast", params={**query, "cutoff": "09:30"}).json()
    later = client.get("/api/v1/forecast", params={**query, "cutoff": "10:30"}).json()
    assert earlier["rows"][0]["forecast_mw"] == 100
    assert later["rows"][0]["forecast_mw"] == 140
    repeated = client.get("/api/v1/forecast", params={**query, "cutoff": "09:30"}).json()
    assert repeated == earlier


def test_forecast_conflict_has_no_older_or_postcutoff_fallback(analytical_dataset):
    client, _, snapshot = analytical_dataset
    response = client.get(
        "/api/v1/forecast",
        params={"decision_date": "2026-01-15", "cutoff": "09:30", "snapshot_id": snapshot["id"]},
    )
    row = response.json()["rows"][3]
    assert row["state"] == "forecast_conflict"
    assert row["forecast_mw"] is None
    assert response.json()["coverage"]["forecast_selected_count"] == 23


def test_forecast_rejects_unknown_repeated_malformed_and_out_of_scope_queries(analytical_dataset):
    client, _, _ = analytical_dataset
    urls = [
        "decision_date=2026-02-01&cutoff=09:30",
        "decision_date=2026-01-15&cutoff=9:30",
        "decision_date=2026-01-15&cutoff=24:00",
        "decision_date=2026-01-15&cutoff=09:30&unknown=1",
        "decision_date=2026-01-15&decision_date=2026-01-16&cutoff=09:30",
        "decision_date=2026-01-15&cutoff=09:30&cutoff=10:30",
        "cutoff=09:30",
    ]
    for query in urls:
        response = client.get("/api/v1/forecast?" + query)
        assert response.status_code == 422, (query, response.text)
        assert "error" in response.json()


def test_unknown_snapshot_is_distinct_from_absent_dataset(analytical_dataset):
    client, _, _ = analytical_dataset
    for path in (
        "data-status?snapshot_id=does-not-exist",
        "forecast?decision_date=2026-01-15&cutoff=09:30&snapshot_id=does-not-exist",
    ):
        response = client.get("/api/v1/" + path)
        assert response.status_code == 404


def test_january_31_forecast_has_february_1_targets(january_dataset):
    client, _, snapshot = january_dataset
    response = client.get(
        "/api/v1/forecast",
        params={"decision_date": "2026-01-31", "cutoff": "09:30", "snapshot_id": snapshot["id"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["delivery_from"] == data["meta"]["delivery_to"] == "2026-02-01"
    assert data["rows"][0]["target_start"].startswith("2026-02-01T00:00")
    assert data["rows"][-1]["target_end"].startswith("2026-02-02T00:00")
