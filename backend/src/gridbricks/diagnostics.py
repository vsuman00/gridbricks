"""Bounded JSON-line events for local HTTP and import diagnostics."""

import json
import logging
import re
from datetime import UTC, datetime

events = logging.getLogger("gridbricks.events")
if not events.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    events.addHandler(handler)
events.setLevel(logging.INFO)
events.propagate = False


def safe_code(value: str) -> str:
    return value if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) else "unclassified_error"


def emit_event(name: str, **fields: object) -> None:
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    payload = {
        "timestamp_utc": timestamp,
        "event": name,
        **fields,
    }
    events.info(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
