import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Analysis } from './api'
import { DataOverview } from './components/DataOverview'
import { DataLoading } from './components/DataLoading'

function completeData(): Analysis {
  return {
    meta: {
      snapshot_id: 'saved-snapshot',
      input_hash: 'input-hash',
      retrieved_at: '2026-10-26T12:00:00Z',
      source_mode: 'live',
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
      evaluation_mode: 'retrospective',
      unit: 'MW',
      comparison_note: 'Physical averaging equivalence is unverified.',
    },
    coverage: {
      expected_count: 1,
      forecast_selected_count: 1,
      complete_actual_count: 1,
      matched_count: 1,
      matched_fraction: 1,
      reason_counts: { matched: 1 },
    },
    metrics: { mae_mw: 20, rmse_mw: 20, bias_mw: -20 },
    rows: [
      {
        decision_date: '2026-01-15',
        cutoff_utc: '2026-01-15T09:30:00Z',
        target_start: '2026-01-16T00:00:00Z',
        target_end: '2026-01-16T01:00:00Z',
        forecast_mw: -20,
        forecast_publish_time: '2026-01-15T08:30:00Z',
        forecast_observation_id: 'forecast',
        forecast_age_hours: 1,
        forecast_lead_hours: 15.5,
        forecast_sources: [],
        actual_mw: 0,
        actual_constituents: [],
        error_mw: -20,
        state: 'matched',
        flags: ['temporal_reference_mismatch'],
      },
    ],
    daily: [],
  }
}

describe('measured overview interpretation', () => {
  it('labels the applied cutoff and the demo default in loaded and loading states', () => {
    const data = completeData()
    data.meta.cutoff_local = '09:00'
    const { unmount } = render(
      <DataOverview data={data} view="accuracy" onOpenDetails={() => {}} />,
    )
    expect(screen.getByText('Applied cutoff: 09:00 UK · Demo default: 09:30 UK.')).toBeVisible()
    unmount()
    render(<DataLoading view="accuracy" cutoff="09:00" />)
    expect(screen.getByText('Applied cutoff: 09:00 UK · Demo default: 09:30 UK.')).toBeVisible()
  })

  it('does not describe complete matched data as incomplete coverage', () => {
    render(<DataOverview data={completeData()} view="accuracy" onOpenDetails={() => {}} />)
    expect(screen.queryByText(/Incomplete coverage/)).not.toBeInTheDocument()
  })

  it('places valid negative net generation inside the visible plotting bounds', () => {
    render(<DataOverview data={completeData()} view="accuracy" onOpenDetails={() => {}} />)
    const point = screen
      .getByRole('img', { name: /Selected forecast and later actual wind reference/ })
      .querySelector('circle')!
    const y = Number(point.getAttribute('cy'))
    expect(y).toBeGreaterThanOrEqual(30)
    expect(y).toBeLessThanOrEqual(225)
  })

  it('explains the limited sample when exactly one interval is matched', () => {
    render(<DataOverview data={completeData()} view="accuracy" onOpenDetails={() => {}} />)
    expect(screen.getByText(/limited sample|one matched|single matched/i)).toBeInTheDocument()
  })
})
