import csv
import io
import json
from datetime import timedelta

from gridbricks.analytics.grid import iso, timestamp


def spreadsheet_safe(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + value
    return value


def export_csv(response: dict, accuracy: bool) -> str:
    meta = response["meta"]
    fields = [
        "snapshot_id",
        "input_hash",
        "retrieved_at",
        "source_mode",
        "decision_date",
        "cutoff_local",
        "cutoff_utc",
        "target_start",
        "target_end",
        "forecast_mw",
        "forecast_publish_time",
        "forecast_observation_id",
        "forecast_age_hours",
        "forecast_lead_hours",
        "forecast_sources",
        "state",
        "flags",
        "unit",
        "selection_policy",
        "alignment_policy",
        "actual_policy",
        "metric_policy",
        "evaluation_mode",
        "comparison_note",
    ]
    if accuracy:
        fields += [
            "actual_mw",
            "error_mw",
            "actual_1_start_time",
            "actual_1_end_time",
            "actual_1_publish_time",
            "actual_1_generation_mw",
            "actual_1_observation_id",
            "actual_1_raw_sources",
        ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in response["rows"]:
        values = {key: row.get(key, meta.get(key)) for key in fields}
        values["forecast_sources"] = json.dumps(row["forecast_sources"], sort_keys=True)
        values["flags"] = json.dumps(row["flags"])
        if accuracy and row["actual_constituents"]:
            part = row["actual_constituents"][0]
            for key in ("start_time", "publish_time", "generation_mw", "observation_id"):
                values["actual_1_" + key] = part[key]
            values["actual_1_end_time"] = iso(timestamp(part["start_time"]) + timedelta(minutes=30))
            values["actual_1_raw_sources"] = json.dumps(part["raw_sources"], sort_keys=True)
        writer.writerow({key: spreadsheet_safe(value) for key, value in values.items()})
    return output.getvalue()
