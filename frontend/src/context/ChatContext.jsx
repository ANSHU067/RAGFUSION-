import { createContext, useContext, useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { chatApi } from '@/services/chat'
import { useAsyncScope } from '@/hooks/useAsyncScope'
import { useAuth } from './AuthContext'
import { ACCESS_TOKEN_KEY, getApiError, isCanceled } from '@/services/api'
import { getAuthSessionVersion, isCurrentSession } from '@/services/session'

const ChatContext = createContext(null)
const ChatDraftContext = createContext(null)
const emptyConversation = () => ({ id: null, messages: [], source: '', loading: false, sending: false, error: '' })

// The account-keyed provider lives above the router. Route unmounts preserve it.
export function ChatProvider({ children }) {
  const [conversation, setConversation] = useState(emptyConversation)
  const current = useRef(conversation)
  const cache = useRef(new Map())
  const [draft, setDraftState] = useState('')
  const draftRef = useRef('')
  const draftCache = useRef(new Map())
  const setDraft = useCallback((value) => {
    draftRef.current = value
    draftCache.current.set(current.current.id, value)
    setDraftState(value)
  }, [])
  const operation = useRef(null)
  const epoch = useRef(0)
  const [chatHistory, setChatHistory] = useState([])
  const [historyError, setHistoryError] = useState('')
  const begin = useAsyncScope()
  const { user, loading: authLoading } = useAuth()
  const userId = user?.id
  const authenticated = useCallback(() => !authLoading && !!userId && !!localStorage.getItem(ACCESS_TOKEN_KEY), [authLoading, userId])
  const publish = useCallback((value) => {
    current.current = value
    if (value.id && !value.loading && !value.error) cache.current.set(value.id, value)
    setConversation(value)
  }, [])
  const cancelOperation = useCallback(() => {
    ++epoch.current
    operation.current?.controller.abort()
    operation.current = null
  }, [])
  useEffect(() => cancelOperation, [cancelOperation])

  const refreshHistory = useCallback(async () => {
    if (!authenticated()) return
    const task = begin('history')
    if (!task) return
    try {
      const data = await chatApi.listSessions({}, { signal: task.signal })
      if (task.active()) { setChatHistory(data.sessions || []); setHistoryError('') }
    } catch (err) {
      if (task.active() && !isCanceled(err)) setHistoryError(getApiError(err, 'Unable to load chat history.'))
    } finally { task.done() }
  }, [authenticated, begin])
  useEffect(() => { refreshHistory() }, [refreshHistory])

  const startNewChat = useCallback(() => {
    cancelOperation()
    const previous = current.current
    if (previous.id && (previous.sending || previous.loading)) cache.current.delete(previous.id)
    publish(emptyConversation())
    setDraft('')
  }, [cancelOperation, publish, setDraft])
  useEffect(() => {
    window.addEventListener('new-chat', startNewChat)
    return () => window.removeEventListener('new-chat', startNewChat)
  }, [startNewChat])

  const loadChat = useCallback((id, { refresh = false } = {}) => {
    if (!authenticated() || !id) return Promise.resolve(null)
    if (current.current.id === id && (operation.current || (!refresh && !current.current.loading && !current.current.error))) return operation.current?.promise || Promise.resolve(current.current)
    if (current.current.id && (current.current.sending || current.current.loading)) cache.current.delete(current.current.id)
    cancelOperation()
    const saved = refresh ? null : cache.current.get(id)
    if (saved) { publish(saved); setDraft(draftCache.current.get(id) || ''); return Promise.resolve(saved) }
    const controller = new AbortController()
    const version = getAuthSessionVersion()
    const requestEpoch = epoch.current
    const active = () => !controller.signal.aborted && requestEpoch === epoch.current && isCurrentSession(version)
    publish({ ...emptyConversation(), id, loading: true })
    setDraft(draftCache.current.get(id) || '')
    const promise = chatApi.getSession(id, { signal: controller.signal }).then((data) => {
      if (active()) publish({ ...emptyConversation(), ...data.session, messages: data.messages || [] })
      return data
    }).catch((err) => {
      if (active() && !isCanceled(err)) publish({ ...current.current, error: getApiError(err, 'Unable to load this conversation.') })
      return null
    }).finally(() => {
      if (active()) { operation.current = null; publish({ ...current.current, loading: false }) }
    })
    operation.current = { controller, promise }
    return promise
  }, [authenticated, cancelOperation, publish, setDraft])

  const sendMessage = useCallback(async (text) => {
    if (!authenticated() || operation.current || !text.trim() || current.current.loading) return null
    const controller = new AbortController()
    const version = getAuthSessionVersion()
    const requestEpoch = ++epoch.current
    const active = () => !controller.signal.aborted && requestEpoch === epoch.current && isCurrentSession(version)
    const previous = current.current
    const previousDraft = draftRef.current
    const optimistic = { id: crypto.randomUUID(), role: 'user', content: text.trim(), created_at: new Date().toISOString() }
    setDraft('')
    publish({ ...previous, messages: [...previous.messages, optimistic], sending: true, error: '' })
    const payload = { message: text.trim(), chat_session_id: previous.id, include_sources: true }
    if (previous.source) {
      const [kind, id] = previous.source.split(':')
      payload.source_ids = { [kind]: [id] }
    } else {
      // An explicit null is the contract for “all indexed sources”. It keeps
      // source selection unambiguous for API clients and avoids accidentally
      // reusing a stale single-source filter.
      payload.source_ids = null
    }
    operation.current = { controller }
    try {
      const data = await chatApi.sendMessage(payload, { signal: controller.signal })
      if (!active()) return null
      publish({ ...current.current, id: data.session_id, messages: [...current.current.messages, { ...data.message, citations: data.sources || data.message.citations }] })
      void refreshHistory()
      return data
    } catch (err) {
      if (active() && !isCanceled(err)) {
        publish({ ...previous, error: getApiError(err, 'Unable to send your message. Your conversation has been preserved.') })
        setDraft(previousDraft)
      }
      return null
    } finally {
      if (active()) { operation.current = null; publish({ ...current.current, sending: false }) }
    }
  }, [authenticated, publish, refreshHistory, setDraft])
  const setSource = useCallback((source) => {
    if (!operation.current) publish({ ...current.current, source })
  }, [publish])
  const clearError = useCallback(() => { publish({ ...current.current, error: '' }); setHistoryError('') }, [publish])
  // Draft changes notify only the composer, not conversation/history consumers.
  const chatValue = useMemo(() => ({ ...conversation, currentChat: conversation.id ? conversation : null, currentSessionId: conversation.id, chatHistory, error: conversation.error || historyError, refreshHistory, loadChat, sendMessage, startNewChat, setDraft, setSource, clearError }), [conversation, chatHistory, historyError, refreshHistory, loadChat, sendMessage, startNewChat, setDraft, setSource, clearError])
  const draftValue = useMemo(() => ({ draft, setDraft }), [draft, setDraft])
  return <ChatContext.Provider value={chatValue}><ChatDraftContext.Provider value={draftValue}>{children}</ChatDraftContext.Provider></ChatContext.Provider>
}
export const useChat = () => useContext(ChatContext)
export const useChatDraft = () => useContext(ChatDraftContext)
