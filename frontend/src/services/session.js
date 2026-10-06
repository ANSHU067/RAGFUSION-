// Shared by auth and HTTP transport to avoid a circular dependency.
import { LEGACY_STORAGE_PREFIX } from './branding'
export const ACCESS_TOKEN_KEY = 'access_token'
export const REFRESH_TOKEN_KEY = 'refresh_token'
let authSessionVersion = 0
let controller = new AbortController()
const listeners = new Set()
export const getAuthSessionVersion = () => authSessionVersion
export const getSessionSignal = () => controller.signal
export const subscribeSession = (listener) => { listeners.add(listener); return () => listeners.delete(listener) }
export const isCurrentSession = (version) => version === authSessionVersion
export function clearSession() {
  authSessionVersion += 1
  controller.abort()
  controller = new AbortController()
  for (const key of Object.keys(localStorage)) {
    if (key.startsWith('ragfusion-') || key.startsWith(LEGACY_STORAGE_PREFIX) || ['access_token', 'refresh_token', 'user'].includes(key)) localStorage.removeItem(key)
  }
  for (const listener of listeners) listener()
  return authSessionVersion
}
// Another tab changing identity invalidates this tab's private tree as well.
window.addEventListener('storage', (event) => {
  if (event.key === 'user') {
    try {
      const previous = JSON.parse(event.oldValue || 'null')
      const next = JSON.parse(event.newValue || 'null')
      if (!previous?.id || previous.id !== next?.id) clearSession()
    } catch { clearSession() }
  } else if (event.key === null || (event.key === ACCESS_TOKEN_KEY && event.newValue === null)) clearSession()
})
