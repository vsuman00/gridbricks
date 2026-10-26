import { useEffect, useState } from 'react'
import { ApiError, request } from './api'

interface Result<T> {
  key: string
  data?: T
  error?: ApiError
}
export function useData<T>(path: string | null) {
  const [result, setResult] = useState<Result<T> | null>(null)
  const [attempt, setAttempt] = useState(0)
  const key = `${path ?? ''}:${attempt}`
  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      if (!controller.signal.aborted) {
        setResult({
          key,
          error: new ApiError('timeout', 'The local API did not respond in time. Try again.'),
        })
        controller.abort()
      }
    }, 15000)
    void request<T>(path, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data })
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setResult({
            key,
            error:
              error instanceof ApiError
                ? error
                : new ApiError(
                    'network_error',
                    'The local API could not be reached. Start the backend, then try again.',
                  ),
          })
      })
      .finally(() => window.clearTimeout(timeout))
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [path, key])
  const current = path && result?.key === key ? result : null
  return {
    data: current?.data,
    error: current?.error,
    loading: !!path && !current,
    retry: () => setAttempt((previous) => previous + 1),
  }
}
