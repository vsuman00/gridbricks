"""Shared local storage configuration; construction has no filesystem effects."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def _public_hosts() -> tuple[str, ...]:
    values = [
        *os.environ.get("GRIDBRICKS_ALLOWED_HOSTS", "").split(","),
        os.environ.get("VERCEL_URL", ""),
        os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", ""),
    ]
    hosts = []
    for value in values:
        host = value.strip()
        if not host:
            continue
        if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            raise ValueError("Allowed hosts must be bare DNS names")
        if host not in hosts:
            hosts.append(host)
    return tuple(hosts)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("GRIDBRICKS_DATA_DIR", Path(__file__).resolve().parents[3] / "data")
        )
    )
    static_dir: Path | None = field(
        default_factory=lambda: (
            Path(os.environ["GRIDBRICKS_STATIC_DIR"])
            if os.environ.get("GRIDBRICKS_STATIC_DIR")
            else None
        )
    )
    public_hosts: tuple[str, ...] = field(default_factory=_public_hosts)

    def __post_init__(self):
        object.__setattr__(self, "data_dir", Path(self.data_dir).expanduser().resolve())
        if self.static_dir is not None:
            object.__setattr__(self, "static_dir", Path(self.static_dir).expanduser().resolve())

    @property
    def db_path(self) -> Path:
        return self.data_dir / "gridbricks.sqlite3"
