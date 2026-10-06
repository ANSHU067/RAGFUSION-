import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { ChatProvider } from '../src/context/ChatContext'
import ChatPage from '../src/pages/readers/ChatPage'
import DashboardPage from '../src/pages/dashboard/DashboardPage'
import WebsiteReaderPage from '../src/pages/readers/WebsiteReaderPage'
import { Navbar } from '../src/components/layout/Navbar'
import { chatApi } from '../src/services/chat'
import { websiteApi } from '../src/services/website'
import { dashboardApi } from '../src/services/dashboard'
import { clearSession } from '../src/services/session'

vi.mock('../src/context/AuthContext', () => ({ useAuth: () => ({ user: { id: 'owner', display_name: 'Ada Stone' }, loading: false }) }))
vi.mock('../src/context/ThemeContext', () => ({ useTheme: () => ({ theme: 'light', resolvedTheme: 'light' }) }))
vi.mock('../src/services/chat', () => ({ chatApi: { listSessions: vi.fn(), getSession: vi.fn(), sendMessage: vi.fn(), listSources: vi.fn() } }))
vi.mock('../src/services/website', () => ({ websiteApi: { list: vi.fn(), create: vi.fn(), process: vi.fn(), remove: vi.fn() } }))
vi.mock('../src/services/dashboard', () => ({ dashboardApi: { overview: vi.fn() } }))
vi.mock('../src/components/chat', () => ({
  ChatWindow: ({ children }) => <div>{children}</div>,
  ChatBubble: ({ message }) => <div><p>{message.content}</p><time dateTime={message.created_at} /></div>,
  TypingIndicator: () => <p>Generating</p>,
  PromptInput: ({ value, onChange, onSubmit, disabled }) => <form onSubmit={(event) => { event.preventDefault(); onSubmit(value) }}><input aria-label="Message" value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} /><button disabled={disabled}>Send</button></form>,
}))
const deferred = () => { let resolve; const promise = new Promise((done) => { resolve = done }); return { promise, resolve } }
const history = (id, content) => ({ session: { id }, messages: [{ id: id + '-message', role: 'assistant', content, created_at: '2026-10-06T00:00:00Z' }] })
function Workspace({ initial = '/chat/a' }) {
  return <MemoryRouter initialEntries={[initial]}><ChatProvider><nav><Link to="/documents">Documents</Link><Link to="/chat">Back to chat</Link><Link to="/chat/b">Other session</Link></nav><Routes><Route path="/documents" element={<h1>Documents page</h1>} /><Route path="/chat" element={<ChatPage />} /><Route path="/chat/:sessionId" element={<ChatPage />} /></Routes></ChatProvider></MemoryRouter>
}
beforeEach(() => {
  clearSession(); localStorage.setItem('access_token', 'valid')
  vi.resetAllMocks()
  chatApi.listSessions.mockResolvedValue({ sessions: [] })
  chatApi.listSources.mockResolvedValue({ sources: [{ id: 'site', type: 'website', title: 'Public article' }] })
  chatApi.getSession.mockImplementation(async (id) => history(id, 'History ' + id))
  websiteApi.list.mockResolvedValue({ items: [], total: 0 })
})
afterEach(cleanup)

test('navigation preserves conversation and unsent draft without another history fetch', async () => {
  render(<Workspace />)
  await screen.findByText('History a')
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'My unfinished question' } })
  fireEvent.click(screen.getByText('Documents'))
  await screen.findByText('Documents page')
  fireEvent.click(screen.getByText('Back to chat'))
  await screen.findByText('History a')
  expect(screen.getByLabelText('Message').value).toBe('My unfinished question')
  expect(chatApi.getSession).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'New chat' }))
  expect(screen.queryByText('History a')).toBeNull()
  expect(screen.getByLabelText('Message').value).toBe('')
})

test('navigation during a send retains the completed answer and blocks duplicate sends', async () => {
  const request = deferred()
  chatApi.sendMessage.mockReturnValue(request.promise)
  render(<Workspace />)
  await screen.findByText('History a')
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Question' } })
  fireEvent.click(screen.getByText('Send')); fireEvent.click(screen.getByText('Send'))
  expect(chatApi.sendMessage).toHaveBeenCalledTimes(1)
  expect(chatApi.sendMessage.mock.calls[0][0].chat_session_id).toBe('a')
  const optimisticDate = screen.getByText('Question').parentElement.querySelector('time').dateTime
  expect(Math.abs(Date.now() - Date.parse(optimisticDate))).toBeLessThan(2000)
  const signal = chatApi.sendMessage.mock.calls[0][1].signal
  fireEvent.click(screen.getByText('Documents'))
  expect(signal.aborted).toBe(false)
  await act(async () => request.resolve({ session_id: 'a', message: { id: 'answer', role: 'assistant', content: 'Persisted answer' }, sources: [] }))
  fireEvent.click(screen.getByText('Back to chat'))
  await screen.findByText('Persisted answer')
  expect(screen.getByText('Question')).toBeDefined()
  expect(chatApi.getSession).toHaveBeenCalledTimes(1)
})

