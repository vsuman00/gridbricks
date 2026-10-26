"""Rebuild a snapshot from its checksummed saved inputs without contacting Elexon."""

import hashlib
import json
from urllib.parse import parse_qsl, urlsplit

from gridbricks.ingestion.validation import digest
from gridbricks.storage.repository import Repository


class SavedSnapshotSource:
    def __init__(self, settings, snapshot_id):
        self.settings = settings
        self.snapshot = Repository(settings).get_snapshot(snapshot_id)
        if self.snapshot is None:
            raise ValueError("Unknown saved snapshot")
        path = settings.data_dir / self.snapshot["manifest_path"]
        manifest = json.loads(path.read_text())
        if digest(manifest) != self.snapshot["manifest_hash"]:
            raise ValueError("Saved manifest hash mismatch")
        self.inputs = {}
        for raw in manifest["raw_inputs"]:
            url = urlsplit(raw["request_url"])
            dataset = url.path.split("/")[-2]
            self.inputs[digest([dataset, dict(parse_qsl(url.query))])] = raw

    def fetch(self, dataset, parameters):
        raw = self.inputs[digest([dataset, parameters])]
        path = (self.settings.data_dir / raw["relative_path"]).resolve()
        if not path.is_relative_to(self.settings.data_dir):
            raise ValueError("Saved raw path is outside data storage")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != raw["content_hash"]:
            raise ValueError("Saved raw hash mismatch")
        return raw["request_url"], body, raw["http_status"]

    def retrieved_at(self, dataset, parameters):
        return self.inputs[digest([dataset, parameters])]["retrieved_at"]
