from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gridbricks.config import Settings
from gridbricks.main import create_app


def test_container_entry_serves_frontend_and_api_on_one_allowed_host(tmp_path: Path):
    static_dir = tmp_path / "frontend"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text('<div id="root">GridBricks</div>')
    (assets_dir / "app-abc12345.js").write_text("document.title = 'GridBricks'")
    (assets_dir / "plain.js").write_text("document.title = 'Unhashed'")
    settings = Settings(
        data_dir=tmp_path / "data",
        static_dir=static_dir,
        public_hosts=("demo.vercel.app",),
    )

    with TestClient(create_app(settings), base_url="https://demo.vercel.app") as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "GridBricks" in home.text
        assert "script-src 'self'" in home.headers["content-security-policy"]
        assert home.headers["cache-control"] == "public, max-age=0, s-maxage=3600"
        hashed_asset = client.get("/assets/app-abc12345.js")
        assert hashed_asset.status_code == 200
        assert hashed_asset.headers["cache-control"] == (
            "public, max-age=31536000, s-maxage=31536000, immutable"
        )
        assert client.get("/assets/plain.js").headers["cache-control"] == "no-store"
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert health.headers["cache-control"] == "no-store"
        assert health.headers["content-security-policy"] == (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        assert client.get("/api/v1/data-status").json()["snapshot"] is None
        assert client.get("/api/v1/data-status").headers["cache-control"] == "no-store"
        assert client.get("/missing").headers["cache-control"] == "no-store"
        assert client.get("/", headers={"Host": "untrusted.example"}).status_code == 400
        assert not settings.db_path.exists()


def test_container_entry_requires_a_built_frontend(tmp_path: Path):
    with pytest.raises(ValueError, match="missing index.html"):
        create_app(Settings(data_dir=tmp_path / "data", static_dir=tmp_path / "missing"))


def test_immutable_deployment_caches_only_successful_public_snapshot_reads(tmp_path: Path):
    from gridbricks.ingestion.fixtures import FixtureSource
    from gridbricks.ingestion.service import import_scope

    settings = Settings(data_dir=tmp_path / "data", immutable_deployment=True)
    snapshot = import_scope(
        settings,
        FixtureSource(),
        source_mode="fixture",
        policies={
            "selection": "asof_per_target_v1",
            "alignment": "timestamp_matched_halfhour_reference_v1",
            "actual": "latest_in_snapshot_v1",
            "metric": "pooled_errors_v1",
        },
    )
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        assert client.get("/api/v1/data-status").headers["cache-control"] == (
            "public, max-age=0, s-maxage=3600"
        )
        accuracy = client.get(
            "/api/v1/accuracy",
            params={
                "decision_from": "2026-01-15",
                "decision_to": "2026-01-15",
                "cutoff": "09:30",
                "snapshot_id": snapshot["id"],
            },
        )
        assert accuracy.status_code == 200
        assert accuracy.headers["cache-control"] == "public, max-age=0, s-maxage=3600"
        assert (
            client.get("/api/v1/forecast?decision_date=2026-01-15&cutoff=09:30").headers[
                "cache-control"
            ]
            == "no-store"
        )
        assert (
            client.get("/api/v1/data-status?snapshot_id=unknown").headers["cache-control"]
            == "no-store"
        )
        assert client.get("/api/v1/health").headers["cache-control"] == "no-store"
