import type { Filters, View } from './types'
import { validApiResponse } from './apiValidation'
export interface Snapshot {
  snapshot_id: string
  input_hash: string
  created_at: string
  retrieved_at: string
  source_mode: 'fixture' | 'live'
  status: string
  decision_from: string
  decision_to: string
  delivery_from: string
  delivery_to: string
  policies: Record<string, string>
  counts: Record<string, number>
}
export interface DataStatus {
  snapshot: Snapshot | null
  last_import: {
    id?: string
    status: string
    completed_at?: string | null
    error_code?: string | null
    counts?: Record<string, number>
  } | null
  alignment: { verified: boolean; policy: string | null; message: string }
  sources: { dataset: string; url: string }[]
}
export interface Lineage {
  raw_response_id: string
  row_index: number
  content_hash: string
  request_url: string
  retrieved_at: string
}
export interface Interval {
  decision_date: string
  cutoff_utc: string
  target_start: string
  target_end: string
  forecast_mw: number | null
  forecast_publish_time: string | null
  forecast_observation_id: string | null
  forecast_age_hours: number | null
  forecast_lead_hours: number | null
  forecast_sources: Lineage[]
  state: string
  flags: string[]
  actual_mw?: number | null
  error_mw?: number | null
  actual_constituents?: {
    observation_id: string
    start_time: string
    end_time?: string
    publish_time: string
    generation_mw: number
    raw_sources: Lineage[]
  }[]
}
export interface Metrics {
  mae_mw: number | null
  rmse_mw: number | null
  bias_mw: number | null
}
export interface Daily extends Metrics {
  decision_date: string
  delivery_date: string
  expected_count: number
  forecast_selected_count: number
  complete_actual_count: number
  matched_count: number
  matched_fraction: number
}
export interface Analysis {
  meta: {
    snapshot_id: string
    input_hash: string
    retrieved_at: string
    source_mode: 'fixture' | 'live'
    decision_from: string
    decision_to: string
    delivery_from: string
    delivery_to: string
    cutoff_local: string
    timezone: string
    comparison_note?: string
    comparison_resolution_minutes: number
    selection_policy: string
    alignment_policy: string | null
    actual_policy: string
    metric_policy: string
    evaluation_mode: string
    unit: string
  }
  coverage: {
    expected_count: number
    forecast_selected_count: number
    reason_counts: Record<string, number>
    complete_actual_count?: number
    matched_count?: number
    matched_fraction?: number
  }
  rows: Interval[]
  metrics?: Metrics
  daily?: Daily[]
}
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 0,
  ) {
    super(message)
  }
}
export async function request<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, { signal })
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new ApiError(
      'invalid_response',
      'The local API returned an unreadable response.',
      response.status,
    )
  }
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string } })?.error
    throw new ApiError(
      error?.code ?? 'request_failed',
      error?.message ?? 'The local API request failed.',
      response.status,
    )
  }
  if (!validApiResponse(path, payload))
    throw new ApiError(
      'invalid_response',
      'The local API returned an unexpected data response.',
      response.status,
    )
  return payload as T
}
export function analysisQuery(view: View, filters: Filters, snapshotId: string) {
  const query = new URLSearchParams({ cutoff: filters.cutoff, snapshot_id: snapshotId })
  if (view === 'decision') query.set('decision_date', filters.decisionFrom)
  else {
    query.set('decision_from', filters.decisionFrom)
    query.set('decision_to', filters.decisionTo)
  }
  return query
}
export function exportUrl(view: View, filters: Filters, snapshotId: string) {
  const query = analysisQuery(view, filters, snapshotId)
  query.set('view', view === 'decision' ? 'forecast' : 'accuracy')
  return `/api/v1/export?${query}`
}
export function mw(value: number | null | undefined, signed = false) {
  return value == null
    ? '—'
    : new Intl.NumberFormat('en-GB', {
        maximumFractionDigits: 2,
        signDisplay: signed ? 'exceptZero' : 'auto',
      }).format(value)
}
export function timestamp(value: string | null | undefined) {
  return value
    ? new Intl.DateTimeFormat('en-GB', {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: 'Europe/London',
      }).format(new Date(value))
    : 'Unavailable'
}
