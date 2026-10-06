import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { ChatProvider, useChat } from '../src/context/ChatContext'
import { chatApi } from '../src/services/chat'
import { clearSession } from '../src/services/session'

const auth = vi.hoisted(() => ({ user: null, loading: false }))
vi.mock('../src/context/AuthContext', () => ({ useAuth: () => auth }))
vi.mock('../src/services/chat', () => ({ chatApi: { listSessions: vi.fn() } }))
function Consumer() {
  const { chatHistory, error } = useChat()
  return <div><span>{chatHistory.length} sessions</span><span>{error}</span></div>
}
function Tree() { return <ChatProvider><Consumer /></ChatProvider> }
beforeEach(() => {
  clearSession()
  auth.user = null
  auth.loading = false
  chatApi.listSessions.mockReset().mockResolvedValue({ sessions: [] })
})
afterEach(cleanup)

test.each([
  { user: null, loading: false, token: 'token' },
  { user: { id: 'a' }, loading: true, token: 'token' },
  { user: { id: 'a' }, loading: false, token: null },
])('does not load history without confirmed authentication (%j)', async ({ user, loading, token }) => {
  auth.user = user; auth.loading = loading
  if (token) localStorage.setItem('access_token', token)
  render(<Tree />)
  await act(async () => {})
  expect(chatApi.listSessions).not.toHaveBeenCalled()
})

test('auth bootstrap loads once, and equivalent user objects or errors do not retrigger it', async () => {
  localStorage.setItem('access_token', 'token')
  auth.loading = true
  const view = render(<Tree />)
  expect(chatApi.listSessions).not.toHaveBeenCalled()
  chatApi.listSessions.mockRejectedValue({ response: { status: 429 } })
  auth.loading = false; auth.user = { id: 'a' }
  view.rerender(<Tree />)
  await screen.findByText('Unable to load chat history.')
  for (let count = 0; count < 5; count++) {
    auth.user = { id: 'a' }
    view.rerender(<Tree />)
  }
  expect(chatApi.listSessions).toHaveBeenCalledTimes(1)
})

test('cancellations are consumed without an error or retry', async () => {
  localStorage.setItem('access_token', 'token'); auth.user = { id: 'a' }
  chatApi.listSessions.mockRejectedValue({ name: 'CanceledError' })
  const view = render(<Tree />)
  await act(async () => {})
  view.rerender(<Tree />)
  expect(chatApi.listSessions).toHaveBeenCalledTimes(1)
  expect(screen.queryByText('Unable to load chat history.')).toBeNull()
})

test('logout remount cannot restart history or accept the previous response', async () => {
  localStorage.setItem('access_token', 'token'); auth.user = { id: 'a' }
  let resolve
  chatApi.listSessions.mockReturnValue(new Promise((done) => { resolve = done }))
  const view = render(<Tree />)
  await waitFor(() => expect(chatApi.listSessions).toHaveBeenCalledTimes(1))
  const signal = chatApi.listSessions.mock.calls[0][1].signal
  clearSession(); auth.user = null
  view.unmount()
  render(<Tree />)
  await act(async () => resolve({ sessions: [{ id: 'private-history' }] }))
  expect(signal.aborted).toBe(true)
  expect(screen.getByText('0 sessions')).toBeDefined()
  expect(chatApi.listSessions).toHaveBeenCalledTimes(1)
})
