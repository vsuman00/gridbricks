import { describe, expect, it } from 'vitest'
import { parseQuery, serializeQuery, validateFilters } from './state'
import { defaults } from './types'

describe('stored-data URL and validation', () => {
  it('restores a shareable accuracy range and pinned snapshot', () => {
    const filters = { decisionFrom: '2026-01-30', decisionTo: '2026-01-31', cutoff: '07:05' }
    expect(parseQuery(serializeQuery('accuracy', filters, 'safe-snapshot'))).toEqual({
      view: 'accuracy',
      snapshotId: 'safe-snapshot',
      hasDates: true,
      filters,
      warning: null,
    })
  })

  it('does not add an end-date parameter to a decision URL', () => {
    const search = serializeQuery('decision', defaults.decision)
    expect(new URLSearchParams(search).has('decision_to')).toBe(false)
    expect(parseQuery(search).filters).toEqual(defaults.decision)
  })

  it.each([
    '?view=trading',
    '?decision_date=2026-02-01',
    '?view=accuracy&decision_from=2026-01-20&decision_to=2026-01-19',
    '?cutoff=24%3A00',
    '?preview=unknown',
    '?decision_date=2026-01-02&decision_date=2026-01-31',
  ])('recovers invalid links with explicit warning: %s', (search) => {
    const query = parseQuery(search)
    expect(query.warning).toMatch(/invalid or unsupported filters/i)
    expect(query.filters).toEqual(defaults[query.view])
  })

  it('validates calendar bounds, ordering, and cutoff separately', () => {
    expect(
      validateFilters({ decisionFrom: '', decisionTo: '2026-02-01', cutoff: '9:30' }, 'accuracy'),
    ).toHaveProperty('decisionFrom')
    expect(
      validateFilters(
        { decisionFrom: '2026-01-20', decisionTo: '2026-01-19', cutoff: '12:60' },
        'accuracy',
      ),
    ).toEqual({
      decisionTo: 'Choose an end date on or after the start date.',
      cutoff: 'Enter a buying cutoff in HH:MM format.',
    })
    expect(
      validateFilters({ decisionFrom: '2026-01-31', decisionTo: '', cutoff: '23:59' }, 'decision'),
    ).toEqual({})
  })

  it('bounds malformed URL input before parsing it', () => {
    const query = parseQuery(`?decision_date=${'x'.repeat(2048)}`)
    expect(query.filters).toEqual(defaults.decision)
    expect(query.warning).toMatch(/invalid|too long/i)
  })

  it.each([
    '?snapshot_id=',
    '?snapshot_id=..%2Foutside',
    '?snapshot_id=%3Cscript%3E',
    `?snapshot_id=${'s'.repeat(129)}`,
    '?mode=unsupported',
    '?mode=unsupported&snapshot_id=otherwise-valid',
    '?mode=preview',
  ])('rejects malformed snapshot or mode before data requests: %s', (search) => {
    const query = parseQuery(search)
    expect(query.warning).toBeTruthy()
    expect(query.snapshotId).toBeNull()
  })

  it('accepts safe snapshot identifiers up to the declared length bound', () => {
    const identifier = 'safe_snapshot-'.padEnd(128, 's')
    const query = parseQuery(`?snapshot_id=${identifier}`)
    expect(query.warning).toBeNull()
    expect(query.snapshotId).toBe(identifier)
  })
})
