import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useData } from './useData'
import { dataStatus, forecastAnalysis } from './test/apiFixtures'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((complete) => {
    resolve = complete
  })
  return { promise, resolve }
}
const response = (value: number) => ({
  ok: true,
  status: 200,
  json: async () => ({ ...forecastAnalysis(), value }),
})

describe('stored response ordering and failures', () => {
  it('aborts the old query and ignores it even if transport still resolves later', async () => {
    const earlier = deferred<ReturnType<typeof response>>()
    const later = deferred<ReturnType<typeof response>>()
    const fetch = vi.fn().mockReturnValueOnce(earlier.promise).mockReturnValueOnce(later.promise)
    vi.stubGlobal('fetch', fetch)
    const { result, rerender } = renderHook(({ path }) => useData<{ value: number }>(path), {
      initialProps: { path: 'forecast?cutoff=09:30' },
    })
    const firstSignal = fetch.mock.calls[0][1].signal as AbortSignal
    rerender({ path: 'forecast?cutoff=10:30' })
    expect(firstSignal.aborted).toBe(true)
    expect(result.current.loading).toBe(true)
    await act(async () => {
      later.resolve(response(140))
    })
    await waitFor(() => expect(result.current.data?.value).toBe(140))
    await act(async () => {
      earlier.resolve(response(100))
    })
    expect(result.current.data?.value).toBe(140)
    expect(result.current.error).toBeUndefined()
  })

  it('immediately hides previous data while a new selection is loading', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(response(100))
        .mockImplementationOnce(() => new Promise(() => {})),
    )
    const { result, rerender } = renderHook(({ path }) => useData<{ value: number }>(path), {
      initialProps: { path: 'forecast?cutoff=09:30' },
    })
    await waitFor(() => expect(result.current.data?.value).toBe(100))
    rerender({ path: 'forecast?cutoff=10:30' })
    expect(result.current.data).toBeUndefined()
    expect(result.current.loading).toBe(true)
  })

  it('reports a bounded timeout and aborts an unresponsive transport', async () => {
    vi.useFakeTimers()
    const fetch = vi.fn(() => new Promise(() => {}))
    vi.stubGlobal('fetch', fetch)
    const { result } = renderHook(() => useData('forecast?cutoff=09:30'))
    await act(async () => {
      vi.advanceTimersByTime(15000)
    })
    expect(result.current.error?.code).toBe('timeout')
    expect(result.current.loading).toBe(false)
    expect(
      (fetch.mock.calls[0] as unknown as [string, { signal: AbortSignal }])[1].signal.aborted,
    ).toBe(true)
  })

  it('preserves the API distinction between unknown snapshot and network failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({
          error: { code: 'snapshot_not_found', message: 'Unknown snapshot' },
        }),
      }),
    )
    const { result } = renderHook(() => useData('data-status?snapshot_id=missing'))
    await waitFor(() => expect(result.current.error?.status).toBe(404))
    expect(result.current.error?.code).toBe('snapshot_not_found')
    expect(result.current.data).toBeUndefined()
  })

  it('rejects malformed data payloads and can retry the same query', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ...dataStatus(), snapshot: null, last_import: null }),
      })
    vi.stubGlobal('fetch', fetch)
    const { result } = renderHook(() => useData('data-status'))
    await waitFor(() => expect(result.current.error?.code).toBe('invalid_response'))
    await act(async () => {
      result.current.retry()
    })
    await waitFor(() => expect(result.current.data).toBeDefined())
    expect(result.current.error).toBeUndefined()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('does not request data for an inactive path', () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const { result } = renderHook(() => useData(null))
    expect(fetch).not.toHaveBeenCalled()
    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeUndefined()
  })
})
