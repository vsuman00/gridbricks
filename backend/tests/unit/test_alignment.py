import pytest

from gridbricks.analytics.alignment import align_actual

POLICY = "timestamp_matched_halfhour_reference_v1"
TARGET = "2026-01-16T00:00:00Z"


def actual(value, start=TARGET, publication="2026-01-16T00:30:00Z", identity="actual"):
    return {
        "id": identity,
        "dataset": "FUELHH",
        "fuel_type": "WIND",
        "generation_mw": value,
        "start_time_utc": start,
        "publish_time_utc": publication,
        "quality_flags": [],
    }


def test_benchmark_uses_one_exact_timestamp_halfhour_without_hourly_averaging():
    records = [actual(80), actual(120, "2026-01-16T00:30:00Z", identity="adjacent")]
    value, constituents, state, flags = align_actual(TARGET, records, POLICY)
    assert value == 80
    assert state == "matched"
    assert len(constituents) == 1
    assert constituents[0]["observation_id"] == "actual"
    assert constituents[0]["generation_mw"] == 80
    assert "temporal_reference_mismatch" in flags


def test_missing_exact_timestamp_cannot_be_filled_by_duplicate_adjacent_halfhours():
    row = actual(120, "2026-01-16T00:30:00Z", identity="adjacent")
    value, constituents, state, _ = align_actual(TARGET, [row, dict(row)], POLICY)
    assert value is None
    assert constituents == []
    assert state == "missing_actual"


def test_exact_timestamp_is_compared_in_utc_not_string_form():
    value, constituents, state, _ = align_actual(
        TARGET, [actual(0, "2026-01-16T01:00:00+01:00")], POLICY
    )
    assert value == 0
    assert len(constituents) == 1
    assert state == "matched"


def test_latest_actual_revision_is_used_but_latest_conflict_stays_unresolved():
    initial = actual(80)
    revised = actual(85, publication="2026-01-20T12:00:00Z", identity="revised")
    value, constituents, state, _ = align_actual(TARGET, [initial, revised], POLICY)
    assert value == 85
    assert constituents[0]["observation_id"] == "revised"
    assert state == "matched"
    conflict = {**revised, "id": "conflict", "generation_mw": 86}
    value, constituents, state, _ = align_actual(TARGET, [initial, revised, conflict], POLICY)
    assert value is None
    assert constituents == []
    assert state == "actual_conflict"


def test_unverified_hourly_average_policy_cannot_silently_activate():
    with pytest.raises(ValueError):
        align_actual(TARGET, [actual(80)], "hourly_average_v1")
