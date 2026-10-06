import axios from 'axios'
import api, { refreshAccessToken } from './api'
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, clearSession, getAuthSessionVersion, isCurrentSession } from './session'
export { clearSession, getAuthSessionVersion } from './session'
async function authenticate(path, payload) {
  const version = clearSession()
  const { data } = await api.post(path, payload, { _sessionVersion: version })
  if (!isCurrentSession(version)) throw new axios.CanceledError()
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token)
  return authApi.currentUser()
}
export const authApi = {
  login: (credentials) => authenticate('/auth/login', credentials),
  signup: (payload) => authenticate('/auth/signup', payload),
  async logout() {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY)
    clearSession()
    if (token) await api.post('/auth/logout', undefined, { headers: { Authorization: `Bearer ${token}` } })
  },
  refresh: refreshAccessToken,
  async updateProfile(payload, config = {}) {
    const version = getAuthSessionVersion()
    const { data } = await api.patch('/auth/me', payload, config)
    if (!isCurrentSession(version)) throw new axios.CanceledError()
    localStorage.setItem('user', JSON.stringify(data))
    return data
  },
  async currentUser(config = {}) {
    const version = getAuthSessionVersion()
    const { data } = await api.get('/auth/me', config)
    if (!isCurrentSession(version)) throw new axios.CanceledError()
    localStorage.setItem('user', JSON.stringify(data))
    return data
  },
}
