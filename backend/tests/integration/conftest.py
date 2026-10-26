from datetime import date

import pytest
from fastapi.testclient import TestClient

from gridbricks.config import Settings
from gridbricks.ingestion.fixtures import FixtureSource
from gridbricks.ingestion.service import import_scope
from gridbricks.main import create_app

POLICIES = {
    "selection": "asof_per_target_v1",
    "alignment": "timestamp_matched_halfhour_reference_v1",
    "actual": "latest_in_snapshot_v1",
    "metric": "pooled_errors_v1",
}


@pytest.fixture
def analytical_dataset(tmp_path):
    settings = Settings(tmp_path / "analytical-data")
    snapshot = import_scope(settings, FixtureSource(), source_mode="fixture", policies=POLICIES)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        yield client, settings, snapshot


@pytest.fixture
def january_dataset(tmp_path):
    settings = Settings(tmp_path / "january-data")
    snapshot = import_scope(
        settings,
        FixtureSource(),
        date(2026, 1, 1),
        date(2026, 1, 31),
        source_mode="fixture",
        policies=POLICIES,
    )
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        yield client, settings, snapshot
