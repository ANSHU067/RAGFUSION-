import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { formatMessageTimestamp, parseTimestamp } from '../src/lib/dates'
import { AuthProvider, useAuth } from '../src/context/AuthContext'
import { Navbar } from '../src/components/layout/Navbar'
import ProfilePage from '../src/pages/profile/ProfilePage'
import HistoryPage from '../src/pages/history/HistoryPage'
import { authApi } from '../src/services/auth'
import { chatApi } from '../src/services/chat'
import api from '../src/services/api'
import { clearSession, getAuthSessionVersion } from '../src/services/session'

vi.mock('../src/context/ThemeContext', () => ({ useTheme: () => ({ theme: 'light', resolvedTheme: 'light' }) }))
vi.mock('../src/services/auth', () => ({ authApi: { currentUser: vi.fn(), updateProfile: vi.fn() } }))
const originalAdapter = api.defaults.adapter
const owner = { id: 'owner', email: 'owner@example.invalid', display_name: 'Before Name', avatar_color: 'slate' }
const ok = (config, data) => ({ config, data, status: 200, statusText: 'OK', headers: {} })
beforeEach(() => {
  clearSession(); localStorage.setItem('access_token', 'valid'); localStorage.setItem('user', JSON.stringify(owner))
  vi.resetAllMocks(); authApi.currentUser.mockResolvedValue(owner)
})
afterEach(() => { cleanup(); api.defaults.adapter = originalAdapter; vi.useRealTimers() })

test.each([undefined, null, '', 'not-a-date', NaN, Infinity, {}, '2026-99-99T00:00:00Z', '2026-02-30T11:00:00Z'])(
  'invalid timestamp %j has a graceful label', (input) => {
    const result = formatMessageTimestamp(input)
    expect(result.label).toBe('Just now')
    expect(result.dateTime).toBeUndefined()
  },
)
test('today uses local time; older messages use local date and time', () => {
  const now = new Date(2026, 9, 6, 12)
  expect(formatMessageTimestamp(new Date(2026, 9, 6, 11, 25).toISOString(), now, 'en-US').label).toBe('11:25 AM')
  expect(formatMessageTimestamp(new Date(2026, 9, 5, 14, 30).toISOString(), now, 'en-US').label).toBe('Oct 5, 2:30 PM')
  expect(parseTimestamp('2026-10-05T14:30:00').toISOString()).toBe('2026-10-05T14:30:00.000Z')
  expect(parseTimestamp('2026-10-05T14:30:00+05:30').toISOString()).toBe('2026-10-05T09:00:00.000Z')
})

test('profile saves through the API and updates header initials without a session reset', async () => {
  authApi.updateProfile.mockResolvedValue({ ...owner, display_name: 'Ada Stone', bio: 'Researcher', workspace: 'Ocean', avatar_color: 'indigo' })
  render(<MemoryRouter initialEntries={['/profile']}><AuthProvider><Navbar /><ProfilePage /></AuthProvider></MemoryRouter>)
  await screen.findByLabelText('Display name')
  const version = getAuthSessionVersion()
  fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'Ada Stone' } })
  fireEvent.change(screen.getByLabelText('Bio'), { target: { value: 'Researcher' } })
  fireEvent.change(screen.getByLabelText('Workspace label'), { target: { value: 'Ocean' } })
  fireEvent.change(screen.getByLabelText('Avatar color'), { target: { value: 'indigo' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'User menu' }).textContent).toBe('AS'))
  expect(authApi.updateProfile.mock.calls[0][0]).toEqual({ display_name: 'Ada Stone', bio: 'Researcher', workspace: 'Ocean', avatar_color: 'indigo' })
  expect(getAuthSessionVersion()).toBe(version)
  expect(localStorage.getItem('access_token')).toBe('valid')
})

function Identity() { const { user } = useAuth(); return <p>{user?.display_name || 'Signed out'}</p> }
test('late profile responses cannot restore a logged-out account', async () => {
  let resolve
  authApi.updateProfile.mockReturnValue(new Promise((done) => { resolve = done }))
  render(<AuthProvider><ProfilePage /><Identity /></AuthProvider>)
  await screen.findByLabelText('Display name')
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
  const signal = authApi.updateProfile.mock.calls[0][1].signal
  await act(async () => clearSession())
  await act(async () => resolve({ ...owner, display_name: 'Leaked old identity' }))
  expect(signal.aborted).toBe(true)
  expect(screen.getByText('Signed out')).toBeDefined()
  expect(screen.queryByText('Leaked old identity')).toBeNull()
})

test('same-account cross-tab profile edits preserve sessions, account changes clear all caches', () => {
  localStorage.setItem('ragfusion-current-chat', 'private')
  localStorage.setItem('docpro-uploads', 'legacy-private')
  const version = getAuthSessionVersion()
  window.dispatchEvent(new StorageEvent('storage', { key: 'user', oldValue: JSON.stringify(owner), newValue: JSON.stringify({ ...owner, display_name: 'New name' }) }))
  expect(getAuthSessionVersion()).toBe(version)
  window.dispatchEvent(new StorageEvent('storage', { key: 'user', oldValue: JSON.stringify(owner), newValue: JSON.stringify({ id: 'other' }) }))
  expect(getAuthSessionVersion()).toBe(version + 1)
  expect(localStorage.getItem('ragfusion-current-chat')).toBeNull()
  expect(localStorage.getItem('docpro-uploads')).toBeNull()
})

test('history loads every message page with the same abort signal', async () => {
  api.defaults.adapter = vi.fn(async (config) => {
    const offset = config.params.offset
    return ok(config, { session: { id: 'long', message_count: 205 }, messages: Array.from({ length: Math.min(100, 205 - offset) }, (_, index) => ({ id: String(offset + index), content: 'Turn ' + (offset + index) })) })
  })
  const controller = new AbortController()
  const result = await chatApi.getSession('long', { signal: controller.signal })
  expect(result.messages).toHaveLength(205)
  expect(result.messages[204].content).toBe('Turn 204')
  expect(api.defaults.adapter.mock.calls.map(([config]) => config.params.offset)).toEqual([0, 100, 200])
  expect(api.defaults.adapter.mock.calls.every(([config]) => config._callerSignal === controller.signal)).toBe(true)
})

test('history rows link to resumable session URLs and retain data after rename', async () => {
  api.defaults.adapter = vi.fn(async (config) => {
    if (config.method === 'patch') return ok(config, { id: 'session', title: 'Updated title' })
    return ok(config, { sessions: [{ id: 'session', title: 'Old title', created_at: '2026-10-06T00:00:00Z', message_count: 3 }], total_pages: 1 })
  })
  render(<MemoryRouter><HistoryPage /></MemoryRouter>)
  await screen.findAllByRole('link', { name: 'Old title' })
  expect(screen.getAllByRole('link', { name: 'Old title' })[0].getAttribute('href')).toBe('/chat/session')
  fireEvent.click(screen.getByRole('button', { name: 'Rename Old title' }))
  fireEvent.change(screen.getByLabelText('Session title'), { target: { value: 'Updated title' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await screen.findAllByRole('link', { name: 'Updated title' })
  expect(screen.queryByText(/Invalid Date|NaN/)).toBeNull()
})
