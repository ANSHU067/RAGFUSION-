import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import axios from 'axios'
import api, { refreshAccessToken } from '../src/services/api'
import { clearSession, getAuthSessionVersion, subscribeSession } from '../src/services/session'

const ok = (config, data = {}) => ({ config, data, status: 200, headers: {}, statusText: 'OK' })
const fail = (config, status = 401) => Promise.reject(new axios.AxiosError('Rejected', 'ERR_BAD_REQUEST', config, null, { config, status, data: {} }))
const deferred = () => {
  let resolve
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}
const initialAdapter = axios.defaults.adapter
beforeEach(() => {
  clearSession()
  localStorage.setItem('access_token', 'old-access')
  localStorage.setItem('refresh_token', 'old-refresh')
})
afterEach(() => { vi.restoreAllMocks(); axios.defaults.adapter = initialAdapter; clearSession() })

test('concurrent 401s share one refresh and retry once with the rotated token', async () => {
  const gate = deferred()
  const refresh = vi.fn(async (config) => {
    await gate.promise
    return ok(config, { access_token: 'new-access', refresh_token: 'new-refresh' })
  })
  axios.defaults.adapter = refresh
  const requests = vi.fn((config) => config.headers.Authorization === 'Bearer new-access' ? Promise.resolve(ok(config)) : fail(config))
  api.defaults.adapter = requests
  const results = Promise.all(Array.from({ length: 12 }, () => api.get('/chat/sessions')))
  await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(1))
  gate.resolve()
  await results
  expect(requests).toHaveBeenCalledTimes(24)
  expect(refresh).toHaveBeenCalledTimes(1)
  expect(localStorage.getItem('refresh_token')).toBe('new-refresh')
})

test('failed refresh clears the session once and never replays queued requests', async () => {
  const gate = deferred()
  const changed = vi.fn()
  const unsubscribe = subscribeSession(changed)
  axios.defaults.adapter = vi.fn(async (config) => { await gate.promise; return fail(config) })
  api.defaults.adapter = vi.fn((config) => fail(config))
  const results = Promise.allSettled(Array.from({ length: 12 }, () => api.get('/chat/sessions')))
  await vi.waitFor(() => expect(axios.defaults.adapter).toHaveBeenCalledTimes(1))
  gate.resolve()
  expect((await results).every((result) => result.status === 'rejected')).toBe(true)
  expect(api.defaults.adapter).toHaveBeenCalledTimes(12)
  expect(changed).toHaveBeenCalledTimes(1)
  expect(localStorage.getItem('access_token')).toBeNull()
  expect(localStorage.getItem('refresh_token')).toBeNull()
  unsubscribe()
})

test.each(['/auth/login', '/auth/signup', '/auth/refresh', '/auth/me', '/auth/me/?check=1', 'http://127.0.0.1:8000/api/v1/auth/me'])('never refreshes or retries %s', async (url) => {
  axios.defaults.adapter = vi.fn()
  api.defaults.adapter = vi.fn((config) => fail(config))
  await expect(api.get(url)).rejects.toBeDefined()
  expect(api.defaults.adapter).toHaveBeenCalledTimes(1)
  expect(axios.defaults.adapter).not.toHaveBeenCalled()
})

test('/auth/me still receives the bearer token', async () => {
  api.defaults.adapter = vi.fn(async (config) => ok(config, { id: 'user-a' }))
  await api.get('/auth/me')
  expect(api.defaults.adapter.mock.calls[0][0].headers.Authorization).toBe('Bearer old-access')
})

test('a second 401 is terminal', async () => {
  axios.defaults.adapter = vi.fn(async (config) => ok(config, { access_token: 'new-access', refresh_token: 'new-refresh' }))
  api.defaults.adapter = vi.fn((config) => fail(config))
  await expect(api.get('/chat/sessions')).rejects.toBeDefined()
  expect(api.defaults.adapter).toHaveBeenCalledTimes(2)
  expect(axios.defaults.adapter).toHaveBeenCalledTimes(1)
})

test('429 does not start refresh or retry', async () => {
  axios.defaults.adapter = vi.fn()
  api.defaults.adapter = vi.fn((config) => fail(config, 429))
  await expect(api.get('/chat/sessions')).rejects.toBeDefined()
  expect(api.defaults.adapter).toHaveBeenCalledTimes(1)
  expect(axios.defaults.adapter).not.toHaveBeenCalled()
})

test('late refresh failure cannot expire a new account', async () => {
  const gate = deferred()
  axios.defaults.adapter = vi.fn(async (config) => { await gate.promise; return fail(config) })
  const result = refreshAccessToken().catch((error) => error)
  await vi.waitFor(() => expect(axios.defaults.adapter).toHaveBeenCalledTimes(1))
  clearSession()
  const version = getAuthSessionVersion()
  localStorage.setItem('access_token', 'account-b')
  localStorage.setItem('refresh_token', 'refresh-b')
  gate.resolve()
  await result
  expect(getAuthSessionVersion()).toBe(version)
  expect(localStorage.getItem('access_token')).toBe('account-b')
})

test('missing refresh credentials expire once without a network refresh', async () => {
  localStorage.removeItem('refresh_token')
  axios.defaults.adapter = vi.fn()
  api.defaults.adapter = vi.fn((config) => fail(config))
  const version = getAuthSessionVersion()
  await Promise.allSettled(Array.from({ length: 5 }, () => api.get('/chat/sessions')))
  expect(axios.defaults.adapter).not.toHaveBeenCalled()
  expect(getAuthSessionVersion()).toBe(version + 1)
})

test('a caller canceled during refresh is not replayed without AbortSignal.any', async () => {
  // Exercise the compatibility path used by browsers without the native method.
  const nativeAny = AbortSignal.any
  AbortSignal.any = undefined
  try {
    const gate = deferred()
    const controller = new AbortController()
    axios.defaults.adapter = vi.fn(async (config) => {
      await gate.promise
      return ok(config, { access_token: 'new-access', refresh_token: 'new-refresh' })
    })
    api.defaults.adapter = vi.fn((config) => fail(config))
    const result = api.get('/chat/sessions', { signal: controller.signal }).catch((error) => error)
    await vi.waitFor(() => expect(axios.defaults.adapter).toHaveBeenCalledTimes(1))
    controller.abort()
    gate.resolve()
    expect(axios.isCancel(await result)).toBe(true)
    expect(api.defaults.adapter).toHaveBeenCalledTimes(1)
  } finally { AbortSignal.any = nativeAny }
})
