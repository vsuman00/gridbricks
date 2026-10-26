import math
from datetime import datetime

from gridbricks.analytics.grid import timestamp


def _latest(records: list[dict], dimension: str) -> tuple[dict | None, str, list[str]]:
    if not records:
        return None, f"missing_{dimension}", []
    publication = max(timestamp(row["publish_time_utc"]) for row in records)
    newest = [row for row in records if timestamp(row["publish_time_utc"]) == publication]
    values = {row["generation_mw"] for row in newest}
    flags = sorted({flag for row in newest for flag in row.get("quality_flags", [])})
    if len(values) > 1:
        return None, f"{dimension}_conflict", flags
    value = newest[0]["generation_mw"]
    if value is None or not math.isfinite(value):
        return None, f"missing_{dimension}", sorted({*flags, f"invalid_{dimension}_value"})
    # Exact semantic duplicates are equivalent. IDs only stabilize provenance, never values.
    selected = min(newest, key=lambda row: str(row["id"]))
    return selected, "selected", flags


def select_forecast(records: list[dict], cutoff: datetime) -> tuple[dict | None, str, list[str]]:
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("Cutoff must include its UTC offset")
    eligible = [row for row in records if timestamp(row["publish_time_utc"]) <= cutoff]
    return _latest(eligible, "forecast")


def select_actual(records: list[dict]) -> tuple[dict | None, str, list[str]]:
    return _latest(records, "actual")
