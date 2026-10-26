import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { accuracyAnalysis, dataStatus } from './test/apiFixtures'

beforeEach(() => window.history.replaceState(null, '', '/'))
afterEach(() => vi.unstubAllGlobals())

describe('stored workspace malformed boundary handling', () => {
  it('starts a pinned accuracy request while snapshot status is still pending', async () => {
    window.history.replaceState(
      null,
      '',
      '/?view=accuracy&decision_from=2026-01-15&decision_to=2026-01-15&cutoff=09%3A30&snapshot_id=saved-snapshot',
    )
    let resolveStatus!: (value: unknown) => void
    const pendingStatus = new Promise((resolve) => {
      resolveStatus = resolve
    })
    const fetch = vi.fn((url: string) =>
      url.includes('data-status')
        ? pendingStatus
        : Promise.resolve({ ok: true, status: 200, json: async () => accuracyAnalysis() }),
    )
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expect(fetch.mock.calls.some(([url]) => url.includes('/api/v1/accuracy?'))).toBe(true)
    resolveStatus({ ok: true, status: 200, json: async () => dataStatus() })
    expect(await screen.findByText('Forecast error')).toBeInTheDocument()
  })

  it('rejects an empty successful snapshot without a pin loop or enabling export', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ...dataStatus(), snapshot: {} }),
      })
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Data request failed' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(window.location.search).not.toContain('snapshot_id=')
  })

  it.each([
    '?snapshot_id=..%2Foutside',
    `?snapshot_id=${'s'.repeat(129)}`,
    '?mode=unsupported&snapshot_id=safe-snapshot',
  ])('blocks malformed URL state before fetching: %s', (query) => {
    window.history.replaceState(null, '', '/' + query)
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    expect(screen.getByRole('alert')).toHaveTextContent(/invalid/i)
    expect(fetch).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
  })
})
