import { createContext, useContext, useState, useEffect, useCallback, useRef, useSyncExternalStore } from 'react'
import { authApi } from '@/services/auth'
import { getApiError, isCanceled } from '@/services/api'
import { getAuthSessionVersion, isCurrentSession, subscribeSession } from '@/services/session'
const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const epoch = useRef(0)
  const sessionVersion = useSyncExternalStore(subscribeSession, getAuthSessionVersion)
  useEffect(() => {
    const unsubscribe = subscribeSession(() => { epoch.current += 1; setUser(null); setLoading(false); setError(null) })
    const controller = new AbortController()
    const request = ++epoch.current
    if (localStorage.getItem('access_token')) {
      authApi.currentUser({ signal: controller.signal }).then((data) => {
        if (epoch.current === request && !controller.signal.aborted) setUser(data)
      }).catch(() => {}).finally(() => {
        if (epoch.current === request && !controller.signal.aborted) setLoading(false)
      })
    } else setLoading(false)
    return () => { unsubscribe(); epoch.current += 1; controller.abort() }
  }, [])
  const authenticate = useCallback(async (action, payload) => {
    const pending = action(payload) // clears the previous identity synchronously
    const request = ++epoch.current
    setError(null); setLoading(true)
    try {
      const data = await pending
      if (request !== epoch.current) return { success: false }
      setUser(data)
      return { success: true, user: data }
    } catch (err) {
      const message = getApiError(err, 'Authentication failed.')
      if (request === epoch.current && !isCanceled(err)) setError(message)
      return { success: false, error: message }
    } finally { if (request === epoch.current) setLoading(false) }
  }, [])
  const login = useCallback((payload) => authenticate(authApi.login, payload), [authenticate])
  const register = useCallback((payload) => authenticate(authApi.signup, payload), [authenticate])
  const logout = useCallback(async () => { try { await authApi.logout() } catch { /* Local credentials are already removed. */ } }, [])
  const updateProfile = useCallback(async (payload, config) => {
    const version = getAuthSessionVersion()
    const updated = await authApi.updateProfile(payload, config)
    if (isCurrentSession(version)) setUser(updated)
    return updated
  }, [])
  return <AuthContext.Provider value={{ user, loading, error, login, register, logout, updateProfile, sessionVersion, isAuthenticated: !!user, clearError: () => setError(null) }}>{children}</AuthContext.Provider>
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('AuthProvider is required'); return value }
