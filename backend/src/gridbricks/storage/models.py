"""Normalized observations and immutable snapshot membership."""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, MetaData, String, Table, Text

metadata = MetaData()
runs = Table(
    "ingestion_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset", String, nullable=False),
    Column("parameters_json", Text, nullable=False),
    Column("started_at", String, nullable=False),
    Column("completed_at", String),
    Column("status", String, nullable=False),
    Column("counts_json", Text, nullable=False),
    Column("error_code", String),
)
raw = Table(
    "raw_responses",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", ForeignKey("ingestion_runs.id"), nullable=False),
    Column("request_url", Text, nullable=False),
    Column("retrieved_at", String, nullable=False),
    Column("content_hash", String, nullable=False),
    Column("relative_path", String, nullable=False),
    Column("http_status", Integer, nullable=False),
)
observations = Table(
    "observations",
    metadata,
    Column("id", String, primary_key=True),
    Column("dataset", String, nullable=False),
    Column("start_time_utc", String, nullable=False),
    Column("publish_time_utc", String, nullable=False),
    Column("generation_mw", Float),
    Column("fuel_type", String, nullable=False),
    Column("semantic_hash", String, nullable=False, unique=True),
    Column("quality_flags_json", Text, nullable=False),
)
Index(
    "ix_observation_target",
    observations.c.dataset,
    observations.c.start_time_utc,
    observations.c.publish_time_utc,
)
sources = Table(
    "observation_sources",
    metadata,
    Column("observation_id", ForeignKey("observations.id"), primary_key=True),
    Column("raw_response_id", ForeignKey("raw_responses.id"), primary_key=True),
    Column("row_index", Integer, primary_key=True),
)
snapshots = Table(
    "snapshots",
    metadata,
    Column("id", String, primary_key=True),
    Column("input_hash", String, nullable=False),
    Column("manifest_hash", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("retrieved_at", String, nullable=False),
    Column("bounds_json", Text, nullable=False),
    Column("status", String, nullable=False),
    Column("source_mode", String, nullable=False),
    Column("policy_versions_json", Text, nullable=False),
    Column("counts_json", Text, nullable=False),
    Column("manifest_path", String, nullable=False),
)
membership = Table(
    "snapshot_observations",
    metadata,
    Column("snapshot_id", ForeignKey("snapshots.id"), primary_key=True),
    Column("observation_id", ForeignKey("observations.id"), primary_key=True),
)
# Fix lineage to the exact raw inputs used by each snapshot, including resumed windows.
snapshot_raw = Table(
    "snapshot_raw_responses",
    metadata,
    Column("snapshot_id", ForeignKey("snapshots.id"), primary_key=True),
    Column("raw_response_id", ForeignKey("raw_responses.id"), primary_key=True),
)
state = Table(
    "app_state",
    metadata,
    Column("key", String, primary_key=True),
    Column("value", String, nullable=False),
)
windows = Table(
    "fetch_windows",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", ForeignKey("ingestion_runs.id"), nullable=False),
    Column("window_key", String, nullable=False),
    Column("dataset", String, nullable=False),
    Column("parameters_json", Text, nullable=False),
    Column("status", String, nullable=False),
    Column("raw_response_id", ForeignKey("raw_responses.id")),
    Column("error_code", String),
)
