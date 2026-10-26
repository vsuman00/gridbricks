from itertools import permutations

from gridbricks.analytics.selection import select_actual


def actual(value, publication, identity):
    return {
        "id": identity,
        "generation_mw": value,
        "publish_time_utc": publication,
        "quality_flags": [],
    }


def test_retrospective_reference_uses_latest_publication_after_the_decision():
    rows = [
        actual(80, "2026-01-16T00:30:00Z", "initial"),
        actual(85, "2026-01-20T12:00:00Z", "revised"),
    ]
    selected, state, _ = select_actual(rows)
    assert state == "selected"
    assert selected["id"] == "revised"
    assert selected["generation_mw"] == 85


def test_latest_actual_conflict_never_falls_back_and_is_order_independent():
    rows = [
        actual(80, "2026-01-16T00:30:00Z", "old"),
        actual(85, "2026-01-20T12:00:00Z", "a"),
        actual(86, "2026-01-20T12:00:00Z", "b"),
    ]
    for ordering in permutations(rows):
        selected, state, _ = select_actual(list(ordering))
        assert selected is None
        assert state == "actual_conflict"


def test_absent_and_invalid_actuals_remain_missing_while_zero_is_real():
    assert select_actual([])[:2] == (None, "missing_actual")
    assert select_actual([actual(None, "2026-01-16T00:30:00Z", "null")])[:2] == (
        None,
        "missing_actual",
    )
    selected, state, _ = select_actual(
        [
            actual(0, "2026-01-16T00:30:00Z", "zero"),
            actual(0, "2026-01-16T00:30:00+00:00", "duplicate"),
        ]
    )
    assert state == "selected"
    assert selected["generation_mw"] == 0
