import { useCallback, useEffect, useRef, useState } from 'react'
import { REFRESH_INTERVAL_MS } from '../constants'
import { getErrorMessage } from '../utils/errors'

interface UsePollingOptions {
  enabled?: boolean
  intervalMs?: number
}

interface UsePollingResult<T> {
  data: T | null
  error: string | null
  isRefreshing: boolean
  lastUpdated: Date | null
  retry: () => void
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: UsePollingOptions = {},
): UsePollingResult<T> {
  const { enabled = true, intervalMs = REFRESH_INTERVAL_MS } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const fetcherRef = useRef(fetcher)
  const requestIdRef = useRef(0)

  useEffect(() => {
    fetcherRef.current = fetcher
  })

  const load = useCallback(async () => {
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    await Promise.resolve()
    if (requestId !== requestIdRef.current) {
      return
    }

    setIsRefreshing(true)
    try {
      const result = await fetcherRef.current()
      if (requestId !== requestIdRef.current) {
        return
      }
      setData(result)
      setError(null)
      setLastUpdated(new Date())
    } catch (requestError) {
      if (requestId !== requestIdRef.current) {
        return
      }
      setError(getErrorMessage(requestError))
    } finally {
      if (requestId === requestIdRef.current) {
        setIsRefreshing(false)
      }
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      return
    }

    void load()
    const intervalId = window.setInterval(() => {
      void load()
    }, intervalMs)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [enabled, intervalMs, load])

  return { data, error, isRefreshing, lastUpdated, retry: load }
}
