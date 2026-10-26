import re
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import Response

from gridbricks.analytics.grid import target_grid, timestamp
from gridbricks.api.errors import ApiError
from gridbricks.api.export import export_csv
from gridbricks.api.service import analyze, data_status, resolve_snapshot


def query(request: Request, allowed: set[str], required: set[str] = frozenset()) -> dict:
    params = request.query_params
    unknown = set(params) - allowed
    repeated = {key for key in params if len(params.getlist(key)) > 1}
    missing = required - set(params)
    if unknown or repeated or missing:
        raise ApiError(
            422,
            "invalid_query",
            "Review the supplied query parameters.",
            {
                "unknown_parameters": sorted(unknown),
                "repeated_parameters": sorted(repeated),
                "missing_parameters": sorted(missing),
            },
        )
    result = dict(params)
    if "snapshot_id" in result and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", result["snapshot_id"]):
        raise ApiError(422, "invalid_query", "Snapshot ID has an invalid format.")
    return result


def dates(params: dict, accuracy: bool) -> tuple[str, str, str]:
    start = params.get("decision_from") if accuracy else params.get("decision_date")
    end = params.get("decision_to") if accuracy else start
    cutoff = params.get("cutoff", "")
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (TypeError, ValueError):
        raise ApiError(422, "invalid_query", "Supply valid January decision dates.") from None
    if not (date(2026, 1, 1) <= first <= last <= date(2026, 1, 31)):
        raise ApiError(
            422, "invalid_query", "Decision dates must be within January 2026 and ordered."
        )
    if (
        str(first) != start
        or str(last) != end
        or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", cutoff)
    ):
        raise ApiError(422, "invalid_query", "Use YYYY-MM-DD dates and an HH:MM cutoff.")
    return start, end, cutoff


def build_router(repository) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def record_context(request: Request, start: str, end: str, cutoff: str, snapshot: dict):
        request.state.decision_from = start
        request.state.decision_to = end
        request.state.cutoff_local = cutoff
        request.state.snapshot_id = snapshot["id"]

    @router.get("/data-status")
    def status(request: Request):
        params = query(request, {"snapshot_id"})
        result = data_status(repository, params.get("snapshot_id"))
        if result["snapshot"]:
            request.state.snapshot_id = result["snapshot"]["snapshot_id"]
        return result

    @router.get("/forecast")
    def forecast(request: Request):
        params = query(
            request, {"decision_date", "cutoff", "snapshot_id"}, {"decision_date", "cutoff"}
        )
        start, end, cutoff = dates(params, False)
        snapshot = resolve_snapshot(repository, params.get("snapshot_id"))
        record_context(request, start, end, cutoff, snapshot)
        return analyze(repository, snapshot, start, end, cutoff, False)

    @router.get("/accuracy")
    def accuracy(request: Request):
        params = query(
            request,
            {"decision_from", "decision_to", "cutoff", "snapshot_id"},
            {"decision_from", "decision_to", "cutoff"},
        )
        start, end, cutoff = dates(params, True)
        snapshot = resolve_snapshot(repository, params.get("snapshot_id"))
        record_context(request, start, end, cutoff, snapshot)
        return analyze(repository, snapshot, start, end, cutoff, True)

    @router.get("/export")
    def export(request: Request):
        params = query(
            request,
            {"view", "decision_date", "decision_from", "decision_to", "cutoff", "snapshot_id"},
            {"view", "cutoff", "snapshot_id"},
        )
        if params["view"] not in {"forecast", "accuracy"}:
            raise ApiError(422, "invalid_query", "Choose forecast or accuracy export.")
        retrospective = params["view"] == "accuracy"
        inconsistent = {"decision_date"} if retrospective else {"decision_from", "decision_to"}
        if inconsistent & params.keys():
            raise ApiError(422, "invalid_query", "Export date parameters do not match its view.")
        start, end, cutoff = dates(params, retrospective)
        snapshot = resolve_snapshot(repository, params["snapshot_id"])
        record_context(request, start, end, cutoff, snapshot)
        result = analyze(repository, snapshot, start, end, cutoff, retrospective)
        filename = f"gridbricks-{params['view']}-{start}-{end}.csv"
        return Response(
            export_csv(result, retrospective),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @router.get("/forecast/revisions")
    def revisions(request: Request):
        params = query(
            request,
            {"decision_date", "target_start", "cutoff", "snapshot_id"},
            {"decision_date", "target_start", "cutoff"},
        )
        start, _, cutoff = dates(params, False)
        grid = target_grid(start, cutoff)
        try:
            target = timestamp(params["target_start"])
        except ValueError:
            raise ApiError(
                422, "invalid_query", "Supply a target timestamp with its UTC offset."
            ) from None
        interval = next((row for row in grid if timestamp(row["target_start"]) == target), None)
        if interval is None:
            raise ApiError(422, "invalid_query", "Target must belong to the selected delivery day.")
        snapshot = resolve_snapshot(repository, params.get("snapshot_id"))
        record_context(request, start, start, cutoff, snapshot)
        rows = repository.observations(
            snapshot["id"], "WINDFOR", interval["target_start"], interval["target_end"]
        )
        eligible = [
            row
            for row in rows
            if timestamp(row["publish_time_utc"]) <= timestamp(interval["cutoff_utc"])
        ]
        return {
            "snapshot_id": snapshot["id"],
            "cutoff_utc": interval["cutoff_utc"],
            "rows": eligible,
        }

    return router
