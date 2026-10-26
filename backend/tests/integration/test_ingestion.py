import json
from datetime import date

import httpx
import pytest

from gridbricks import cli
from gridbricks.config import Settings
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import import_scope
from gridbricks.ingestion.validation import PayloadError, validate
from gridbricks.sources.elexon import ElexonSource, SourceError, request_url
from gridbricks.storage.repository import Repository


class ReplacingSource(FixtureSource):
    def __init__(self, replace):
        self.replace = replace

    def fetch(self, dataset, parameters):
        url, body, status = super().fetch(dataset, parameters)
        return url, self.replace(dataset, body), status


def test_fixture_import_does_not_use_network_and_preserves_zero(tmp_path, monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Fixture import contacted the network")

    monkeypatch.setattr(httpx.Client, "get", forbid)
    settings = Settings(tmp_path)
    snapshot = import_scope(settings, FixtureSource(), source_mode="fixture")
    repository = Repository(settings)
    actuals = repository.observations(
        snapshot["id"], "FUELHH", "2026-01-16T00:00:00Z", "2026-01-17T00:00:00Z"
    )
    assert actuals[0]["generation_mw"] == 0
    assert snapshot["source_mode"] == "fixture"
    assert snapshot["counts"]["conflicting_keys"] == 2
    assert snapshot["status"] == "partial"


@pytest.mark.parametrize("body", [b"{", b"{}", b"[1]", b'[{"unexpected":1}]'])
def test_malformed_payload_retains_active_snapshot_and_raw(tmp_path, body):
    settings = Settings(tmp_path)
    initial = import_scope(settings, FixtureSource(), source_mode="fixture")
    bad = ReplacingSource(lambda dataset, original: body)
    with pytest.raises(PayloadError):
        import_scope(settings, bad, source_mode="fixture")
    repository = Repository(settings)
    assert repository.get_snapshot()["id"] == initial["id"]
    assert repository.last_import()["status"] == "failed"
    windows = repository.last_import()["windows"]
    assert {window["status"] for window in windows} == {"failed", "not_attempted"}
    assert sum(window["status"] == "failed" for window in windows) == 1
    assert any(path.read_bytes() == body for path in (tmp_path / "raw").iterdir())


def test_invalid_generation_retains_a_key_marker_and_partial_counts(tmp_path):
    def replace(dataset, body):
        rows = json.loads(body)
        if dataset == "WINDFOR":
            for row in rows:
                if row["startTime"] == "2026-01-16T01:00:00Z" and "09:30" in row["publishTime"]:
                    row["generation"] = None
        return json.dumps(rows).encode()

    settings = Settings(tmp_path)
    snapshot = import_scope(settings, ReplacingSource(replace), source_mode="fixture")
    rows = Repository(settings).observations(
        snapshot["id"], "WINDFOR", "2026-01-16T01:00:00Z", "2026-01-16T02:00:00Z"
    )
    invalid = [row for row in rows if "invalid_generation" in row["quality_flags"]]
    assert len(invalid) == 2
    assert all(row["generation_mw"] is None for row in invalid)
    assert snapshot["counts"]["invalid_generation"] > 0
    assert snapshot["status"] == "partial"


def test_invalid_timezone_or_subhour_timestamp_fails_schema():
    row = {
        "dataset": "WINDFOR",
        "startTime": "2026-01-16T01:00:00",
        "publishTime": "2026-01-15T09:30:00Z",
        "generation": 100,
    }
    with pytest.raises(PayloadError, match="invalid_timestamp"):
        validate(json.dumps([row]), "WINDFOR")
    row["startTime"] = "2026-01-16T01:30:00Z"
    with pytest.raises(PayloadError, match="invalid_timestamp"):
        validate(json.dumps([row]), "WINDFOR")


def test_nonwind_filtered_locally_and_wrong_dataset_rejected():
    row = {
        "dataset": "FUELHH",
        "startTime": "2026-01-16T01:00:00Z",
        "publishTime": "2026-01-16T01:30:00Z",
        "generation": 100,
        "fuelType": "GAS",
    }
    rows, counts = validate(json.dumps([row]), "FUELHH")
    assert rows == []
    assert counts["filtered_non_wind"] == 1
    with pytest.raises(PayloadError):
        validate(json.dumps([{**row, "dataset": "UNEXPECTED"}]), "FUELHH")


def test_source_uses_supported_explicit_filters_only():
    url = request_url(
        "FUELHH",
        {"settlementDateFrom": "2026-01-16", "settlementDateTo": "2026-01-16", "fuelType": "WIND"},
    )
    assert "fuelType=WIND" in url
    assert "settlementDateFrom=" in url
    assert "publishDateTime" not in url
    with pytest.raises(ValueError):
        request_url("WINDFOR", {})


@pytest.mark.parametrize("status,expected_calls", [(400, 1), (401, 1), (503, 3), (429, 3)])
def test_source_bounded_retries(status, expected_calls):
    calls, delays = [], []

    def handle(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Retry-After": "1"})

    source = ElexonSource(
        httpx.Client(transport=httpx.MockTransport(handle)), sleep=delays.append, jitter=lambda: 0
    )
    with pytest.raises(SourceError):
        source.fetch(
            "WINDFOR",
            {
                "publishDateTimeFrom": "2026-01-01T00:00:00Z",
                "publishDateTimeTo": "2026-01-02T00:00:00Z",
            },
        )
    assert len(calls) == expected_calls
    assert source.last_attempt_count == expected_calls
    assert len(delays) == expected_calls - 1
    assert sum(delays) <= 10


def test_retry_after_exceeding_budget_does_not_retry_early():
    calls, delays = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "30"})

    source = ElexonSource(httpx.Client(transport=httpx.MockTransport(handle)), sleep=delays.append)
    with pytest.raises(SourceError, match="budget_exceeded"):
        source.fetch(
            "WINDFOR",
            {
                "publishDateTimeFrom": "2026-01-01T00:00:00Z",
                "publishDateTimeTo": "2026-01-02T00:00:00Z",
            },
        )
    assert len(calls) == 1
    assert delays == []


def test_date_bounds_rejected_before_creating_database(tmp_path):
    with pytest.raises(ValueError):
        import_scope(
            Settings(tmp_path / "absent"),
            FixtureSource(),
            date(2026, 2, 1),
            date(2026, 2, 2),
            "fixture",
        )
    assert not (tmp_path / "absent").exists()


def test_source_closes_owned_client_but_preserves_injected_client():
    with ElexonSource() as owned:
        assert not owned.client.is_closed
    assert owned.client.is_closed
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        with ElexonSource(client) as injected:
            assert injected.client is client
        assert not client.is_closed


@pytest.mark.parametrize("fails", [False, True])
def test_cli_closes_live_client_on_success_or_failure(tmp_path, monkeypatch, fails, capsys):
    sources = []

    class TrackedSource:
        def __init__(self):
            self.closed = False
            sources.append(self)

        def close(self):
            self.closed = True

    def run_import(*args, **kwargs):
        if fails:
            raise SourceError("source_retry_exhausted")
        return {"status": "succeeded"}

    monkeypatch.setattr(cli, "ElexonSource", TrackedSource)
    monkeypatch.setattr(cli, "import_scope", run_import)
    assert cli.main(["ingest-sample", "--data-dir", str(tmp_path)]) == int(fails)
    assert sources[0].closed is True
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == ("failed" if fails else "succeeded")
