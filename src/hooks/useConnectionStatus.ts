import { useState, useEffect, useCallback, useRef } from 'react'

export type ConnectionState = 'online' | 'delayed' | 'offline' | 'checking'

export function useConnectionStatus(pollIntervalMs = 30000): ConnectionState {
  const [state, setState] = useState<ConnectionState>('checking')
  const isFirstCheck = useRef(true)

  const checkConnection = useCallback(async () => {
    const start = performance.now()
    try {
      await fetch('/api/v1/health', {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(isFirstCheck.current ? 2000 : 5000),
      })
      const elapsed = performance.now() - start
      setState(elapsed > 1500 ? 'delayed' : 'online')
    } catch {
      setState('offline')
    } finally {
      isFirstCheck.current = false
    }
  }, [])

  useEffect(() => {
    checkConnection()
    const timer = setInterval(checkConnection, pollIntervalMs)
    return () => clearInterval(timer)
  }, [checkConnection, pollIntervalMs])

  return state
}
