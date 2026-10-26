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
    (assets_dir / "app.js").write_text("document.title = 'GridBricks'")
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
        assert client.get("/assets/app.js").status_code == 200
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert health.headers["content-security-policy"] == (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        assert client.get("/api/v1/data-status").json()["snapshot"] is None
        assert client.get("/", headers={"Host": "untrusted.example"}).status_code == 400
        assert not settings.db_path.exists()


def test_container_entry_requires_a_built_frontend(tmp_path: Path):
    with pytest.raises(ValueError, match="missing index.html"):
        create_app(Settings(data_dir=tmp_path / "data", static_dir=tmp_path / "missing"))
