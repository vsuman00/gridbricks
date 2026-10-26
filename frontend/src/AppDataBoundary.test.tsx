import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { dataStatus } from './test/apiFixtures'

beforeEach(() => window.history.replaceState(null, '', '/'))
afterEach(() => vi.unstubAllGlobals())

describe('stored workspace malformed boundary handling', () => {
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
