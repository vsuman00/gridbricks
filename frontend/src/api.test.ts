import { afterEach, describe, expect, it, vi } from 'vitest'
import { analysisQuery, exportUrl, mw, request } from './api'
import { accuracyAnalysis, dataStatus, forecastAnalysis } from './test/apiFixtures'

afterEach(() => vi.unstubAllGlobals())

describe('stored API query boundaries', () => {
  const filters = { decisionFrom: '2026-01-15', decisionTo: '2026-01-31', cutoff: '09:30' }
  it('pins forecast CSV to the same cutoff/date/snapshot without accuracy parameters', () => {
    const query = new URLSearchParams(exportUrl('decision', filters, 'snapshot-1').split('?')[1])
    expect(Object.fromEntries(query)).toEqual({
      view: 'forecast',
      decision_date: '2026-01-15',
      cutoff: '09:30',
      snapshot_id: 'snapshot-1',
    })
    expect(analysisQuery('decision', filters, 'snapshot-1').has('decision_to')).toBe(false)
  })
  it('pins retrospective range exports without a decision-date shortcut', () => {
    const query = new URLSearchParams(exportUrl('accuracy', filters, 'snapshot-2').split('?')[1])
    expect(Object.fromEntries(query)).toEqual({
      view: 'accuracy',
      decision_from: '2026-01-15',
      decision_to: '2026-01-31',
      cutoff: '09:30',
      snapshot_id: 'snapshot-2',
    })
  })
  it('keeps missing different from zero and preserves error direction in display', () => {
    expect(mw(null)).toBe('—')
    expect(mw(0)).toBe('0')
    expect(mw(-20, true)).toBe('-20')
    expect(mw(20, true)).toBe('+20')
  })
})

function replaceAt<T>(payload: T, path: string[], value: unknown): T {
  let target = payload as Record<string, unknown>
  for (const field of path.slice(0, -1)) target = target[field] as Record<string, unknown>
  target[path[path.length - 1]] = value
  return payload
}

