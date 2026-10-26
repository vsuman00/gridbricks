import csv
import io
import math

import pytest

from gridbricks.api.export import export_csv, spreadsheet_safe
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import import_scope


def read_csv(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    return list(csv.DictReader(io.StringIO(response.text)))


def test_export_requires_an_explicit_snapshot_and_consistent_view_parameters(analytical_dataset):
    client, _, _ = analytical_dataset
    for query in (
        "view=forecast&decision_date=2026-01-15&cutoff=09:30",
        "view=other&decision_date=2026-01-15&cutoff=09:30&snapshot_id=x",
        "view=forecast&decision_date=2026-01-15&decision_from=2026-01-01&cutoff=09:30&snapshot_id=x",
    ):
        assert client.get("/api/v1/export?" + query).status_code == 422


def test_forecast_csv_retains_every_grid_row_gap_and_selected_publication(analytical_dataset):
    client, _, snapshot = analytical_dataset
    query = {"decision_date": "2026-01-15", "cutoff": "09:30", "snapshot_id": snapshot["id"]}
    analysis = client.get("/api/v1/forecast", params=query).json()
    rows = read_csv(client.get("/api/v1/export", params={**query, "view": "forecast"}))
    assert len(rows) == len(analysis["rows"]) == 24
    for exported, shown in zip(rows, analysis["rows"], strict=True):
        assert exported["snapshot_id"] == snapshot["id"]
        assert exported["target_start"] == shown["target_start"]
        assert exported["state"] == shown["state"]
        assert exported["forecast_publish_time"] == (shown["forecast_publish_time"] or "")
        if shown["forecast_mw"] is None:
            assert exported["forecast_mw"] == ""
        else:
            assert float(exported["forecast_mw"]) == shown["forecast_mw"]
    assert rows[3]["forecast_mw"] == ""
    assert rows[3]["state"] == "forecast_conflict"
    assert "fixture://synthetic/" in str(rows[0])


def test_accuracy_csv_recomputes_json_metrics_at_full_precision(analytical_dataset):
    client, _, snapshot = analytical_dataset
    query = {
        "decision_from": "2026-01-15",
        "decision_to": "2026-01-15",
        "cutoff": "09:30",
        "snapshot_id": snapshot["id"],
    }
    data = client.get("/api/v1/accuracy", params=query).json()
    rows = read_csv(client.get("/api/v1/export", params={**query, "view": "accuracy"}))
    assert len(rows) == data["coverage"]["expected_count"]
    errors = [float(row["error_mw"]) for row in rows if row["state"] == "matched"]
    assert len(errors) == data["coverage"]["matched_count"]
    assert data["metrics"]["mae_mw"] == pytest.approx(sum(map(abs, errors)) / len(errors))
    assert data["metrics"]["rmse_mw"] == pytest.approx(
        math.sqrt(sum(v * v for v in errors) / len(errors))
    )
    assert data["metrics"]["bias_mw"] == pytest.approx(sum(errors) / len(errors))
    assert rows[0]["alignment_policy"] == "timestamp_matched_halfhour_reference_v1"
    assert any("actual" in key and "publish" in key for key in rows[0])
    assert "temporal_reference_mismatch" in str(rows[0])


def test_csv_from_a_pinned_snapshot_survives_a_later_active_import(analytical_dataset):
    client, settings, snapshot = analytical_dataset
    query = {
        "view": "forecast",
        "decision_date": "2026-01-15",
        "cutoff": "09:30",
        "snapshot_id": snapshot["id"],
    }
    before = client.get("/api/v1/export", params=query)
    assert before.status_code == 200
    newer = import_scope(
        settings, FixtureSource(), source_mode="fixture", policies=snapshot["policies"]
    )
    assert newer["id"] != snapshot["id"]
    after = client.get("/api/v1/export", params=query)
    assert after.status_code == 200
    assert after.text == before.text


@pytest.mark.parametrize(
    "value", ["=1+1", "+SUM(A1)", "-formula", "@SUM(A1)", "\t=1", "\r=1", "\n=1"]
)
def test_free_text_formula_prefixes_are_escaped(value):
    assert spreadsheet_safe(value) == "'" + value


def test_numeric_negative_errors_remain_numeric_and_csv_quotes_lineage(analytical_dataset):
    client, _, snapshot = analytical_dataset
    response = client.get(
        "/api/v1/accuracy",
        params={
            "decision_from": "2026-01-15",
            "decision_to": "2026-01-15",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        },
    ).json()
    response["meta"]["comparison_note"] = '=HYPERLINK("https://example.invalid")'
    response["rows"][0]["error_mw"] = -20.125
    response["rows"][0]["forecast_sources"][0]["request_url"] = (
        'fixture://source/with,"quotes"\nand newline'
    )
    text = export_csv(response, accuracy=True)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 24
    assert rows[0]["error_mw"] == "-20.125"
    assert rows[0]["comparison_note"].startswith("'=")
    assert spreadsheet_safe(-20.125) == -20.125
