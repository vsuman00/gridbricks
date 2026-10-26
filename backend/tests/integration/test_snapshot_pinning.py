import json

import pytest

from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import import_scope
from gridbricks.storage.repository import Repository


class ChangedFixture:
    def fetch(self, dataset, parameters):
        url, body, status = FixtureSource().fetch(dataset, parameters)
        rows = json.loads(body)
        if dataset == "WINDFOR":
            for row in rows:
                row["generation"] += 50
        return url + "&revision=changed", json.dumps(rows).encode(), status


def query(client, snapshot_id=None):
    parameters = {"decision_date": "2026-01-15", "cutoff": "09:30"}
    if snapshot_id:
        parameters["snapshot_id"] = snapshot_id
    return client.get("/api/v1/forecast", params=parameters)


def test_active_refresh_cannot_change_explicit_snapshot_rows_or_raw_lineage(analytical_dataset):
    client, settings, original = analytical_dataset
    before = query(client, original["id"]).json()
    changed = import_scope(
        settings, ChangedFixture(), source_mode="fixture", policies=original["policies"]
    )
    assert changed["id"] != original["id"]
    assert changed["input_hash"] != original["input_hash"]
    assert query(client).json()["rows"][0]["forecast_mw"] == 150
    after = query(client, original["id"]).json()
    assert after == before
    assert after["rows"][0]["forecast_mw"] == 100


def test_failed_refresh_retains_active_forecast_and_exposes_last_failure(analytical_dataset):
    client, settings, original = analytical_dataset
    before = query(client).json()

    class FailedSource:
        def fetch(self, dataset, parameters):
            raise TimeoutError("Synthetic transport failure")

    with pytest.raises(TimeoutError):
        import_scope(settings, FailedSource(), source_mode="fixture", policies=original["policies"])
    assert Repository(settings).get_snapshot()["id"] == original["id"]
    assert query(client).json() == before
    status = client.get("/api/v1/data-status").json()
    assert status["snapshot"]["snapshot_id"] == original["id"]
    assert status["last_import"]["status"] == "failed"


def test_first_query_resolves_active_snapshot_once_and_reuses_it_for_reads(analytical_dataset):
    client, settings, original = analytical_dataset
    repository = client.app.state.repository
    original_get_snapshot = repository.get_snapshot
    calls = []

    def observed_get_snapshot(snapshot_id=None):
        calls.append(snapshot_id)
        return original_get_snapshot(snapshot_id)

    repository.get_snapshot = observed_get_snapshot
    response = query(client)
    assert response.status_code == 200
    assert response.json()["meta"]["snapshot_id"] == original["id"]
    assert calls.count(None) == 1
    assert Repository(settings).get_snapshot()["id"] == original["id"]
