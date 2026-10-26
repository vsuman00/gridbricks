"""Read-only access to explicit snapshot membership, never a migration trigger."""

import json
import sqlite3
from contextlib import contextmanager

from gridbricks.config import Settings
from gridbricks.ingestion.validation import timestamp
from gridbricks.storage.models import metadata


class Repository:
    def __init__(self, settings: Settings):
        self.settings = settings

    @contextmanager
    def _connection(self):
        connection = None
        try:
            if self.settings.db_path.is_file():
                connection = sqlite3.connect(self.settings.db_path.as_uri() + "?mode=ro", uri=True)
                connection.row_factory = sqlite3.Row
                present = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not set(metadata.tables) <= present:
                    connection.close()
                    connection = None
            yield connection
        finally:
            if connection is not None:
                connection.close()

    def get_snapshot(self, snapshot_id=None):
        with self._connection() as connection:
            if connection is None:
                return None
            if snapshot_id is None:
                pointer = connection.execute(
                    "SELECT value FROM app_state WHERE key='active_snapshot'"
                ).fetchone()
                if pointer is None:
                    return None
                snapshot_id = pointer[0]
            row = connection.execute(
                "SELECT * FROM snapshots WHERE id=?", (snapshot_id,)
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            for key, target in (
                ("bounds_json", "bounds"),
                ("policy_versions_json", "policies"),
                ("counts_json", "counts"),
            ):
                result[target] = json.loads(result.pop(key))
            return result

    def observations(self, snapshot_id, dataset, start, end):
        with self._connection() as connection:
            if connection is None:
                return []
            rows = connection.execute(
                "SELECT o.* FROM observations o JOIN snapshot_observations s "
                "ON s.observation_id=o.id WHERE s.snapshot_id=? AND o.dataset=? "
                "AND o.start_time_utc>=? AND o.start_time_utc<? "
                "ORDER BY o.start_time_utc,o.publish_time_utc,o.semantic_hash",
                (snapshot_id, dataset, timestamp(start), timestamp(end)),
            ).fetchall()
            result = []
            for row in rows:
                observation = dict(row)
                observation["quality_flags"] = json.loads(observation.pop("quality_flags_json"))
                result.append(observation)
            return result

    def lineage(self, observation_id, snapshot_id=None):
        with self._connection() as connection:
            if connection is None:
                return []
            sql = (
                "SELECT s.raw_response_id,s.row_index,r.content_hash,r.request_url,r.retrieved_at "
                "FROM observation_sources s JOIN raw_responses r ON r.id=s.raw_response_id "
                "WHERE s.observation_id=?"
            )
            parameters = [observation_id]
            if snapshot_id is not None:
                sql += (
                    " AND EXISTS (SELECT 1 FROM snapshot_raw_responses sr WHERE "
                    "sr.snapshot_id=? AND sr.raw_response_id=r.id)"
                )
                parameters.append(snapshot_id)
            return [
                dict(row)
                for row in connection.execute(
                    sql + " ORDER BY r.retrieved_at,r.id,s.row_index", parameters
                ).fetchall()
            ]

    def lineage_many(self, observation_ids, snapshot_id):
        """Fetch pinned provenance in bounded chunks, with one read-only connection."""
        result = {observation_id: [] for observation_id in observation_ids}
        ids = list(result)
        with self._connection() as connection:
            if connection is None:
                return result
            for offset in range(0, len(ids), 800):
                chunk = ids[offset : offset + 800]
                placeholders = ",".join("?" for _ in chunk)
                # Only '?' placeholders are constructed; all IDs are bound separately below.
                sql = (
                    "SELECT s.observation_id,s.raw_response_id,s.row_index,r.content_hash,"  # noqa: S608
                    "r.request_url,r.retrieved_at FROM observation_sources s "
                    "JOIN raw_responses r ON r.id=s.raw_response_id "
                    "JOIN snapshot_raw_responses sr ON sr.raw_response_id=r.id "
                    "WHERE sr.snapshot_id=? AND s.observation_id IN (" + placeholders + ") "
                    "ORDER BY r.retrieved_at,r.id,s.row_index"
                )
                for row in connection.execute(sql, [snapshot_id, *chunk]).fetchall():
                    source = dict(row)
                    result[source.pop("observation_id")].append(source)
        return result

    def last_import(self):
        with self._connection() as connection:
            if connection is None:
                return None
            row = connection.execute(
                "SELECT * FROM ingestion_runs ORDER BY started_at DESC,id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["parameters"] = json.loads(result.pop("parameters_json"))
            result["counts"] = json.loads(result.pop("counts_json"))
            result["windows"] = [
                dict(window)
                for window in connection.execute(
                    "SELECT dataset,parameters_json,status,error_code FROM fetch_windows "
                    "WHERE run_id=? ORDER BY window_key",
                    (result["id"],),
                ).fetchall()
            ]
            for window in result["windows"]:
                window["parameters"] = json.loads(window.pop("parameters_json"))
            return result
