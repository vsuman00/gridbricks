from datetime import UTC, datetime

from gridbricks.analytics.grid import target_grid
from gridbricks.analytics.selection import select_forecast


def record(value, publication, identity="row"):
    return {
        "id": identity,
        "generation_mw": value,
        "publish_time_utc": publication,
        "quality_flags": [],
    }


def test_grid_uses_next_london_day_and_january_month_boundary():
    rows = target_grid("2026-01-31", "09:30")
    assert len(rows) == 24
    assert rows[0]["target_start"] == "2026-02-01T00:00:00Z"
    assert rows[-1]["target_end"] == "2026-02-02T00:00:00Z"
    assert rows[0]["cutoff_utc"] == "2026-01-31T09:30:00Z"


def test_exact_cutoff_is_eligible_and_later_revision_is_excluded():
    rows = [
        record(100, "2026-01-15T08:30:00Z"),
        record(110, "2026-01-15T09:30:00Z", "at-cutoff"),
        record(140, "2026-01-15T10:30:00Z"),
    ]
    selected, state, _ = select_forecast(rows, datetime(2026, 1, 15, 9, 30, tzinfo=UTC))
    assert state == "selected"
    assert selected["id"] == "at-cutoff"
    assert selected["generation_mw"] == 110


def test_newest_conflict_is_unresolved_without_fallback_or_row_order_choice():
    rows = [record(90, "2026-01-14T08:30:00Z"), record(100, "2026-01-15T08:30:00Z")]
    rows.append(record(101, "2026-01-15T08:30:00Z", "conflict"))
    for values in (rows, list(reversed(rows))):
        selected, state, _ = select_forecast(values, datetime(2026, 1, 15, 9, 30, tzinfo=UTC))
        assert selected is None
        assert state == "forecast_conflict"


def test_older_publication_zero_and_exact_duplicate_are_valid():
    row = record(0, "2026-01-13T08:30:00Z")
    selected, state, _ = select_forecast([row, dict(row)], datetime(2026, 1, 15, tzinfo=UTC))
    assert state == "selected"
    assert selected["generation_mw"] == 0


def test_invalid_newest_value_never_silently_falls_back():
    rows = [record(90, "2026-01-14T08:30:00Z"), record(None, "2026-01-15T08:30:00Z")]
    selected, state, flags = select_forecast(rows, datetime(2026, 1, 15, 9, 30, tzinfo=UTC))
    assert selected is None
    assert state == "missing_forecast"
    assert "invalid_forecast_value" in flags
