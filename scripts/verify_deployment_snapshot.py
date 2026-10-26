"""Check the immutable live snapshot packaged in the Vercel image."""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from gridbricks.config import Settings
from gridbricks.ingestion.validation import digest
from gridbricks.storage.repository import Repository

EXPECTED_SNAPSHOT_ID = "9e2b992d3cb943aa9a82d4c3e71fd68f"
EXPECTED_INPUT_HASH = "dfebf7e8895557c162096eb06e3cf1fcf17971e5dbd29974290310de231bb94d"
EXPECTED_RAW_COUNT = 69


def verify(data_dir: Path) -> dict:
    settings = Settings(data_dir=data_dir)
    if not settings.db_path.is_file():
        raise ValueError("Deployment database is missing")
    with sqlite3.connect(settings.db_path.as_uri() + "?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Deployment database integrity failed")

    repository = Repository(settings)
    snapshot = repository.get_snapshot()
    if snapshot is None:
        raise ValueError("Deployment snapshot is missing")
    if (
        snapshot["id"] != EXPECTED_SNAPSHOT_ID
        or snapshot["input_hash"] != EXPECTED_INPUT_HASH
        or snapshot["source_mode"] != "live"
    ):
        raise ValueError("Deployment snapshot identity does not match the reviewed live input")

    manifest_path = (settings.data_dir / snapshot["manifest_path"]).resolve()
    if not manifest_path.is_relative_to(settings.data_dir):
        raise ValueError("Deployment manifest path escapes its data directory")
    manifest = json.loads(manifest_path.read_text())
    if digest(manifest) != snapshot["manifest_hash"]:
        raise ValueError("Deployment manifest hash mismatch")
    if manifest["snapshot_id"] != snapshot["id"] or manifest["input_hash"] != EXPECTED_INPUT_HASH:
        raise ValueError("Deployment manifest identity mismatch")
    if len(manifest["raw_inputs"]) != EXPECTED_RAW_COUNT:
        raise ValueError("Deployment raw-input count mismatch")
    for raw in manifest["raw_inputs"]:
        raw_path = (settings.data_dir / raw["relative_path"]).resolve()
        if not raw_path.is_relative_to(settings.data_dir):
            raise ValueError("Deployment raw path escapes its data directory")
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != raw["content_hash"]:
            raise ValueError("Deployment raw input hash mismatch")

    return {
        "snapshot_id": snapshot["id"],
        "input_hash": snapshot["input_hash"],
        "raw_inputs_verified": len(manifest["raw_inputs"]),
        "source_mode": snapshot["source_mode"],
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_deployment_snapshot.py DATA_DIR")
    print(json.dumps(verify(Path(sys.argv[1])), sort_keys=True))
