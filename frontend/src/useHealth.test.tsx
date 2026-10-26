import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useHealth } from './useHealth'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('local process health', () => {
  it('checks health without requesting source or analytical data', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) })
    vi.stubGlobal('fetch', fetch)
    const { result } = renderHook(useHealth)
    expect(result.current.connection).toBe('checking')
    await waitFor(() => expect(result.current.connection).toBe('connected'))
    expect(fetch).toHaveBeenCalledOnce()
    expect(fetch).toHaveBeenCalledWith('/api/v1/health', { signal: expect.any(AbortSignal) })
  })

  it.each([
    ['network error', () => Promise.reject(new TypeError('offline'))],
    ['HTTP error', () => Promise.resolve({ ok: false, status: 503 })],
    [
      'unknown body',
      () => Promise.resolve({ ok: true, json: async () => ({ status: 'unknown' }) }),
    ],
  ])('shows unavailable for %s', async (_case, response) => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(response))
    const { result } = renderHook(useHealth)
    await waitFor(() => expect(result.current.connection).toBe('unavailable'))
  })

  it('retries a failed health check', async () => {
    const fetch = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('offline'))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok' }) })
    vi.stubGlobal('fetch', fetch)
    const { result } = renderHook(useHealth)
    await waitFor(() => expect(result.current.connection).toBe('unavailable'))
    act(() => result.current.retry())
    await waitFor(() => expect(result.current.connection).toBe('connected'))
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('ignores a timed-out response that resolves after the retry', async () => {
    vi.useFakeTimers()
    let resolveOld!: (value: unknown) => void
    const fetch = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve
          }),
      )
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok' }) })
    vi.stubGlobal('fetch', fetch)
    const { result } = renderHook(useHealth)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(result.current.connection).toBe('unavailable')
    expect(fetch.mock.calls[0][1].signal.aborted).toBe(true)
    await act(async () => result.current.retry())
    expect(result.current.connection).toBe('connected')
    await act(async () => resolveOld({ ok: false, status: 503 }))
    expect(result.current.connection).toBe('connected')
  })

  it('cancels an outstanding check when the details panel unmounts', () => {
    const fetch = vi.fn<typeof globalThis.fetch>(() => new Promise(() => {}))
    vi.stubGlobal('fetch', fetch)
    const { unmount } = renderHook(useHealth)
    const signal = fetch.mock.calls[0]?.[1] as { signal: AbortSignal } | undefined
    unmount()
    expect(signal?.signal.aborted).toBe(true)
  })
})
