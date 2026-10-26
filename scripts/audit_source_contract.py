"""Read-only T01 checks. These are source samples, never an application snapshot."""

import argparse
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets/"


def utc(value):
    return value.isoformat().replace("+00:00", "Z")


def fetch(job):
    name, dataset, params, decision = job
    url = BASE + dataset + "/stream?" + urlencode(params)
    result = {"name": name, "dataset": dataset, "request_url": url}
    try:
        with urlopen(url, timeout=20) as response:
            body = response.read()
            result["http_status"] = response.status
        result["response_sha256"] = hashlib.sha256(body).hexdigest()
        rows = json.loads(body)
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError("Expected an array of records")
        selected = [r for r in rows if dataset != "FUELHH" or r.get("fuelType") == "WIND"]
        result.update(status="succeeded", total_records=len(rows), wind_records=len(selected))
        by_key = defaultdict(set)
        by_target = defaultdict(set)
        for row in selected:
            by_key[(row["startTime"], row["publishTime"])].add(row["generation"])
            by_target[row["startTime"]].add(row["publishTime"])
        result["same_key_conflicts"] = sum(len(v) > 1 for v in by_key.values())
        result["targets_with_multiple_publications"] = sum(len(v) > 1 for v in by_target.values())
        result["exact_duplicate_count"] = len(selected) - sum(len(v) for v in by_key.values())
        result["sample_records"] = selected[:2]
        publications = sorted({r["publishTime"] for r in selected})
        result["publication_bounds"] = [publications[0], publications[-1]] if publications else []
        if decision:
            local = ZoneInfo("Europe/London")
            cutoff = datetime.combine(decision, time(9, 30), local).astimezone(UTC)
            start = datetime.combine(decision + timedelta(days=1), time(), local).astimezone(UTC)
            step = timedelta(hours=1) if dataset == "WINDFOR" else timedelta(minutes=30)
            expected = [utc(start + step * i) for i in range(24 if dataset == "WINDFOR" else 48)]
            eligible = [
                r
                for r in selected
                if r["startTime"] in expected
                and (dataset == "FUELHH" or datetime.fromisoformat(r["publishTime"]) <= cutoff)
            ]
            result.update(
                decision_date=str(decision),
                delivery_date=str(decision + timedelta(days=1)),
                cutoff_utc=utc(cutoff),
                expected_targets=len(expected),
                observed_eligible_targets=len({r["startTime"] for r in eligible}),
                missing_targets=sorted(set(expected) - {r["startTime"] for r in eligible}),
            )
            if dataset == "WINDFOR":
                result["records_at_cutoff"] = sum(
                    datetime.fromisoformat(r["publishTime"]) == cutoff for r in eligible
                )
            else:
                result["final_half_hour_present"] = expected[-1] in {
                    r["startTime"] for r in eligible
                }
        else:
            result["records_at_lower_bound"] = sum(
                r["publishTime"] == params["publishDateTimeFrom"] for r in selected
            )
            result["records_at_upper_bound"] = sum(
                r["publishTime"] == params["publishDateTimeTo"] for r in selected
            )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New JSON evidence file (never overwritten)"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output path; existing evidence is never overwritten")
    jobs = []
    for decision in (date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 31)):
        cutoff = datetime.combine(decision, time(9, 30), ZoneInfo("Europe/London")).astimezone(UTC)
        jobs.append(
            (
                f"forecast-{decision}",
                "WINDFOR",
                {
                    "publishDateTimeFrom": utc(cutoff - timedelta(days=7)),
                    "publishDateTimeTo": utc(cutoff),
                },
                decision,
            )
        )
        delivery = str(decision + timedelta(days=1))
        jobs.append(
            (
                f"actual-{delivery}",
                "FUELHH",
                {"settlementDateFrom": delivery, "settlementDateTo": delivery, "fuelType": "WIND"},
                decision,
            )
        )
    for start, end in (
        ("2026-01-15T23:30:00Z", "2026-01-16T00:00:00Z"),
        ("2026-01-16T00:00:00Z", "2026-01-16T00:30:00Z"),
    ):
        jobs.append(
            (
                f"boundary-{start}",
                "FUELHH",
                {"publishDateTimeFrom": start, "publishDateTimeTo": end, "fuelType": "WIND"},
                None,
            )
        )
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, jobs))
    evidence = {
        "checked_at_utc": utc(datetime.now(UTC)),
        "purpose": (
            "Read-only T01 source samples; not ingestion, a full-month audit, "
            "or accuracy validation."
        ),
        "results": results,
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(evidence, output, indent=2)
        output.write("\n")
    print(
        json.dumps(
            [
                {
                    k: r[k]
                    for k in (
                        "name",
                        "status",
                        "wind_records",
                        "observed_eligible_targets",
                        "same_key_conflicts",
                        "records_at_lower_bound",
                        "records_at_upper_bound",
                        "error",
                    )
                    if k in r
                }
                for r in results
            ],
            indent=2,
        )
    )
    return int(any(r["status"] == "failed" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
