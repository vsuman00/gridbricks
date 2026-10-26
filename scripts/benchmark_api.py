"""Measure 100 warm, sequential full-January HTTP requests on one pinned snapshot."""

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from gridbricks.config import Settings
from gridbricks.storage.repository import Repository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/api-benchmark.json"))
    args = parser.parse_args()
    settings = Settings(args.data_dir) if args.data_dir else Settings()
    snapshot = Repository(settings).get_snapshot()
    if snapshot is None:
        parser.error("Import a January snapshot before measuring the analytical API")
    report = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "snapshot_id": snapshot["id"],
        "input_hash": snapshot["input_hash"],
        "source_mode": snapshot["source_mode"],
        "policies": snapshot["policies"],
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "scope": (
            "100 sequential warm local full-January accuracy HTTP requests; "
            "source download excluded."
        ),
    }
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    query = urlencode(
        {
            "decision_from": "2026-01-01",
            "decision_to": "2026-01-31",
            "cutoff": "09:30",
            "snapshot_id": snapshot["id"],
        }
    )
    base = f"http://127.0.0.1:{port}/api/v1/"
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "gridbricks.main:app",
                "--fd",
                str(listener.fileno()),
                "--no-access-log",
            ],
            pass_fds=(listener.fileno(),),
            env={**os.environ, "GRIDBRICKS_DATA_DIR": str(settings.data_dir)},
            stdout=log,
            stderr=log,
        )
        try:
            for _attempt in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Owned benchmark API failed to start")
                try:
                    with urlopen(base + "health", timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(0.05)
            else:
                raise RuntimeError("Owned benchmark API was not ready")
            timings = []
            for index in range(105):
                start = time.perf_counter()
                with urlopen(base + "accuracy?" + query, timeout=10) as response:
                    data = json.load(response)
                elapsed = (time.perf_counter() - start) * 1000
                if data["meta"]["snapshot_id"] != snapshot["id"] or len(data["rows"]) != 744:
                    raise RuntimeError("Benchmark response did not retain the complete pinned grid")
                if index >= 5:
                    timings.append(elapsed)
            ordered = sorted(timings)
            report.update(
                status="passed" if ordered[94] <= 1000 else "failed",
                warmup_count=5,
                request_count=100,
                expected_rows_per_request=744,
                p50_ms=ordered[49],
                p95_ms=ordered[94],
                max_ms=max(timings),
                target_p95_ms=1000,
                duration_samples_ms=timings,
                coverage=data["coverage"],
                metrics=data["metrics"],
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            listener.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "duration_samples_ms"},
            indent=2,
        )
    )
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
