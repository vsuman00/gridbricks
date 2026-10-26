"""Writer-only schema migration entry point."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from gridbricks.config import Settings


def writer_engine(settings: Settings):
    return create_engine("sqlite:///" + str(settings.db_path))


def migrate(settings: Settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[3] / "migrations")
    )
    with writer_engine(settings).begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
