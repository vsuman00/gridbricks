"""Independently reconcile HTTP CSV exports with the pinned live JSON response."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
META_FIELDS = (
    "snapshot_id",
    "input_hash",
    "retrieved_at",
    "source_mode",
    "cutoff_local",
    "unit",
    "selection_policy",
    "alignment_policy",
    "actual_policy",
    "metric_policy",
    "evaluation_mode",
    "comparison_note",
)
ROW_FIELDS = (
    "decision_date",
    "cutoff_utc",
    "target_start",
    "target_end",
    "forecast_mw",
    "forecast_publish_time",
    "forecast_observation_id",
    "forecast_age_hours",
    "forecast_lead_hours",
    "state",
)
NUMERIC = {
    "forecast_mw",
    "forecast_age_hours",
    "forecast_lead_hours",
    "actual_mw",
    "error_mw",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def download(base, path, parameters=None):
    suffix = "?" + urlencode(parameters) if parameters else ""
    with urlopen(base + "/api/v1/" + path + suffix, timeout=30) as response:
        return response.read(), {key.lower(): value for key, value in response.headers.items()}


@contextmanager
def local_api():
    with socket.socket() as listener, tempfile.TemporaryFile() as log:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        base = f"http://127.0.0.1:{listener.getsockname()[1]}"
        environment = dict(os.environ)
        environment["GRIDBRICKS_DATA_DIR"] = str(ROOT / "data")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "gridbricks.main:app",
                "--fd",
                str(listener.fileno()),
            ],
            cwd=ROOT,
            env=environment,
            pass_fds=(listener.fileno(),),
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Owned verification API exited before readiness")
                try:
                    download(base, "health")
                    break
                except (URLError, TimeoutError):
                    time.sleep(0.05)
            else:
                raise RuntimeError("Owned verification API did not become ready")
            yield base
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def scalar(value):
    return "" if value is None else str(value)


def reconcile(base, view, query):
    json_bytes, _ = download(base, view, query)
    result = json.loads(json_bytes)
    csv_bytes, headers = download(base, "export", {**query, "view": view})
    require(headers["content-type"].startswith("text/csv"), "Export is not CSV")
    require("attachment" in headers["content-disposition"], "Export is not a download")
    exported = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"), newline="")))
    require(len(exported) == result["coverage"]["expected_count"], "CSV grid length differs")
    require(len(exported) == len(result["rows"]), "CSV and JSON row lengths differ")
    reasons = dict(sorted(Counter(row["state"] for row in exported).items()))
    require(reasons == result["coverage"]["reason_counts"], "Primary reason counts differ")
    require(
        sum(row["forecast_mw"] != "" for row in exported)
        == result["coverage"]["forecast_selected_count"],
        "Selected forecast count differs",
    )
    errors = []
    for index, (csv_row, row) in enumerate(zip(exported, result["rows"], strict=True)):
        for field in META_FIELDS:
            require(
                csv_row[field] == scalar(result["meta"].get(field)),
                f"Metadata differs: {field}",
            )
        for field in (
            *ROW_FIELDS,
            *(("actual_mw", "error_mw") if view == "accuracy" else ()),
        ):
            parsed = (
                (None if csv_row[field] == "" else float(csv_row[field]))
                if field in NUMERIC
                else csv_row[field]
            )
            expected = row.get(field) if field in NUMERIC else scalar(row.get(field))
            require(parsed == expected, f"Row {index} differs: {field}")
        for field in ("flags", "forecast_sources"):
            require(json.loads(csv_row[field]) == row[field], f"Row {index} loses {field}")
        if view == "forecast":
            require(
                not {"actual_mw", "error_mw"}.intersection(csv_row),
                "Forecast leaks actuals",
            )
            continue
        constituents = row["actual_constituents"]
        require(len(constituents) <= 1, "Benchmark duplicated an hourly forecast")
        if constituents:
            part = constituents[0]
            for field in ("observation_id", "start_time", "end_time", "publish_time"):
                require(
                    csv_row["actual_1_" + field] == part[field],
                    "Actual provenance differs",
                )
            require(
                float(csv_row["actual_1_generation_mw"]) == part["generation_mw"],
                "Actual constituent value differs",
            )
            require(
                json.loads(csv_row["actual_1_raw_sources"]) == part["raw_sources"],
                "Actual source lineage differs",
            )
        if csv_row["state"] == "matched":
            forecast, actual, error = map(
                float,
                (csv_row["forecast_mw"], csv_row["actual_mw"], csv_row["error_mw"]),
            )
            require(error == forecast - actual, "Export error sign or equation differs")
            errors.append(error)
    report = {
        "view": view,
        "expected_rows": len(exported),
        "snapshot_id": result["meta"]["snapshot_id"],
        "input_hash": result["meta"]["input_hash"],
        "source_mode": result["meta"]["source_mode"],
        "coverage": result["coverage"],
        "policy_and_row_parity": True,
        "source_and_constituent_lineage_parity": True,
        "response_sha256": {
            "json": hashlib.sha256(json_bytes).hexdigest(),
            "csv": hashlib.sha256(csv_bytes).hexdigest(),
        },
        "download_bytes": {"json": len(json_bytes), "csv": len(csv_bytes)},
    }
    if view == "accuracy":
        computed = {"mae_mw": None, "rmse_mw": None, "bias_mw": None}
        if errors:
            count = len(errors)
            computed = {
                "mae_mw": math.fsum(abs(v) for v in errors) / count,
                "rmse_mw": math.sqrt(math.fsum(v * v for v in errors) / count),
                "bias_mw": math.fsum(errors) / count,
            }
        require(
            len(errors) == result["coverage"]["matched_count"],
            "Matched population differs",
        )
        require(
            sum(row["actual_mw"] != "" for row in exported)
            == result["coverage"]["complete_actual_count"],
            "Complete actual reference count differs",
        )
        for name, value in computed.items():
            api_value = result["metrics"][name]
            require(
                value is None
                and api_value is None
                or value is not None
                and math.isclose(value, api_value, rel_tol=1e-12, abs_tol=1e-9),
                f"Recomputed metric differs: {name}",
            )
        report.update(
            matched_rows=len(errors),
            recomputed_metrics=computed,
            json_metrics=result["metrics"],
            metrics_parity=True,
            reason_counts_from_csv=reasons,
            comparison_note=result["meta"]["comparison_note"],
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/evidence/live-export-reconciliation.json",
    )
    args = parser.parse_args()
    with local_api() as base:
        payload, _ = download(base, "data-status")
        snapshot = json.loads(payload)["snapshot"]
        require(
            snapshot and snapshot["source_mode"] == "live",
            "A default live snapshot is required",
        )
        query = {"snapshot_id": snapshot["snapshot_id"], "cutoff": "09:30"}
        accuracy = reconcile(
            base,
            "accuracy",
            {**query, "decision_from": "2026-01-01", "decision_to": "2026-01-31"},
        )
        forecast = reconcile(base, "forecast", {**query, "decision_date": "2026-01-15"})
        after, _ = download(base, "data-status")
        require(
            json.loads(after)["snapshot"]["snapshot_id"] == snapshot["snapshot_id"],
            "Active snapshot changed during read-only verification",
        )
    evidence = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "status": "passed",
        "command": "backend/.venv/bin/python scripts/reconcile_live_exports.py",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "method": "Owned HTTP server; stdlib CSV parsing and independent metric equations.",
        "snapshot_id": snapshot["snapshot_id"],
        "input_hash": snapshot["input_hash"],
        "accuracy": accuracy,
        "forecast": forecast,
        "limits": [
            "Checks API/CSV parity, not independent correctness of source observations.",
            "Averaging equivalence remains unverified; metrics describe the named benchmark.",
            "No ingestion or source downloads occurred; the existing live snapshot was read only.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "snapshot_id": snapshot["snapshot_id"],
                "matched_rows": accuracy["matched_rows"],
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
