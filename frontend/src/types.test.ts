import { describe, expect, it } from 'vitest'
import { defaults, formatDate, nextDay } from './types'

describe('calendar labels', () => {
  it('labels the delivery day across the January boundary', () => {
    expect(nextDay('2026-01-31')).toBe('2026-02-01')
    expect(formatDate(nextDay('2026-01-31'))).toBe('01 Feb 2026')
  })

  it('uses fixed historical defaults rather than the computer date', () => {
    expect(defaults.decision).toEqual({
      decisionFrom: '2026-01-15',
      decisionTo: '2026-01-15',
      cutoff: '09:30',
    })
    expect(defaults.accuracy).toEqual({
      decisionFrom: '2026-01-01',
      decisionTo: '2026-01-31',
      cutoff: '09:30',
    })
  })
})
