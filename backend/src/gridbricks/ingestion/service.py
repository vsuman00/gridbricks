"""Windowed import journal, raw preservation and atomic snapshot publication."""

import hashlib
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from gridbricks.analytics.policies import POLICIES
from gridbricks.config import Settings
from gridbricks.diagnostics import emit_event, safe_code
from gridbricks.ingestion.validation import canonical, digest, timestamp, validate
from gridbricks.storage import models as m
from gridbricks.storage.database import migrate, writer_engine
from gridbricks.storage.repository import Repository


def now():
    return timestamp(datetime.now(UTC).isoformat())


def scope(decision_from: date, decision_to: date):
    if not date(2026, 1, 1) <= decision_from <= decision_to <= date(2026, 1, 31):
        raise ValueError("Decision scope must be within January 2026")
    local = ZoneInfo("Europe/London")

    def midnight(day):
        return timestamp(datetime.combine(day, time(), local).isoformat())

    return {
        "decision_from": str(decision_from),
        "decision_to": str(decision_to),
        "delivery_from": str(decision_from + timedelta(days=1)),
        "delivery_to": str(decision_to + timedelta(days=1)),
        "forecast_publish_from": midnight(decision_from - timedelta(days=7)),
        "forecast_publish_to": midnight(decision_to + timedelta(days=1)),
    }


def fetch_plan(bounds):
    jobs = []
    day = date.fromisoformat(bounds["forecast_publish_from"][:10])
    end = date.fromisoformat(bounds["forecast_publish_to"][:10])
    while day < end:
        jobs.append(
            (
                "WINDFOR",
                {
                    "publishDateTimeFrom": f"{day}T00:00:00Z",
                    "publishDateTimeTo": f"{day + timedelta(days=1)}T00:00:00Z",
                },
            )
        )
        day += timedelta(days=1)
    day = date.fromisoformat(bounds["delivery_from"])
    while day <= date.fromisoformat(bounds["delivery_to"]):
        jobs.append(
            (
                "FUELHH",
                {"settlementDateFrom": str(day), "settlementDateTo": str(day), "fuelType": "WIND"},
            )
        )
        day += timedelta(days=1)
    return jobs


