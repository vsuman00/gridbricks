from datetime import date

import pytest

from gridbricks import cli
from gridbricks.config import Settings
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import audit, fetch_plan, import_scope, scope
from gridbricks.sources.elexon import SourceError
from gridbricks.storage.repository import Repository


def test_january_fixture_is_repeatable_and_retains_february_boundary(tmp_path):
    settings = Settings(tmp_path)
    start, end = date(2026, 1, 1), date(2026, 1, 31)
    first = import_scope(settings, FixtureSource(), start, end, "fixture")
    second = import_scope(settings, FixtureSource(), start, end, "fixture")
    assert first["input_hash"] == second["input_hash"]
    assert first["counts"] == second["counts"]
    counts = first["counts"]
    assert counts["expected_forecast_targets"] == 744
    assert counts["expected_actual_targets"] == 1488
    assert counts["missing_forecast_targets"] == 1
    assert counts["missing_actual_targets"] == 1
    assert counts["completed_windows"] == 69
    rows = Repository(settings).observations(
        first["id"], "FUELHH", "2026-02-01T23:30:00Z", "2026-02-02T00:00:00Z"
    )
    assert len(rows) == 1
    assert len(Repository(settings).last_import()["windows"]) == 69
    report = audit(settings)
    assert report["comparison_available"] is True
    assert report["analysis"]["coverage"]["expected_count"] == 744
    assert report["analysis"]["coverage"]["matched_count"] == 741
    assert report["analysis"]["coverage"]["reason_counts"] == {
        "forecast_conflict": 1,
        "missing_forecast": 1,
        "missing_actual": 1,
        "matched": 741,
    }


def test_failed_window_is_not_missing_and_resume_uses_preserved_raw(tmp_path):
    class FailsThird(FixtureSource):
        count = 0

        def fetch(self, dataset, params):
            self.count += 1
            if self.count == 3:
                raise SourceError("source_retry_exhausted")
            return super().fetch(dataset, params)

    settings = Settings(tmp_path)
    with pytest.raises(SourceError):
        import_scope(settings, FailsThird(), source_mode="fixture")
    repository = Repository(settings)
    failed = repository.last_import()
    assert repository.get_snapshot() is None
    assert failed["counts"]["completed_windows"] == 2
    assert "missing_forecast_targets" not in failed["counts"]
    assert len([window for window in failed["windows"] if window["status"] == "failed"]) == 1

    class Records(FixtureSource):
        calls = []

        def fetch(self, dataset, params):
            self.calls.append((dataset, params))
            return super().fetch(dataset, params)

    source = Records()
    snapshot = import_scope(settings, source, source_mode="fixture")
    assert snapshot is not None
    assert len(source.calls) == len(fetch_plan(scope(date(2026, 1, 15), date(2026, 1, 15)))) - 2
    assert (
        len(
            [
                window
                for window in repository.last_import()["windows"]
                if window["status"] == "resumed"
            ]
        )
        == 2
    )


def test_january_audit_keeps_full_grid_for_a_one_day_active_snapshot(tmp_path):
    settings = Settings(tmp_path)
    snapshot = import_scope(settings, FixtureSource(), source_mode="fixture")
    assert snapshot["counts"]["expected_forecast_targets"] == 24
    report = audit(settings)
    analysis = report["analysis"]
    assert analysis["meta"]["decision_from"] == "2026-01-01"
    assert analysis["meta"]["decision_to"] == "2026-01-31"
    assert analysis["meta"]["delivery_to"] == "2026-02-01"
    coverage = analysis["coverage"]
    assert coverage["expected_count"] == 744
    assert coverage["forecast_selected_count"] == 23
    assert coverage["complete_actual_count"] == 24
    assert coverage["matched_count"] == 23
    assert coverage["matched_fraction"] == pytest.approx(23 / 744)
    reasons = coverage["reason_counts"]
    assert reasons["matched"] == 23
    assert reasons["forecast_conflict"] == 1
    assert reasons.get("missing_forecast", 0) + reasons.get("history_window_exhausted", 0) == 720
    assert sum(reasons.values()) == 744
    assert report["snapshot"]["bounds"]["decision_from"] == "2026-01-15"
    assert report["snapshot"]["bounds"]["decision_to"] == "2026-01-15"


def test_cli_january_audit_rejects_narrowing_decision_bounds(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["audit-january", "--data-dir", str(tmp_path), "--decision-from", "2026-01-15"])
    assert error.value.code == 2
    assert "audit-january always covers 1-31 January 2026" in capsys.readouterr().err
    assert not (tmp_path / "gridbricks.sqlite3").exists()
