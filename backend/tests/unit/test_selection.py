import json
from datetime import UTC, datetime
from itertools import permutations
from pathlib import Path

import pytest

from gridbricks.analytics.selection import select_forecast

CUTOFF = datetime(2026, 1, 15, 9, 30, tzinfo=UTC)


def test_named_synthetic_revision_fixture_reconstructs_100_not_140():
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/cutoff_revisions.json").read_text())
    selected, state, _ = select_forecast(fixture["observations"], CUTOFF)
    assert state == "selected"
    assert selected["generation_mw"] == 100
    assert len(fixture["observations"]) == 3


def observation(value, publication, identity="observation", flags=None):
    return {
        "id": identity,
        "generation_mw": value,
        "publish_time_utc": publication,
        "quality_flags": flags or [],
    }


def test_cutoff_one_second_boundary_uses_actual_publication_offsets():
    records = [
        observation(100, "2026-01-15T08:30:00Z", "earlier"),
        observation(110, "2026-01-15T10:30:00+01:00", "equal"),
        observation(140, "2026-01-15T09:30:01Z", "future"),
    ]
    selected, state, _ = select_forecast(records, CUTOFF)
    assert state == "selected"
    assert selected["id"] == "equal"
    assert selected["generation_mw"] == 110


def test_all_insertion_orders_preserve_newest_conflict_without_older_fallback():
    records = [
        observation(90, "2026-01-14T08:30:00Z", "old"),
        observation(100, "2026-01-15T08:30:00Z", "new-a"),
        observation(101, "2026-01-15T08:30:00Z", "new-b"),
    ]
    for ordering in permutations(records):
        selected, state, _ = select_forecast(list(ordering), CUTOFF)
        assert selected is None
        assert state == "forecast_conflict"


def test_old_conflict_does_not_invalidate_a_new_unambiguous_publication():
    rows = [
        observation(90, "2026-01-14T08:30:00Z", "old-a"),
        observation(91, "2026-01-14T08:30:00Z", "old-b"),
        observation(-2, "2026-01-15T08:30:00Z", "new"),
    ]
    selected, state, _ = select_forecast(rows, CUTOFF)
    assert state == "selected"
    assert selected["generation_mw"] == -2


def test_only_future_publications_and_absent_records_remain_missing():
    for records in ([], [observation(140, "2026-01-15T10:30:00Z")]):
        selected, state, _ = select_forecast(records, CUTOFF)
        assert selected is None
        assert state == "missing_forecast"


@pytest.mark.parametrize("invalid", [None, float("nan"), float("inf"), -float("inf")])
def test_nonfinite_latest_forecast_cannot_reveal_an_older_valid_value(invalid):
    rows = [
        observation(90, "2026-01-14T08:30:00Z", "old"),
        observation(invalid, "2026-01-15T08:30:00Z", "new"),
    ]
    selected, state, flags = select_forecast(rows, CUTOFF)
    assert selected is None
    assert state == "missing_forecast"
    assert "invalid_forecast_value" in flags


def test_selection_rejects_naive_cutoff_to_avoid_machine_timezone_dependence():
    with pytest.raises(ValueError, match="offset"):
        select_forecast([], datetime(2026, 1, 15, 9, 30))


def test_zero_duplicates_retain_quality_flags_without_mutating_input():
    rows = [
        observation(0, "2026-01-13T08:30:00Z", "b", ["source_note"]),
        observation(0, "2026-01-13T08:30:00Z", "a"),
    ]
    selected, state, flags = select_forecast(rows, CUTOFF)
    assert state == "selected"
    assert selected["generation_mw"] == 0
    assert flags == ["source_note"]
    assert [r["id"] for r in rows] == ["b", "a"]
