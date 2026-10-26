import type { Analysis, DataStatus, Lineage } from '../api'

export const lineage: Lineage = {
  raw_response_id: 'raw-response-1',
  row_index: 0,
  content_hash: 'a'.repeat(64),
  request_url: 'fixture://synthetic/WINDFOR',
  retrieved_at: '2026-10-26T12:00:00Z',
}

export function forecastAnalysis(): Analysis {
  return {
    meta: {
      snapshot_id: 'saved-snapshot',
      input_hash: 'b'.repeat(64),
      retrieved_at: '2026-10-26T12:00:00Z',
      source_mode: 'fixture',
      decision_from: '2026-01-15',
      decision_to: '2026-01-15',
      delivery_from: '2026-01-16',
      delivery_to: '2026-01-16',
      cutoff_local: '09:30',
      timezone: 'Europe/London',
      comparison_resolution_minutes: 60,
      selection_policy: 'asof_per_target_v1',
      alignment_policy: 'timestamp_matched_halfhour_reference_v1',
      actual_policy: 'latest_in_snapshot_v1',
      metric_policy: 'pooled_errors_v1',
      evaluation_mode: 'decision',
      unit: 'MW',
      comparison_note: 'A timestamp-matched benchmark.',
    },
    coverage: { expected_count: 1, forecast_selected_count: 1, reason_counts: { selected: 1 } },
    rows: [
      {
        decision_date: '2026-01-15',
        cutoff_utc: '2026-01-15T09:30:00Z',
        target_start: '2026-01-16T00:00:00Z',
        target_end: '2026-01-16T01:00:00Z',
        forecast_mw: 100,
        forecast_publish_time: '2026-01-15T08:30:00Z',
        forecast_observation_id: 'forecast-1',
        forecast_age_hours: 1,
        forecast_lead_hours: 15.5,
        forecast_sources: [{ ...lineage }],
        state: 'selected',
        flags: [],
      },
    ],
  }
}

export function accuracyAnalysis(): Analysis {
  const value = forecastAnalysis()
  value.meta.evaluation_mode = 'retrospective'
  value.coverage = {
    expected_count: 1,
    forecast_selected_count: 1,
    complete_actual_count: 1,
    matched_count: 1,
    matched_fraction: 1,
    reason_counts: { matched: 1 },
  }
  value.rows[0] = {
    ...value.rows[0],
    actual_mw: 80,
    error_mw: 20,
    state: 'matched',
    flags: ['temporal_reference_mismatch'],
    actual_constituents: [
      {
        observation_id: 'actual-1',
        start_time: '2026-01-16T00:00:00Z',
        end_time: '2026-01-16T00:30:00Z',
        publish_time: '2026-01-16T00:30:00Z',
        generation_mw: 80,
        raw_sources: [{ ...lineage, request_url: 'fixture://synthetic/FUELHH' }],
      },
    ],
  }
  value.metrics = { mae_mw: 20, rmse_mw: 20, bias_mw: 20 }
  value.daily = [
    {
      decision_date: '2026-01-15',
      delivery_date: '2026-01-16',
      expected_count: 1,
      forecast_selected_count: 1,
      complete_actual_count: 1,
      matched_count: 1,
      matched_fraction: 1,
      mae_mw: 20,
      rmse_mw: 20,
      bias_mw: 20,
    },
  ]
  return value
}

export function dataStatus(): DataStatus {
  return {
    snapshot: {
      snapshot_id: 'saved-snapshot',
      input_hash: 'b'.repeat(64),
      created_at: '2026-10-26T12:00:00Z',
      retrieved_at: '2026-10-26T12:00:00Z',
      source_mode: 'fixture',
      status: 'succeeded',
      decision_from: '2026-01-15',
      decision_to: '2026-01-15',
      delivery_from: '2026-01-16',
      delivery_to: '2026-01-16',
      policies: {
        selection: 'asof_per_target_v1',
        alignment: 'timestamp_matched_halfhour_reference_v1',
        actual: 'latest_in_snapshot_v1',
        metric: 'pooled_errors_v1',
      },
      counts: { expected_forecast_targets: 24, expected_actual_targets: 48 },
    },
    last_import: {
      id: 'import-1',
      status: 'succeeded',
      completed_at: '2026-10-26T12:00:00Z',
      counts: {},
    },
    alignment: {
      verified: true,
      policy: 'timestamp_matched_halfhour_reference_v1',
      message: 'A timestamp-matched benchmark.',
    },
    sources: [{ dataset: 'WINDFOR', url: 'https://bmrs.elexon.co.uk/wind-generation' }],
  }
}
