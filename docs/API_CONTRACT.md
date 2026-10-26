# Application integration contract

Implementation handoff for the authorized full-project build. This refines the architecture's proposed JSON field names without changing cutoff, snapshot, provenance or error rules. All analytical computation remains in Python. Frontend code must use stored API responses; it must never download Elexon data or calculate its own metrics.

## Storage/service boundary

`gridbricks.config.Settings` resolves `GRIDBRICKS_DATA_DIR` (default project-root `data`) and SQLite storage. The API reads existing schema/snapshots only. The separate CLI migrates and imports; starting the web API must not migrate, ingest or create a dataset.

The ingestion/storage owner exposes `gridbricks.storage.repository.Repository(settings)` with `get_snapshot(snapshot_id=None) -> dict | None`, `observations(snapshot_id, dataset, start, end) -> list[dict]`, `lineage(observation_id) -> list[dict]`, and `last_import() -> dict | None`. Snapshot dictionaries contain `id`, `input_hash`, `manifest_hash`, `created_at`, `retrieved_at`, `bounds` (`decision_from`, `decision_to`, `delivery_from`, `delivery_to`, `forecast_publish_from`, `forecast_publish_to`), `status`, `source_mode` (`fixture` or `live`), `policies`, `counts`. Observation dictionaries contain `id`, `dataset`, `start_time_utc`, `publish_time_utc`, `generation_mw`, `fuel_type`, `quality_flags`. Missing active schema/database returns no snapshot rather than causing filesystem writes. All timestamps are canonical UTC strings.

Exact snapshot membership must be fixed. One request resolves its snapshot once, then passes that ID to all reads. An explicit unknown ID produces 404; no active dataset produces 503 for analytical routes. Source failure retains the active snapshot. Import CLI records failed windows and raw hashes separately from recognized source gaps.

## API responses

All implemented browser routes are GET under `/api/v1`. Health remains process-only. Unknown/repeated/inconsistent query parameters are rejected. January dates and HH:MM cutoffs are required for analytical queries; timezone is fixed to Europe/London.

API responses include `X-Request-ID`, a generated opaque ID that matches the server's JSON-line `http_request` diagnostic event. The ID is for local troubleshooting and carries no analytical meaning.

The local convenience routes `GET /` and `GET /health` sit outside the versioned API. `/` redirects to the development UI at `http://127.0.0.1:5173/`; `/health` is an alias of `/api/v1/health` and does not check or import data. Browser asset paths are served by the frontend, not the API.

`/data-status?snapshot_id=...` returns `{snapshot, last_import, alignment, sources}`. `snapshot` can be null when no dataset exists: this diagnostic route still returns 200 so an import failure can be inspected. Unknown explicit snapshot returns 404. `alignment` contains `verified`, `policy`, `message`; `verified` is true only when the snapshot's complete selection/alignment/actual/metric policy set is supported. Snapshot fields use browser names `snapshot_id`, `input_hash`, `created_at`, `retrieved_at`, `source_mode`, `status`, `decision_from`, `decision_to`, `delivery_from`, `delivery_to`, `policies`, `counts`. No invented retrieval timestamps or healthy-data claims.

`/forecast?decision_date=2026-01-15&cutoff=09:30&snapshot_id=...` and `/accuracy?decision_from=2026-01-01&decision_to=2026-01-31&cutoff=09:30&snapshot_id=...` share an envelope:

- `meta`: `snapshot_id`, `input_hash`, `retrieved_at`, `source_mode`, `decision_from`, `decision_to`, `delivery_from`, `delivery_to`, `cutoff_local`, `timezone`, `comparison_resolution_minutes`, `selection_policy`, `alignment_policy`, `actual_policy`, `metric_policy`, `evaluation_mode`, `unit`.
- `coverage`: `expected_count`, `forecast_selected_count`, `reason_counts`; accuracy also includes `complete_actual_count`, `matched_count`, `matched_fraction`.
- `rows`: every expected target, sorted by decision date then target start. Fields: `decision_date`, `cutoff_utc`, `target_start`, `target_end`, `forecast_mw`, `forecast_publish_time`, `forecast_observation_id`, `forecast_age_hours`, `forecast_lead_hours`, `forecast_sources`, `state`, `flags`. Missing fields use null, never zero. `target_end` marks the display grid, not a claim of forecast physical averaging.
- Accuracy rows add `actual_mw`, `actual_constituents`, `error_mw`. Each constituent retains `observation_id`, `start_time`, `end_time` (half-hour boundary), `publish_time`, `generation_mw`, `raw_sources`. Forecast responses must omit actual and error fields entirely.
- Accuracy adds `metrics: {mae_mw, rmse_mw, bias_mw}` and `daily`. Each daily entry has `decision_date`, `delivery_date`, `expected_count`, `forecast_selected_count`, `complete_actual_count`, `matched_count`, `matched_fraction`, `mae_mw`, `rmse_mw`, `bias_mw`. No matches produces null metrics.

Lineage entries retain `raw_response_id`, `row_index`, `content_hash`, `request_url`, `retrieved_at`. Forecast publication age is cutoff minus publication; lead time is target minus publication. Conflicting newest eligible records remain unresolved with no fallback. Signed error is forecast minus actual.

`/export` requires `view=forecast|accuracy`, the corresponding query dates/cutoff and explicit `snapshot_id`. It calls the same analytical service as JSON. All expected rows, nulls/reasons, policies, publications and constituent lineage survive CSV. Numeric negative errors stay numeric; free-text formula prefixes are escaped. Unsupported alignment yields 409 until source research selects and documents a defensible policy.

Error envelope: `{error: {code, message, details}}`; 422 invalid input/range, 404 unknown snapshot, 503 `dataset_unavailable`, 409 `alignment_unverified`. No-source data and API/network failures remain distinguishable in the UI. Shared API metadata always labels fixture inputs as synthetic and actual comparison as retrospective.

## Frontend integration rules

Preserve the existing mockup-inspired SCSS layout and reduced-motion behavior. Default to the real stored-data workflow; retain illustrations only behind an explicitly selected UI-preview mode, with truthful labels. Initial data-status resolves/pins the active snapshot and chooses a covered January date. Applied filters, view and snapshot remain in the URL. Abort or ignore superseded status/analytical requests; an old response must never replace a newer selection. Chart gaps, cards, tables and CSV derive from the same response/snapshot. Export is enabled only when a real response with a pinned snapshot exists.

The PRD, architecture and [ADR-002](decisions/0002-timestamp-matched-reference.md) now adopt `timestamp_matched_halfhour_reference_v1`. Accuracy uses one exact-time FUELHH constituent and preserves `temporal_reference_mismatch`. Include `meta.comparison_note`: "Timestamp-matched benchmark: WINDFOR compared with the half-hour average starting at the same timestamp; physical averaging equivalence is unverified." This note is visible in Accuracy and retained in CSV/presentations. Unknown/unverified snapshot policies still return 409. Do not infer an hourly average from cadence.