def import_scope(
    settings: Settings,
    source,
    decision_from=date(2026, 1, 15),
    decision_to=date(2026, 1, 15),
    source_mode="live",
    policies=None,
):
    if source_mode not in {"fixture", "live"}:
        raise ValueError("Unknown source mode")
    bounds = scope(decision_from, decision_to)
    policies = policies or POLICIES
    parameters = {"bounds": bounds, "source_mode": source_mode, "policies": policies}
    migrate(settings)
    engine = writer_engine(settings)
    run_id = uuid4().hex
    started = perf_counter()
    plan = fetch_plan(bounds)
    counts = Counter()
    raw_inputs, members, semantic_rows = [], set(), {}
    with engine.begin() as connection:
        prior = (
            connection.execute(
                select(m.runs)
                .where(m.runs.c.parameters_json == canonical(parameters))
                .order_by(m.runs.c.started_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        resumable = {}
        if prior and prior["status"] == "failed":
            resumable = {
                row["window_key"]: row["raw_response_id"]
                for row in connection.execute(
                    select(m.windows).where(
                        m.windows.c.run_id == prior["id"],
                        m.windows.c.status.in_(["succeeded", "resumed"]),
                    )
                ).mappings()
            }
        connection.execute(
            insert(m.runs).values(
                id=run_id,
                dataset="WINDFOR,FUELHH",
                parameters_json=canonical(parameters),
                started_at=now(),
                status="running",
                counts_json="{}",
            )
        )
        for dataset, params in plan:
            connection.execute(
                insert(m.windows).values(
                    id=uuid4().hex,
                    run_id=run_id,
                    window_key=digest([dataset, params]),
                    dataset=dataset,
                    parameters_json=canonical(params),
                    status="pending",
                )
            )
    emit_event(
        "import_started",
        run_id=run_id,
        source_mode=source_mode,
        decision_from=bounds["decision_from"],
        decision_to=bounds["decision_to"],
        planned_windows=len(plan),
    )
    window_in_progress = False
    try:
        for dataset, params in plan:
            window_in_progress = True
            window_started = perf_counter()
            attempt_count = 0
            key = digest([dataset, params])
            raw_id = resumable.get(key)
            with engine.connect() as connection:
                raw_row = (
                    connection.execute(select(m.raw).where(m.raw.c.id == raw_id)).mappings().first()
                    if raw_id
                    else None
                )
            window_from = params.get("publishDateTimeFrom", params.get("settlementDateFrom"))
            window_to = params.get("publishDateTimeTo", params.get("settlementDateTo"))
            emit_event(
                "import_window_started",
                run_id=run_id,
                dataset=dataset,
                window_key=key,
                window_from=window_from,
                window_to=window_to,
                reused_saved_raw=bool(raw_row),
            )
            if raw_row:
                body = (settings.data_dir / raw_row["relative_path"]).read_bytes()
                if hashlib.sha256(body).hexdigest() != raw_row["content_hash"]:
                    raise ValueError("resumed_raw_hash_mismatch")
                raw_info = dict(raw_row)
            else:
                try:
                    url, body, status = source.fetch(dataset, params)
                finally:
                    attempt_count = getattr(source, "last_attempt_count", 1)
                content_hash = hashlib.sha256(body).hexdigest()
                raw_id = uuid4().hex
                relative = f"raw/{content_hash}.json"
                raw_dir = settings.data_dir / "raw"
                raw_dir.mkdir(exist_ok=True)
                raw_path = settings.data_dir / relative
                if not raw_path.exists():
                    raw_path.write_bytes(body)
                elif hashlib.sha256(raw_path.read_bytes()).hexdigest() != content_hash:
                    raise ValueError("stored_raw_hash_mismatch")
                raw_info = {
                    "id": raw_id,
                    "run_id": run_id,
                    "request_url": url,
                    "retrieved_at": (
                        source.retrieved_at(dataset, params)
                        if hasattr(source, "retrieved_at")
                        else now()
                    ),
                    "content_hash": content_hash,
                    "relative_path": relative,
                    "http_status": status,
                }
                with engine.begin() as connection:
                    connection.execute(insert(m.raw).values(**raw_info))
            rows, row_counts = validate(body, dataset)
            counts.update(row_counts)
            lower = bounds["delivery_from"] + "T00:00:00.000000Z"
            upper = str(date.fromisoformat(bounds["delivery_to"]) + timedelta(days=1))
            upper += "T00:00:00.000000Z"
            retained = []
            for row in rows:
                if not lower <= row["start_time_utc"] < upper:
                    counts["filtered_outside_target_scope"] += 1
                    continue
                if dataset == "WINDFOR" and not (
                    timestamp(params["publishDateTimeFrom"])
                    <= row["publish_time_utc"]
                    <= timestamp(params["publishDateTimeTo"])
                ):
                    counts["filtered_outside_publication_window"] += 1
                    continue
                retained.append(row)
                members.add(row["id"])
                semantic_rows[row["id"]] = row
            with engine.begin() as connection:
                for row in retained:
                    observation = {key: value for key, value in row.items() if key != "row_index"}
                    connection.execute(
                        sqlite_insert(m.observations)
                        .values(**observation)
                        .on_conflict_do_nothing(index_elements=["semantic_hash"])
                    )
                    connection.execute(
                        sqlite_insert(m.sources)
                        .values(
                            observation_id=row["id"],
                            raw_response_id=raw_id,
                            row_index=row["row_index"],
                        )
                        .on_conflict_do_nothing()
                    )
                connection.execute(
                    update(m.windows)
                    .where(m.windows.c.run_id == run_id, m.windows.c.window_key == key)
                    .values(status="resumed" if raw_row else "succeeded", raw_response_id=raw_id)
                )
            raw_inputs.append(raw_info)
            counts["completed_windows"] += 1
            emit_event(
                "import_window_finished",
                run_id=run_id,
                dataset=dataset,
                window_key=key,
                status="resumed" if raw_row else "succeeded",
                attempts=attempt_count,
                observed_count=row_counts["observed_count"],
                valid_count=row_counts["valid_count"],
                invalid_generation_count=row_counts["invalid_generation"],
                filtered_non_wind_count=row_counts["filtered_non_wind"],
                retained_count=len(retained),
                duration_ms=round((perf_counter() - window_started) * 1000, 3),
            )
            window_in_progress = False
        by_key = defaultdict(set)
        for row in semantic_rows.values():
            by_key[(row["dataset"], row["start_time_utc"], row["publish_time_utc"])].add(
                row["generation_mw"]
            )
        counts["conflicting_keys"] = sum(len(values) > 1 for values in by_key.values())
        counts["semantic_observations"] = len(members)
        counts["valid_scoped_observations"] = sum(
            row["generation_mw"] is not None for row in semantic_rows.values()
        )
        days = (decision_to - decision_from).days + 1
        counts["expected_forecast_targets"] = days * 24
        counts["expected_actual_targets"] = days * 48
        for dataset, name in (("WINDFOR", "forecast"), ("FUELHH", "actual")):
            counts[f"observed_{name}_targets"] = len(
                {
                    row["start_time_utc"]
                    for row in semantic_rows.values()
                    if row["dataset"] == dataset
                }
            )
            counts[f"missing_{name}_targets"] = max(
                0, counts[f"expected_{name}_targets"] - counts[f"observed_{name}_targets"]
            )
        partial = any(
            counts[name]
            for name in (
                "invalid_timestamp",
                "invalid_generation",
                "conflicting_keys",
                "missing_forecast_targets",
                "missing_actual_targets",
            )
        )
        status = "partial" if partial else "succeeded"
        identity = {
            "semantic_hashes": sorted(members),
            "raw_hashes": sorted({row["content_hash"] for row in raw_inputs}),
            "bounds": bounds,
            "policies": policies,
            "source_mode": source_mode,
        }
        input_hash = digest(identity)
        snapshot_id = uuid4().hex
        created_at = now()
        manifest = {
            **identity,
            "snapshot_id": snapshot_id,
            "input_hash": input_hash,
            "created_at": created_at,
            "raw_inputs": raw_inputs,
            "counts": dict(counts),
            "status": status,
            "run_id": run_id,
        }
        manifest_hash = digest(manifest)
        manifest_path = f"snapshots/{snapshot_id}.json"
        (settings.data_dir / "snapshots").mkdir(exist_ok=True)
        (settings.data_dir / manifest_path).write_text(canonical(manifest) + "\n")
        with engine.begin() as connection:
            connection.execute(
                insert(m.snapshots).values(
                    id=snapshot_id,
                    input_hash=input_hash,
                    manifest_hash=manifest_hash,
                    created_at=created_at,
                    retrieved_at=max(row["retrieved_at"] for row in raw_inputs),
                    bounds_json=canonical(bounds),
                    status=status,
                    source_mode=source_mode,
                    policy_versions_json=canonical(policies),
                    counts_json=canonical(dict(counts)),
                    manifest_path=manifest_path,
                )
            )
            if members:
                connection.execute(
                    insert(m.membership),
                    [{"snapshot_id": snapshot_id, "observation_id": member} for member in members],
                )
            connection.execute(
                insert(m.snapshot_raw),
                [{"snapshot_id": snapshot_id, "raw_response_id": row["id"]} for row in raw_inputs],
            )
            connection.execute(
                sqlite_insert(m.state)
                .values(key="active_snapshot", value=snapshot_id)
                .on_conflict_do_update(index_elements=["key"], set_={"value": snapshot_id})
            )
            connection.execute(
                update(m.runs)
                .where(m.runs.c.id == run_id)
                .values(status=status, completed_at=now(), counts_json=canonical(dict(counts)))
            )
        emit_event(
            "import_published",
            run_id=run_id,
            snapshot_id=snapshot_id,
            manifest_hash=manifest_hash,
            source_mode=source_mode,
            status=status,
            counts=dict(counts),
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
        return Repository(settings).get_snapshot(snapshot_id)
    except Exception as error:
        # Store stable error classes/codes, never response bodies, arbitrary paths or credentials.
        code = (
            str(error)
            if type(error).__name__ in {"PayloadError", "SourceError"}
            else type(error).__name__
        )
        with engine.begin() as connection:
            if window_in_progress:
                connection.execute(
                    update(m.windows)
                    .where(m.windows.c.run_id == run_id, m.windows.c.window_key == key)
                    .values(status="failed", error_code=code)
                )
            connection.execute(
                update(m.windows)
                .where(m.windows.c.run_id == run_id, m.windows.c.status == "pending")
                .values(status="not_attempted")
            )
            connection.execute(
                update(m.runs)
                .where(m.runs.c.id == run_id)
                .values(
                    status="failed",
                    completed_at=now(),
                    counts_json=canonical(dict(counts)),
                    error_code=code,
                )
            )
        if window_in_progress:
            emit_event(
                "import_window_failed",
                run_id=run_id,
                dataset=dataset,
                window_key=key,
                window_from=window_from,
                window_to=window_to,
                attempts=attempt_count,
                error_code=safe_code(code),
                duration_ms=round((perf_counter() - window_started) * 1000, 3),
            )
        emit_event(
            "import_failed",
            run_id=run_id,
            error_code=safe_code(code),
            completed_windows=counts["completed_windows"],
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
        raise
    finally:
        engine.dispose()


def audit(settings, cutoff="09:30"):
    """Audit the entire January decision scope against the active immutable inputs."""
    from gridbricks.api.errors import ApiError
    from gridbricks.api.service import analyze

    repository = Repository(settings)
    snapshot = repository.get_snapshot()
    result = {
        "snapshot": snapshot,
        "last_import": repository.last_import(),
        "comparison_available": bool(snapshot and snapshot["policies"] == POLICIES),
        "analysis": None,
        "note": "Observed input coverage is distinct from selected and matched coverage.",
    }
    if snapshot:
        arguments = (
            repository,
            snapshot,
            "2026-01-01",
            "2026-01-31",
            cutoff,
        )
        try:
            forecast = analyze(*arguments, accuracy=False)
            result["forecast_coverage"] = forecast["coverage"]
            if result["comparison_available"]:
                response = analyze(*arguments, accuracy=True)
                result["analysis"] = {
                    key: response[key] for key in ("meta", "coverage", "metrics", "daily")
                }
        except ApiError as error:
            result["analysis_error"] = {"code": error.code, "message": error.message}
    return result