describe('successful HTTP responses still require valid stored-data shapes', () => {
  const invalid: [string, string, () => unknown][] = [
    ['an empty snapshot', 'data-status', () => replaceAt(dataStatus(), ['snapshot'], {})],
    [
      'a missing snapshot identifier',
      'data-status',
      () => replaceAt(dataStatus(), ['snapshot', 'snapshot_id'], undefined),
    ],
    [
      'a malformed retrieval timestamp',
      'data-status',
      () => replaceAt(dataStatus(), ['snapshot', 'retrieved_at'], 'not-a-time'),
    ],
    [
      'null snapshot counts',
      'data-status',
      () => replaceAt(dataStatus(), ['snapshot', 'counts'], null),
    ],
    [
      'an infinite snapshot count',
      'data-status',
      () => replaceAt(dataStatus(), ['snapshot', 'counts', 'expected_forecast_targets'], Infinity),
    ],
    [
      'a nonboolean alignment state',
      'data-status',
      () => replaceAt(dataStatus(), ['alignment', 'verified'], 'yes'),
    ],
    [
      'missing forecast metadata',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['meta'], undefined),
    ],
    [
      'missing required metadata fields',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['meta'], {}),
    ],
    [
      'null forecast rows',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows'], null),
    ],
    [
      'a nonarray forecast grid',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows'], {}),
    ],
    [
      'an incomplete interval',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows'], [{}]),
    ],
    [
      'an invalid interval timestamp',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows', '0', 'target_start'], 'not-a-time'),
    ],
    [
      'a string generation value',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows', '0', 'forecast_mw'], '100'),
    ],
    [
      'nonfinite generation',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows', '0', 'forecast_mw'], NaN),
    ],
    [
      'null expected count',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['coverage', 'expected_count'], null),
    ],
    [
      'infinite expected count',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['coverage', 'expected_count'], Infinity),
    ],
    [
      'a negative reason count',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['coverage', 'reason_counts', 'selected'], -1),
    ],
    [
      'null source lineage',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows', '0', 'forecast_sources'], null),
    ],
    [
      'future actuals leaking into the decision response',
      'forecast?cutoff=09:30',
      () => replaceAt(forecastAnalysis(), ['rows', '0', 'actual_mw'], 80),
    ],
    [
      'a malformed source retrieval time',
      'forecast?cutoff=09:30',
      () =>
        replaceAt(
          forecastAnalysis(),
          ['rows', '0', 'forecast_sources', '0', 'retrieved_at'],
          'invalid',
        ),
    ],
    [
      'missing accuracy metrics',
      'accuracy?cutoff=09:30',
      () => replaceAt(accuracyAnalysis(), ['metrics'], undefined),
    ],
    [
      'nonfinite accuracy metrics',
      'accuracy?cutoff=09:30',
      () => replaceAt(accuracyAnalysis(), ['metrics', 'rmse_mw'], Infinity),
    ],
    [
      'a nonarray daily breakdown',
      'accuracy?cutoff=09:30',
      () => replaceAt(accuracyAnalysis(), ['daily'], {}),
    ],
    [
      'malformed daily dates',
      'accuracy?cutoff=09:30',
      () => replaceAt(accuracyAnalysis(), ['daily', '0', 'decision_date'], 'invalid'),
    ],
    [
      'a missing constituent array',
      'accuracy?cutoff=09:30',
      () => replaceAt(accuracyAnalysis(), ['rows', '0', 'actual_constituents'], undefined),
    ],
    [
      'null constituent generation',
      'accuracy?cutoff=09:30',
      () =>
        replaceAt(
          accuracyAnalysis(),
          ['rows', '0', 'actual_constituents', '0', 'generation_mw'],
          null,
        ),
    ],
    [
      'invalid constituent boundaries',
      'accuracy?cutoff=09:30',
      () =>
        replaceAt(
          accuracyAnalysis(),
          ['rows', '0', 'actual_constituents', '0', 'end_time'],
          'invalid',
        ),
    ],
  ]
  it.each(invalid)('rejects %s as invalid_response', async (_name, path, payload) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => payload() }),
    )
    await expect(request(path, new AbortController().signal)).rejects.toMatchObject({
      code: 'invalid_response',
      status: 200,
    })
  })

  it.each<[string, () => unknown]>([
    ['data-status', dataStatus],
    ['forecast?cutoff=09:30', forecastAnalysis],
    ['accuracy?cutoff=09:30', accuracyAnalysis],
  ])('accepts complete valid %s fixtures', async (path, payload) => {
    const value = payload()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => value }),
    )
    await expect(request(path, new AbortController().signal)).resolves.toEqual(value)
  })

  it('accepts explicit gaps and null metrics without converting them to zero', async () => {
    const value = accuracyAnalysis()
    value.rows[0] = {
      ...value.rows[0],
      forecast_mw: null,
      forecast_publish_time: null,
      forecast_observation_id: null,
      forecast_age_hours: null,
      forecast_lead_hours: null,
      forecast_sources: [],
      actual_mw: null,
      error_mw: null,
      actual_constituents: [],
      state: 'missing_forecast',
    }
    value.coverage = {
      expected_count: 1,
      forecast_selected_count: 0,
      complete_actual_count: 0,
      matched_count: 0,
      matched_fraction: 0,
      reason_counts: { missing_forecast: 1 },
    }
    value.metrics = { mae_mw: null, rmse_mw: null, bias_mw: null }
    value.daily = [
      {
        decision_date: '2026-01-15',
        delivery_date: '2026-01-16',
        expected_count: 1,
        forecast_selected_count: 0,
        complete_actual_count: 0,
        matched_count: 0,
        matched_fraction: 0,
        mae_mw: null,
        rmse_mw: null,
        bias_mw: null,
      },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => value }),
    )
    await expect(request('accuracy?cutoff=09:30', new AbortController().signal)).resolves.toEqual(
      value,
    )
  })
})
