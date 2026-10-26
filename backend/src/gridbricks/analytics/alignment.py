from datetime import timedelta

from gridbricks.analytics.grid import iso, timestamp
from gridbricks.analytics.policies import ALIGNMENT_POLICY
from gridbricks.analytics.selection import select_actual


def align_actual(
    target_start: str, records: list[dict], policy: str
) -> tuple[float | None, list[dict], str, list[str]]:
    if policy != ALIGNMENT_POLICY:
        raise ValueError("Unsupported comparison policy")
    exact = [row for row in records if timestamp(row["start_time_utc"]) == timestamp(target_start)]
    selected, state, flags = select_actual(exact)
    flags = sorted({*flags, "temporal_reference_mismatch"})
    if selected is None:
        return None, [], state, flags
    constituent = {
        "observation_id": selected["id"],
        "start_time": selected["start_time_utc"],
        "end_time": iso(timestamp(selected["start_time_utc"]) + timedelta(minutes=30)),
        "publish_time": selected["publish_time_utc"],
        "generation_mw": selected["generation_mw"],
    }
    return selected["generation_mw"], [constituent], "matched", flags
