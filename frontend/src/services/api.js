import axios from 'axios'
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, clearSession, getAuthSessionVersion, getSessionSignal, isCurrentSession } from './session'
export { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from './session'
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const timeout = Number(import.meta.env.VITE_API_TIMEOUT_MS || 300000)
const api = axios.create({ baseURL, timeout, headers: { Accept: 'application/json' } })
const AUTH_ENDPOINTS = ['/auth/login', '/auth/signup', '/auth/refresh', '/auth/me', '/auth/logout']
const requestPath = (url = '') => new URL(url, 'http://localhost').pathname.replace(/\/+$/, '')
const isEndpoint = (url, endpoint) => requestPath(url).endsWith(endpoint)
const isAuthRequest = (url) => AUTH_ENDPOINTS.some((endpoint) => isEndpoint(url, endpoint))
const combineSignals = (config) => {
  const requestSignal = config._callerSignal
  const sessionSignal = getSessionSignal()
  if (!requestSignal) return sessionSignal
  if (typeof AbortSignal.any === 'function') return AbortSignal.any([requestSignal, sessionSignal])
  const controller = new AbortController()
  const abort = () => controller.abort()
  requestSignal.addEventListener('abort', abort, { once: true })
  sessionSignal.addEventListener('abort', abort, { once: true })
  config._disposeSignals = () => {
    requestSignal.removeEventListener('abort', abort)
    sessionSignal.removeEventListener('abort', abort)
  }
  if (requestSignal.aborted || sessionSignal.aborted) controller.abort()
  return controller.signal
}
const canceled = () => new axios.CanceledError('Authentication session changed')
const expireSession = (version) => {
  // clearSession advances the version before notifying AuthProvider. Only the
  // first failure in this session clears it; old failures cannot log out a new user.
  if (isCurrentSession(version)) clearSession()
}
api.interceptors.request.use((config) => {
  if (config._sessionVersion !== undefined && !isCurrentSession(config._sessionVersion)) throw canceled()
  if (!Object.prototype.hasOwnProperty.call(config, '_callerSignal')) config._callerSignal = config.signal
  config._sessionVersion ??= getAuthSessionVersion()
  config.signal = combineSignals(config)
  if (!isAuthRequest(config.url) || isEndpoint(config.url, '/auth/me')) {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY)
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
let refreshFlight = null
export function refreshAccessToken() {
  const version = getAuthSessionVersion()
  if (refreshFlight?.version === version) return refreshFlight.promise
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  const flight = { version }
  flight.promise = Promise.resolve().then(async () => {
    try {
      if (!isCurrentSession(version)) throw canceled()
      if (!refreshToken) throw new Error('Your session has expired. Please sign in again.')
      const { data } = await axios.post('/auth/refresh', { refresh_token: refreshToken }, { baseURL, timeout, signal: getSessionSignal() })
      if (!isCurrentSession(version)) throw canceled()
      if (!data.access_token || !data.refresh_token) throw new Error('Invalid authentication response.')
      localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token)
      return data
    } catch (error) {
      if (!isCanceled(error)) expireSession(version)
      throw error
    }
  }).finally(() => { if (refreshFlight === flight) refreshFlight = null })
  refreshFlight = flight
  return flight.promise
}
api.interceptors.response.use((response) => {
  response.config._disposeSignals?.()
  if (!isCurrentSession(response.config._sessionVersion)) throw canceled()
  return response
}, async (error) => {
  const request = error.config
  request?._disposeSignals?.()
  if (request && !isCurrentSession(request._sessionVersion)) throw canceled()
  if (!request || isCanceled(error) || error.response?.status !== 401) throw error
  if (isAuthRequest(request.url)) {
    if (isEndpoint(request.url, '/auth/me') || isEndpoint(request.url, '/auth/refresh')) expireSession(request._sessionVersion)
    throw error
  }
  if (request._retry) { expireSession(request._sessionVersion); throw error }
  if (request.signal?.aborted) throw canceled()
  request._retry = true
  // A delayed 401 may belong to the token already rotated by another request.
  const currentToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (!currentToken || !request.headers.Authorization || request.headers.Authorization === `Bearer ${currentToken}`) await refreshAccessToken()
  if (!isCurrentSession(request._sessionVersion) || request.signal?.aborted || request._callerSignal?.aborted) throw canceled()
  return api(request)
})
export const isCanceled = (error) => axios.isCancel(error) || error?.name === 'AbortError' || error?.name === 'CanceledError'
export function getApiError(error, fallback = 'Something went wrong. Please try again.') {
  const body = error?.response?.data
  const validation = body?.error?.details?.errors
  if (Array.isArray(validation)) {
    const messages = validation.map((item) => item?.message).filter((item) => typeof item === 'string' && item)
    if (messages.length) return messages.join(', ')
  }
  if (typeof body?.error?.message === 'string') return body.error.message
  const detail = body?.detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg || item?.message).filter((item) => typeof item === 'string')
    if (messages.length) return messages.join(', ')
  }
  if (typeof detail === 'string') return detail
  if (error?.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
  if (typeof body?.message === 'string') return body.message
  return fallback
}
export default api
