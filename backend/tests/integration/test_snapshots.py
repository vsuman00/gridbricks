import sqlite3

import pytest
from sqlalchemy import event

from gridbricks.config import Settings
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.replay import SavedSnapshotSource
from gridbricks.ingestion.service import import_scope
from gridbricks.storage.database import writer_engine
from gridbricks.storage.repository import Repository


def test_absent_repository_reads_do_not_create_directories(tmp_path):
    settings = Settings(tmp_path / "absent")
    repository = Repository(settings)
    assert repository.get_snapshot() is None
    assert repository.last_import() is None
    assert (
        repository.observations(
            "unknown", "WINDFOR", "2026-01-16T00:00:00Z", "2026-01-17T00:00:00Z"
        )
        == []
    )
    assert not settings.data_dir.exists()


def test_incomplete_schema_is_unavailable_without_migrating(tmp_path):
    settings = Settings(tmp_path)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("CREATE TABLE snapshots (id TEXT PRIMARY KEY)")
    before = settings.db_path.read_bytes()
    assert Repository(settings).get_snapshot() is None
    assert settings.db_path.read_bytes() == before


def test_repeat_input_deduplicates_observations_and_keeps_download_lineage(tmp_path):
    settings = Settings(tmp_path)
    first = import_scope(settings, FixtureSource(), source_mode="fixture")
    repository = Repository(settings)
    rows = repository.observations(
        first["id"], "WINDFOR", "2026-01-16T00:00:00Z", "2026-01-17T00:00:00Z"
    )
    original_lineage = repository.lineage(rows[0]["id"], first["id"])
    assert repository.lineage_many([rows[0]["id"]], first["id"]) == {
        rows[0]["id"]: original_lineage
    }
    injection = "' OR 1=1 --"
    assert repository.lineage_many([injection], first["id"]) == {injection: []}
    assert repository.lineage_many([rows[0]["id"]], injection) == {rows[0]["id"]: []}
    second = import_scope(settings, FixtureSource(), source_mode="fixture")
    assert first["id"] != second["id"]
    assert first["input_hash"] == second["input_hash"]
    assert first["manifest_hash"] != second["manifest_hash"]
    assert repository.lineage(rows[0]["id"], first["id"]) == original_lineage
    assert len(repository.lineage(rows[0]["id"])) > len(original_lineage)
    assert (
        repository.observations(
            first["id"], "WINDFOR", "2026-01-16T00:00:00Z", "2026-01-17T00:00:00Z"
        )
        == rows
    )
    with sqlite3.connect(settings.db_path) as connection:
        count = connection.execute("SELECT count(*) FROM observations").fetchone()[0]
        assert count == first["counts"]["semantic_observations"]


def test_published_snapshots_do_not_gain_later_observations(tmp_path):
    class Modified(FixtureSource):
        def fetch(self, dataset, params):
            url, body, status = super().fetch(dataset, params)
            return url, body.replace(b'"generation":100,', b'"generation":999,'), status

    settings = Settings(tmp_path)
    initial = import_scope(settings, FixtureSource(), source_mode="fixture")
    repo = Repository(settings)
    args = ("WINDFOR", "2026-01-16T00:00:00Z", "2026-01-17T00:00:00Z")
    old = repo.observations(initial["id"], *args)
    new = import_scope(settings, Modified(), source_mode="fixture")
    assert new["input_hash"] != initial["input_hash"]
    assert repo.observations(initial["id"], *args) == old
    assert repo.observations(new["id"], *args) != old


def test_saved_input_replay_preserves_identity_and_original_retrieval(tmp_path):
    source_settings = Settings(tmp_path / "source")
    initial = import_scope(source_settings, FixtureSource(), source_mode="fixture")
    source = SavedSnapshotSource(source_settings, initial["id"])
    settings = Settings(tmp_path / "replayed")
    replayed = import_scope(settings, source, source_mode="fixture")
    assert replayed["input_hash"] == initial["input_hash"]
    assert replayed["retrieved_at"] == initial["retrieved_at"]
    assert replayed["manifest_hash"] != initial["manifest_hash"]


def test_corrupt_saved_input_cannot_replace_active_snapshot(tmp_path):
    settings = Settings(tmp_path)
    initial = import_scope(settings, FixtureSource(), source_mode="fixture")
    source = SavedSnapshotSource(settings, initial["id"])
    raw = next(iter(source.inputs.values()))
    (settings.data_dir / raw["relative_path"]).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="hash mismatch"):
        import_scope(settings, source, source_mode="fixture")
    assert Repository(settings).get_snapshot()["id"] == initial["id"]


def test_publication_transaction_rolls_back_membership_and_pointer(tmp_path, monkeypatch):
    settings = Settings(tmp_path)
    initial = import_scope(settings, FixtureSource(), source_mode="fixture")
    engine = writer_engine(settings)

    def fail_pointer(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO app_state"):
            raise RuntimeError("Injected pointer write failure")

    event.listen(engine, "before_cursor_execute", fail_pointer)
    monkeypatch.setattr("gridbricks.ingestion.service.writer_engine", lambda configured: engine)
    with pytest.raises(RuntimeError, match="pointer write failure"):
        import_scope(settings, FixtureSource(), source_mode="fixture")
    repository = Repository(settings)
    assert repository.get_snapshot()["id"] == initial["id"]
    assert repository.last_import()["status"] == "failed"
    assert all(window["status"] == "succeeded" for window in repository.last_import()["windows"])
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT count(DISTINCT snapshot_id) FROM snapshot_observations"
            ).fetchone()[0]
            == 1
        )
