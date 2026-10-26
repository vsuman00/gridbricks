from datetime import UTC, date, datetime, timedelta

from gridbricks.analytics.grid import target_grid, timestamp


def test_all_january_decisions_cover_exactly_the_required_delivery_scope():
    rows = []
    for day in range(1, 32):
        decision = date(2026, 1, day)
        daily = target_grid(str(decision), "09:30")
        assert len(daily) == 24
        assert daily[0]["decision_date"] == str(decision)
        assert timestamp(daily[0]["cutoff_utc"]) == datetime(2026, 1, day, 9, 30, tzinfo=UTC)
        assert timestamp(daily[0]["target_start"]).date() == decision + timedelta(days=1)
        rows.extend(daily)
    assert len(rows) == 744
    assert len({r["target_start"] for r in rows}) == 744
    assert timestamp(rows[0]["target_start"]) == datetime(2026, 1, 2, tzinfo=UTC)
    assert timestamp(rows[-1]["target_end"]) == datetime(2026, 2, 2, tzinfo=UTC)
    for previous, following in zip(rows, rows[1:], strict=False):
        assert timestamp(previous["target_end"]) == timestamp(following["target_start"])


def test_grid_contains_rows_independent_of_observations_and_cutoff_changes():
    early = target_grid("2026-01-15", "00:00")
    late = target_grid("2026-01-15", "23:59")
    assert [r["target_start"] for r in early] == [r["target_start"] for r in late]
    assert timestamp(early[0]["cutoff_utc"]) == datetime(2026, 1, 15, tzinfo=UTC)
    assert timestamp(late[0]["cutoff_utc"]) == datetime(2026, 1, 15, 23, 59, tzinfo=UTC)
    assert all(
        timestamp(r["target_end"]) - timestamp(r["target_start"]) == timedelta(hours=1)
        for r in late
    )
