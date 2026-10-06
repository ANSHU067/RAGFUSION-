import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import axios from 'axios'
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from '../src/context/AuthContext'
import { ChatProvider } from '../src/context/ChatContext'
import api from '../src/services/api'
import { clearSession } from '../src/services/session'

function ProtectedRoute() {
  const { user, loading } = useAuth()
  if (loading) return <p>Checking session</p>
  if (!user) return <Navigate to="/login" replace />
  return <p>Private dashboard</p>
}
function Tree() {
  return <AuthProvider><ChatProvider><MemoryRouter initialEntries={['/dashboard']}><Routes>
    <Route path="/dashboard" element={<ProtectedRoute />} />
    <Route path="/login" element={<p>Sign in</p>} />
  </Routes></MemoryRouter></ChatProvider></AuthProvider>
}
const adapter = axios.defaults.adapter
beforeEach(() => {
  clearSession()
  localStorage.setItem('access_token', 'expired')
  localStorage.setItem('refresh_token', 'expired-refresh')
})
afterEach(() => { cleanup(); axios.defaults.adapter = adapter; clearSession() })
test('expired bootstrap reaches login without ever requesting chat sessions or refresh', async () => {
  axios.defaults.adapter = vi.fn()
  api.defaults.adapter = vi.fn(async (config) => {
    expect(config.url).toBe('/auth/me')
    throw new axios.AxiosError('Expired', 'ERR_BAD_REQUEST', config, null, { status: 401, config, data: {} })
  })
  render(<Tree />)
  await screen.findByText('Sign in')
  await act(async () => {})
  expect(api.defaults.adapter).toHaveBeenCalledTimes(1)
  expect(axios.defaults.adapter).not.toHaveBeenCalled()
  expect(localStorage.getItem('access_token')).toBeNull()
})
test('runtime refresh failure clears user and routes to login without another history fetch', async () => {
  const urls = []
  api.defaults.adapter = vi.fn(async (config) => {
    urls.push(config.url)
    if (config.url === '/auth/me') return { config, status: 200, data: { id: 'user-a' }, headers: {}, statusText: 'OK' }
    throw new axios.AxiosError('Expired', 'ERR_BAD_REQUEST', config, null, { status: 401, config, data: {} })
  })
  axios.defaults.adapter = vi.fn(async (config) => {
    throw new axios.AxiosError('Expired refresh', 'ERR_BAD_REQUEST', config, null, { status: 401, config, data: {} })
  })
  render(<Tree />)
  await screen.findByText('Sign in')
  await act(async () => {})
  expect(urls).toEqual(['/auth/me', '/chat/sessions'])
  expect(axios.defaults.adapter).toHaveBeenCalledTimes(1)
  expect(localStorage.getItem('access_token')).toBeNull()
})
