import math
from collections import defaultdict
from datetime import date, timedelta

from gridbricks.analytics.alignment import align_actual
from gridbricks.analytics.grid import iso, target_grid, timestamp
from gridbricks.analytics.metrics import metrics, summarize
from gridbricks.analytics.policies import COMPARISON_NOTE, POLICIES
from gridbricks.analytics.selection import select_forecast
from gridbricks.api.errors import ApiError


def resolve_snapshot(repository, snapshot_id=None) -> dict:
    snapshot = repository.get_snapshot(snapshot_id)
    if snapshot is None:
        if snapshot_id is not None:
            raise ApiError(404, "snapshot_not_found", "This dataset snapshot is not available.")
        raise ApiError(
            503, "dataset_unavailable", "Import a stored dataset before reviewing forecasts."
        )
    return snapshot


def snapshot_status(snapshot: dict | None) -> dict | None:
    if snapshot is None:
        return None
    return {
        "snapshot_id": snapshot["id"],
        "input_hash": snapshot["input_hash"],
        "created_at": snapshot["created_at"],
        "retrieved_at": snapshot["retrieved_at"],
        "source_mode": snapshot["source_mode"],
        "status": snapshot["status"],
        "policies": snapshot["policies"],
        "counts": snapshot["counts"],
        **snapshot["bounds"],
    }


def data_status(repository, snapshot_id=None) -> dict:
    snapshot = (
        resolve_snapshot(repository, snapshot_id) if snapshot_id else repository.get_snapshot()
    )
    policy = snapshot["policies"].get("alignment", "unverified") if snapshot else "unverified"
    comparison_available = bool(snapshot and snapshot["policies"] == POLICIES)
    return {
        "snapshot": snapshot_status(snapshot),
        "last_import": repository.last_import(),
        "alignment": {
            "verified": comparison_available,
            "policy": policy,
            "message": (
                COMPARISON_NOTE if comparison_available else "Comparison policy unavailable."
            ),
        },
        "sources": [
            {
                "dataset": name,
                "url": f"https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/{name}/stream",
            }
            for name in ("WINDFOR", "FUELHH")
        ],
    }


def _group(records):
    groups = defaultdict(list)
    for record in records:
        groups[timestamp(record["start_time_utc"])].append(record)
    return groups


def analyze(
    repository, snapshot, decision_from: str, decision_to: str, cutoff: str, accuracy: bool
):
    policies = snapshot["policies"]
    if policies.get("selection") != POLICIES["selection"]:
        raise ApiError(
            409, "policy_unsupported", "This snapshot uses an unsupported selection policy."
        )
    if accuracy and any(policies.get(key) != value for key, value in POLICIES.items()):
        raise ApiError(
            409, "alignment_unverified", "This snapshot's comparison policy is unavailable."
        )
    day = date.fromisoformat(decision_from)
    last = date.fromisoformat(decision_to)
    grid = []
    while day <= last:
        grid.extend(target_grid(str(day), cutoff))
        day += timedelta(days=1)
    if not grid:
        raise ApiError(422, "invalid_query", "Choose a nonempty January decision-date range.")
    start, end = grid[0]["target_start"], grid[-1]["target_end"]
    forecasts = _group(repository.observations(snapshot["id"], "WINDFOR", start, end))
    actuals = (
        _group(repository.observations(snapshot["id"], "FUELHH", start, end)) if accuracy else {}
    )
    rows, ids = [], set()
    for interval in grid:
        target, deadline = timestamp(interval["target_start"]), timestamp(interval["cutoff_utc"])
        candidates = forecasts.get(target, [])
        forecast, state, flags = select_forecast(candidates, deadline)
        eligible = [row for row in candidates if timestamp(row["publish_time_utc"]) <= deadline]
        published = max((timestamp(row["publish_time_utc"]) for row in eligible), default=None)
        if state == "missing_forecast" and not eligible:
            flags = sorted({*flags, "bounded_history_search"})
            history = timestamp(snapshot["bounds"]["forecast_publish_from"])
            if deadline - history < timedelta(days=8):
                state = "history_window_exhausted"
        row = {
            **interval,
            "forecast_mw": forecast["generation_mw"] if forecast else None,
            "forecast_publish_time": iso(published) if published else None,
            "forecast_observation_id": forecast["id"] if forecast else None,
            "forecast_age_hours": (deadline - published).total_seconds() / 3600
            if published
            else None,
            "forecast_lead_hours": (target - published).total_seconds() / 3600
            if published
            else None,
            "forecast_sources": [],
            "state": state,
            "flags": flags,
        }
        if forecast:
            ids.add(forecast["id"])
        if accuracy:
            actual, constituents, actual_state, actual_flags = align_actual(
                interval["target_start"], actuals.get(target, []), policies["alignment"]
            )
            row.update(actual_mw=actual, actual_constituents=constituents, error_mw=None)
            row["flags"] = sorted({*flags, *actual_flags})
            ids.update(part["observation_id"] for part in constituents)
            if forecast:
                row["state"] = actual_state
                if actual is not None:
                    error = forecast["generation_mw"] - actual
                    if math.isfinite(error):
                        row["error_mw"] = error
                    else:
                        row["state"] = "invalid_error"
                        row["flags"] = sorted({*row["flags"], "nonfinite_derived_error"})
        rows.append(row)
    lineage = repository.lineage_many(sorted(ids), snapshot["id"])
    for row in rows:
        row["forecast_sources"] = lineage.get(row["forecast_observation_id"], [])
        for part in row.get("actual_constituents", []):
            part["raw_sources"] = lineage.get(part["observation_id"], [])
    response = {
        "meta": {
            "snapshot_id": snapshot["id"],
            "input_hash": snapshot["input_hash"],
            "retrieved_at": snapshot["retrieved_at"],
            "source_mode": snapshot["source_mode"],
            "decision_from": decision_from,
            "decision_to": decision_to,
            "delivery_from": str(date.fromisoformat(decision_from) + timedelta(days=1)),
            "delivery_to": str(last + timedelta(days=1)),
            "cutoff_local": cutoff,
            "timezone": "Europe/London",
            "comparison_resolution_minutes": 60,
            "selection_policy": policies["selection"],
            "alignment_policy": policies["alignment"],
            "actual_policy": policies["actual"],
            "metric_policy": policies["metric"],
            "evaluation_mode": "retrospective" if accuracy else "decision",
            "unit": "MW",
            "comparison_note": COMPARISON_NOTE,
        },
        "coverage": summarize(rows, accuracy=accuracy),
        "rows": rows,
    }
    if accuracy:
        response["metrics"] = metrics(rows)
        daily = []
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["decision_date"]].append(row)
        for decision, values in sorted(grouped.items()):
            daily.append(
                {
                    "decision_date": decision,
                    "delivery_date": str(date.fromisoformat(decision) + timedelta(days=1)),
                    **summarize(values),
                    **metrics(values),
                }
            )
        response["daily"] = daily
    return response