test('changing sessions aborts and ignores out-of-order history responses', async () => {
  const request = deferred()
  chatApi.getSession.mockImplementation((id) => id === 'a' ? request.promise : Promise.resolve(history(id, 'History b')))
  render(<Workspace />)
  await waitFor(() => expect(chatApi.getSession).toHaveBeenCalledTimes(1))
  const signal = chatApi.getSession.mock.calls[0][1].signal
  fireEvent.click(screen.getByText('Other session'))
  await screen.findByText('History b')
  expect(signal.aborted).toBe(true)
  await act(async () => request.resolve(history('a', 'Stale private history')))
  expect(screen.queryByText('Stale private history')).toBeNull()
  fireEvent.click(screen.getByText('Documents')); fireEvent.click(screen.getByText('Back to chat'))
  await screen.findByText('History b')
  expect(chatApi.getSession).toHaveBeenCalledTimes(2)
})

test('New chat cancels an in-flight answer and a late result cannot recreate it', async () => {
  const request = deferred()
  chatApi.sendMessage.mockReturnValue(request.promise)
  render(<Workspace initial="/chat" />)
  await screen.findByRole('option', { name: 'website · Public article' })
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Old question' } })
  fireEvent.click(screen.getByText('Send'))
  const signal = chatApi.sendMessage.mock.calls[0][1].signal
  fireEvent.click(screen.getByRole('button', { name: 'New chat' }))
  await act(async () => request.resolve({ session_id: 'old', message: { id: 'old-answer', content: 'Late answer' } }))
  expect(signal.aborted).toBe(true)
  expect(screen.queryByText('Late answer')).toBeNull()
  expect(screen.queryByText('Old question')).toBeNull()
})

test('a website deep link selects the real source and sends its ID to the API', async () => {
  chatApi.sendMessage.mockResolvedValue({ session_id: 'new', message: { id: 'answer', content: 'Website answer' } })
  render(<Workspace initial="/chat?source=website:site" />)
  await waitFor(() => expect(screen.getByLabelText('Source').value).toBe('website:site'))
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Summarize the page' } })
  fireEvent.click(screen.getByText('Send'))
  await screen.findByText('Website answer')
  expect(chatApi.sendMessage.mock.calls[0][0].source_ids).toEqual({ website: ['site'] })
})

test('dashboard displays only server metrics and links directly to recent sessions', async () => {
  dashboardApi.overview.mockResolvedValue({ stats: { documents: 12, youtube: 3, websites: 8, conversations: 5 }, recent_sessions: [{ id: 'recent', title: 'Research notes', updated_at: '2026-10-06T00:00:00Z', message_count: 9, token_count: 42 }] })
  render(<MemoryRouter><DashboardPage /></MemoryRouter>)
  await screen.findByText('12')
  expect(screen.getByText('8')).toBeDefined()
  expect(screen.getByText('9 messages')).toBeDefined()
  expect(screen.getByText('42 recorded tokens')).toBeDefined()
  expect(screen.getByRole('link', { name: 'Resume Research notes' }).getAttribute('href')).toBe('/chat/recent')
  expect(screen.getByRole('link', { name: /Scrape website/ }).getAttribute('href')).toBe('/website/reader')
})

test('website form uses live create/process APIs and exposes the ready source chat link', async () => {
  const request = deferred()
  const item = { id: 'site', url: 'https://example.com/article', status: 'pending' }
  websiteApi.create.mockResolvedValue(item)
  websiteApi.process.mockReturnValue(request.promise)
  render(<MemoryRouter><WebsiteReaderPage /></MemoryRouter>)
  await screen.findByText(/Add your first page/)
  fireEvent.change(screen.getByLabelText('Page URL'), { target: { value: item.url } })
  fireEvent.click(screen.getByRole('button', { name: 'Scrape website' }))
  await waitFor(() => expect(websiteApi.process).toHaveBeenCalledTimes(1))
  expect(websiteApi.create.mock.calls[0][0]).toBe(item.url)
  expect(screen.queryByRole('link', { name: 'Chat with website' })).toBeNull()
  await act(async () => request.resolve({ ...item, title: 'Public article', status: 'ready', metadata: { total_chunks: 4 } }))
  expect(screen.getByRole('link', { name: 'Chat with website' }).getAttribute('href')).toBe('/chat?source=website:site')
  expect(screen.getByText('ready · 4 chunks indexed')).toBeDefined()
  expect(screen.getByRole('button', { name: 'Remove Public article' })).toBeDefined()
})

test('navbar keeps right actions in their own nonshrinking, auto-margin flex group', () => {
  render(<MemoryRouter initialEntries={['/website/reader']}><Navbar /></MemoryRouter>)
  expect(screen.getByText('Website')).toBeDefined()
  const theme = screen.getByRole('button', { name: 'Toggle theme' })
  const profile = screen.getByRole('button', { name: 'User menu' })
  const actions = theme.parentElement
  expect(actions.contains(profile)).toBe(true)
  expect(actions.className).toContain('ml-auto')
  expect(actions.className).toContain('shrink-0')
  expect(actions.contains(screen.getByRole('button', { name: 'Open menu' }))).toBe(false)
})
