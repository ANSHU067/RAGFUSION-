import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ChatWindow, ChatBubble, PromptInput, TypingIndicator } from '@/components/chat'
import { chatApi } from '@/services/chat'
import { getApiError, isCanceled } from '@/services/api'
import { Button } from '@/components/ui/button'
import { useChat, useChatDraft } from '@/context/ChatContext'

const quickPrompts = [
  'Summarize my indexed sources',
  'What are the key themes?',
  'Find important action items',
]
const layoutWidthClass = 'mx-auto w-full max-w-3xl px-4'

function ChatComposer(props) {
  const { draft, setDraft } = useChatDraft()
  return <PromptInput {...props} value={draft} onChange={setDraft} />
}

export default function ChatPage() {
  const chat = useChat()
  const { loadChat, startNewChat, setSource } = chat
  const [params] = useSearchParams()
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const addressedSession = sessionId || params.get('session')
  const requestedSource = params.get('source')
  const handledNew = useRef(null)
  const [sources, setSources] = useState([])
  const [sourceError, setSourceError] = useState('')
  useEffect(() => {
    if (location.pathname === '/chat/new') {
      if (handledNew.current !== location.key) { handledNew.current = location.key; startNewChat() }
      navigate('/chat', { replace: true })
    } else if (addressedSession) void loadChat(addressedSession, { refresh: Boolean(location.state?.refreshChat) })
  }, [addressedSession, loadChat, location.key, location.pathname, location.state?.refreshChat, navigate, startNewChat])
  useEffect(() => {
    const controller = new AbortController()
    chatApi.listSources({ signal: controller.signal }).then((data) => {
      if (controller.signal.aborted) return
      setSources(data.sources)
      if (requestedSource && data.sources.some((source) => source.type + ':' + source.id === requestedSource)) setSource(requestedSource)
    }).catch((err) => {
      if (!controller.signal.aborted && !isCanceled(err)) setSourceError(getApiError(err, 'Unable to load indexed sources.'))
    })
    return () => controller.abort()
  }, [requestedSource, setSource])
  const newChat = useCallback(() => { startNewChat(); navigate('/chat', { replace: true }) }, [startNewChat, navigate])
  const copyMessage = useCallback(async (content) => {
    try { await navigator.clipboard.writeText(content) } catch { /* Clipboard permission can be denied. */ }
  }, [])
  const showEmptyHero = !chat.loading && chat.messages.length === 0 && !chat.error
  const promptInput = <ChatComposer
    onSubmit={chat.sendMessage}
    disabled={chat.loading || chat.sending || !!chat.error}
    autoFocus={showEmptyHero}
  />

  return <div className="mx-auto flex h-[calc(100dvh-6rem)] w-full max-w-5xl flex-col gap-4">
    <header className="flex items-center justify-between gap-3 px-1">
      <div className="min-w-0"><h1 className="truncate text-lg font-semibold">Your workspace chat</h1><p className="hidden text-xs text-muted-foreground sm:block">Answers grounded in your indexed sources.</p></div>
      <Button variant="outline" size="sm" className="rounded-full" onClick={newChat}>New chat</Button>
    </header>
    <div className="flex items-center justify-center px-1">
      <label htmlFor="chat-source" className="sr-only">Source</label>
      <select id="chat-source" value={chat.source} onChange={(event) => setSource(event.target.value)} disabled={chat.loading || chat.sending} className="max-w-full rounded-full border border-border/60 bg-transparent px-3 py-1.5 text-xs text-muted-foreground outline-none transition-colors hover:border-border focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option value="">All my indexed sources</option>
        {sources.map((source) => <option key={source.type + ':' + source.id} value={source.type + ':' + source.id}>{source.type} · {source.title}</option>)}
        {chat.source && !sources.some((source) => source.type + ':' + source.id === chat.source) && <option value={chat.source}>Selected source unavailable</option>}
      </select>
    </div>
    {sourceError && <p role="alert" className="text-sm text-destructive">{sourceError}</p>}
    {chat.error && <div role="alert" className="rounded-lg border border-destructive/30 p-3 text-sm">{chat.error}<Button variant="link" onClick={chat.clearError}>Dismiss</Button></div>}
    <main className="flex min-h-0 flex-1 flex-col">
      {showEmptyHero ? <section className="flex flex-1 flex-col items-center justify-center px-2 pb-8 pt-4" aria-labelledby="chat-empty-title">
        <div className={`${layoutWidthClass} text-center`}>
          <h2 id="chat-empty-title" className="text-3xl font-semibold tracking-tight sm:text-4xl">Where should we begin?</h2>
          <p className="mx-auto mt-3 max-w-lg text-sm text-muted-foreground">Ask anything about your documents, videos, and websites.</p>
          <div className="mt-8 rounded-[1.75rem] border border-border/80 bg-background/80 p-2 shadow-lg backdrop-blur-md">{promptInput}</div>
          <div className="mt-4 flex flex-wrap justify-center gap-2" aria-label="Suggested prompts">
            {quickPrompts.map((prompt) => <button key={prompt} type="button" className="rounded-full border border-border/70 bg-muted/30 px-3.5 py-2 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:bg-primary/10 hover:text-foreground" onClick={() => chat.setDraft(prompt)}>{prompt}</button>)}
          </div>
        </div>
      </section> : <>
        <ChatWindow className="min-h-0" contentClassName="px-0"><div className={`${layoutWidthClass} space-y-6 py-2`}>
          {chat.loading && <p role="status" className="py-12 text-center text-sm text-muted-foreground">Loading conversation…</p>}
          {chat.messages.map((message) => <ChatBubble key={message.id} message={message} onCopy={copyMessage} />)}
          {chat.sending && <TypingIndicator variant="minimal" />}
        </div></ChatWindow>
        <div className="sticky bottom-0 z-10 w-full bg-background/80 py-2 backdrop-blur-md"><div className={layoutWidthClass}><div className="rounded-[1.75rem] border border-border/80 bg-background/80 p-2 shadow-lg">{promptInput}</div></div></div>
      </>}
      <p className="shrink-0 py-2 text-center text-[11px] text-muted-foreground">Answers grounded in your indexed sources</p>
    </main>
  </div>
}
