import math

import pytest

from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import import_scope


def test_accuracy_uses_exact_time_actuals_and_reports_benchmark_policy(analytical_dataset):
    client, _, snapshot = analytical_dataset
    response = client.get(
        "/api/v1/accuracy",
        params={
            "decision_from": "2026-01-15",
            "decision_to": "2026-01-15",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["meta"]["evaluation_mode"] == "retrospective"
    assert data["meta"]["alignment_policy"] == "timestamp_matched_halfhour_reference_v1"
    assert data["coverage"]["expected_count"] == 24
    assert data["coverage"]["matched_count"] == 23
    assert data["rows"][0]["actual_mw"] == 0
    assert data["rows"][0]["error_mw"] == 100
    for row in data["rows"]:
        assert "temporal_reference_mismatch" in row["flags"]
        if row["state"] == "matched":
            assert len(row["actual_constituents"]) == 1
            constituent = row["actual_constituents"][0]
            assert constituent["raw_sources"]
            assert row["error_mw"] == row["forecast_mw"] - row["actual_mw"]
    errors = [row["error_mw"] for row in data["rows"] if row["state"] == "matched"]
    assert data["metrics"]["mae_mw"] == pytest.approx(sum(abs(v) for v in errors) / len(errors))
    assert data["metrics"]["rmse_mw"] == pytest.approx(
        math.sqrt(sum(v * v for v in errors) / len(errors))
    )
    assert data["metrics"]["bias_mw"] == pytest.approx(sum(errors) / len(errors))


def test_unknown_alignment_returns_conflict_instead_of_inventing_accuracy(analytical_dataset):
    client, settings, _ = analytical_dataset
    snapshot = import_scope(
        settings,
        FixtureSource(),
        source_mode="fixture",
        policies={
            "selection": "asof_per_target_v1",
            "alignment": "unverified",
            "actual": "latest_in_snapshot_v1",
            "metric": "pooled_mw_v1",
        },
    )
    response = client.get(
        "/api/v1/accuracy",
        params={
            "decision_from": "2026-01-15",
            "decision_to": "2026-01-15",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "alignment_unverified"
    forecast = client.get("/api/v1/forecast?decision_date=2026-01-15&cutoff=09:30")
    assert forecast.status_code == 200


def test_status_does_not_verify_a_partly_unsupported_comparison_policy(analytical_dataset):
    client, settings, _ = analytical_dataset
    policies = {
        "selection": "asof_per_target_v1",
        "alignment": "timestamp_matched_halfhour_reference_v1",
        "actual": "latest_in_snapshot_v1",
        "metric": "unknown_metric_v1",
    }
    snapshot = import_scope(settings, FixtureSource(), source_mode="fixture", policies=policies)
    status = client.get("/api/v1/data-status", params={"snapshot_id": snapshot["id"]})
    assert status.status_code == 200
    assert status.json()["alignment"] == {
        "verified": False,
        "policy": "timestamp_matched_halfhour_reference_v1",
        "message": "Comparison policy unavailable.",
    }
    response = client.get(
        "/api/v1/accuracy",
        params={
            "decision_from": "2026-01-15",
            "decision_to": "2026-01-15",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "alignment_unverified"


def test_all_missing_forecasts_return_sparse_success_with_null_metrics(analytical_dataset):
    client, _, snapshot = analytical_dataset
    response = client.get(
        "/api/v1/accuracy",
        params={
            "decision_from": "2026-01-01",
            "decision_to": "2026-01-01",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["rows"]) == data["coverage"]["expected_count"] == 24
    assert data["coverage"]["matched_count"] == 0
    assert all(value is None for value in data["metrics"].values())
    assert sum(data["coverage"]["reason_counts"].values()) == 24


def test_range_metrics_pool_returned_rows_and_each_day_has_its_own_cutoff(january_dataset):
    client, _, snapshot = january_dataset
    response = client.get(
        "/api/v1/accuracy",
        params={
            "decision_from": "2026-01-01",
            "decision_to": "2026-01-31",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["rows"]) == 744
    assert len(data["daily"]) == 31
    assert data["rows"][-1]["target_start"].startswith("2026-02-01T23:00")
    for row in data["rows"]:
        assert row["cutoff_utc"].startswith(row["decision_date"] + "T09:30")
    errors = [row["error_mw"] for row in data["rows"] if row["state"] == "matched"]
    assert data["coverage"]["matched_count"] == len(errors)
    assert sum(row["matched_count"] for row in data["daily"]) == len(errors)
    assert data["metrics"]["bias_mw"] == pytest.approx(sum(errors) / len(errors))
    assert data["metrics"]["mae_mw"] == pytest.approx(sum(abs(v) for v in errors) / len(errors))
    assert sum(data["coverage"]["reason_counts"].values()) == 744


def test_accuracy_rejects_reversed_range_and_inconsistent_view_parameters(analytical_dataset):
    client, _, _ = analytical_dataset
    for query in (
        "decision_from=2026-01-31&decision_to=2026-01-01&cutoff=09:30",
        "decision_from=2026-01-01&decision_to=2026-02-01&cutoff=09:30",
        "decision_from=2026-01-01&decision_to=2026-01-31&cutoff=09:30&decision_date=2026-01-15",
    ):
        assert client.get("/api/v1/accuracy?" + query).status_code == 422
