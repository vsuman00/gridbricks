"""Source schema failure is distinct from recognized, counted row defects."""

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime


class PayloadError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone is required")
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def validate(body, dataset):
    try:
        rows = json.loads(body)
    except (ValueError, UnicodeError) as error:
        raise PayloadError("malformed_json") from error
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise PayloadError("unknown_payload_schema")
    counts = Counter(observed_count=len(rows))
    normalized = []
    for index, row in enumerate(rows):
        required = {"dataset", "startTime", "publishTime", "generation"}
        if dataset == "FUELHH":
            required.add("fuelType")
        if not required <= row.keys() or row["dataset"] != dataset:
            raise PayloadError("unknown_row_schema")
        if dataset == "FUELHH" and row["fuelType"] != "WIND":
            counts["filtered_non_wind"] += 1
            continue
        try:
            start, publish = timestamp(row["startTime"]), timestamp(row["publishTime"])
            parsed = datetime.fromisoformat(start.replace("Z", "+00:00"))
            cadence = 60 if dataset == "WINDFOR" else 30
            if parsed.minute % cadence or parsed.second or parsed.microsecond:
                raise ValueError("Invalid source cadence")
        except (ValueError, TypeError, OverflowError):
            raise PayloadError("invalid_timestamp") from None
        value = row["generation"]
        flags = []
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            value = None
        else:
            try:
                value = float(value)
            except OverflowError:
                value = None
        if value is None or not math.isfinite(value):
            counts["invalid_generation"] += 1
            flags.append("invalid_generation")
            value = None
        else:
            counts["valid_count"] += 1
            if value < 0:
                flags.append("negative_generation")
        semantic = {
            "dataset": dataset,
            "start_time_utc": start,
            "publish_time_utc": publish,
            "generation_mw": value,
            "fuel_type": "WIND",
        }
        semantic_hash = digest(semantic)
        normalized.append(
            {
                **semantic,
                "id": semantic_hash,
                "semantic_hash": semantic_hash,
                "quality_flags_json": canonical(flags),
                "row_index": index,
            }
        )
    return normalized, counts
