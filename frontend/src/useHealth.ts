import { useEffect, useState } from 'react'

export type Connection = 'checking' | 'connected' | 'unavailable'

export function useHealth() {
  const [connection, setConnection] = useState<Connection>('checking')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setConnection('unavailable')
      controller.abort()
    }, 5000)

    async function check() {
      try {
        const response = await fetch('/api/v1/health', { signal: controller.signal })
        if (!response.ok) throw new Error('Health request failed')
        const payload: unknown = await response.json()
        if (typeof payload !== 'object' || payload === null ||
          !('status' in payload) || payload.status !== 'ok') {
          throw new Error('Unexpected health response')
        }
        if (!controller.signal.aborted) setConnection('connected')
      } catch {
        if (!controller.signal.aborted) setConnection('unavailable')
      } finally {
        window.clearTimeout(timeout)
      }
    }
    void check()
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [attempt])

  return {
    connection,
    retry() {
      setConnection('checking')
      setAttempt((previous) => previous + 1)
    },
  }
}
