import { useCallback, useEffect, useRef } from 'react'
import { getAuthSessionVersion, isCurrentSession } from '@/services/session'
// Per-mount cancellation and synchronous action locks. A completed request may
// write only to the mount and authentication session that started it.
export function useAsyncScope() {
  const scope = useRef(null)
  useEffect(() => {
    const value = { controller: new AbortController(), version: getAuthSessionVersion(), locks: new Set() }
    scope.current = value
    return () => { value.controller.abort() }
  }, [])
  return useCallback((key) => {
    const value = scope.current
    if (!value || value.controller.signal.aborted || !isCurrentSession(value.version) || value.locks.has(key)) return null
    value.locks.add(key)
    return {
      signal: value.controller.signal,
      active: () => !value.controller.signal.aborted && isCurrentSession(value.version),
      done: () => value.locks.delete(key),
    }
  }, [])
}
