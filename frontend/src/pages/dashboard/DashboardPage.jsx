import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, FileText, Video, Globe, MessageSquareText, Sparkles, Clock3, RefreshCw } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { dashboardApi } from '@/services/dashboard'
import { getApiError, isCanceled } from '@/services/api'
import { Button } from '@/components/ui/button'
import { parseTimestamp } from '@/lib/dates'

const tools = [
  { key: 'documents', label: 'Documents indexed', action: 'Upload document', description: 'Turn PDFs and files into answers.', path: '/documents/reader', icon: FileText, color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400' },
  { key: 'youtube', label: 'Videos ingested', action: 'Ingest YouTube video', description: 'Explore ideas inside a transcript.', path: '/youtube/reader', icon: Video, color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400' },
  { key: 'websites', label: 'Websites crawled', action: 'Scrape website', description: 'Bring a public webpage into context.', path: '/website/reader', icon: Globe, color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
  { key: 'conversations', label: 'Active conversations', action: 'Start new chat', description: 'Connect the dots across your sources.', path: '/chat/new', icon: MessageSquareText, color: 'bg-violet-500/10 text-violet-600 dark:text-violet-400' },
]
const timestamp = (value) => { const date = parseTimestamp(value); return date ? date.toLocaleString() : '—' }

export default function DashboardPage() {
  const { user } = useAuth()
  const [overview, setOverview] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    dashboardApi.overview({ signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) setOverview(data)
    }).catch((err) => {
      if (!controller.signal.aborted && !isCanceled(err)) setError(getApiError(err, 'Unable to load your workspace overview.'))
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [refresh])
  const reload = () => { setLoading(true); setError(''); setRefresh((value) => value + 1) }
  return <div className="mx-auto max-w-7xl space-y-8 pb-8">
    <header className="relative overflow-hidden rounded-3xl border bg-gradient-to-br from-primary/10 via-card to-card p-6 sm:p-9">
      <div className="pointer-events-none absolute -right-14 -top-16 h-64 w-64 rounded-full bg-primary/10 blur-3xl" aria-hidden="true" />
      <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
        <div><p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Sparkles className="h-4 w-4" /> Your knowledge, connected</p><h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">Welcome back, {user?.display_name || user?.username || 'there'}.</h1><p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">A place to explore your sources, continue a thought, and find answers worth keeping.</p></div>
        <Button asChild className="shrink-0 self-start sm:self-center"><Link to="/chat"><MessageSquareText className="mr-2 h-4 w-4" />Open your chat<ArrowRight className="ml-2 h-4 w-4" /></Link></Button>
      </div>
    </header>
    <section aria-label="Workspace statistics">
      <div className="mb-3 flex items-center justify-between"><p className="text-xs text-muted-foreground">{loading ? 'Updating your workspace…' : 'Indexed sources and active conversations'}</p><Button variant="ghost" size="sm" onClick={reload} disabled={loading}><RefreshCw className={'mr-2 h-3 w-3' + (loading ? ' animate-spin' : '')} />Refresh</Button></div>
      {error && <p role="alert" className="mb-4 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {tools.map(({ key, label, icon: Icon, color }) => <div key={key} className="rounded-2xl border bg-card p-5 shadow-sm">
          <div className={'mb-4 inline-flex rounded-xl p-2.5 ' + color}><Icon className="h-5 w-5" /></div>
          <p className="text-3xl font-semibold tracking-tight tabular-nums">{overview ? overview.stats[key].toLocaleString() : '—'}</p><h2 className="mt-1 text-xs text-muted-foreground sm:text-sm">{label}</h2>
        </div>)}
      </div>
    </section>
    <section aria-labelledby="actions-heading"><div className="mb-4"><h2 id="actions-heading" className="text-xl font-semibold tracking-tight">Make room for a new idea</h2><p className="mt-1 text-sm text-muted-foreground">Add a source or start exploring what you already know.</p></div>
      <nav aria-label="Quick actions" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{tools.map(({ key, action, description, path, icon: Icon, color }) => <Link key={key} to={path} className="group rounded-2xl border bg-card p-5 transition duration-200 hover:-translate-y-1 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transform-none">
        <div className="flex items-center justify-between"><span className={'rounded-lg p-2 ' + color}><Icon className="h-5 w-5" /></span><ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" /></div><h3 className="mt-4 font-semibold">{action}</h3><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
      </Link>)}</nav>
    </section>
    <section aria-labelledby="recent-heading" className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b p-5"><div><h2 id="recent-heading" className="text-lg font-semibold">Pick up where you left off</h2><p className="mt-1 text-xs text-muted-foreground">Your most recently updated conversations.</p></div><Link to="/dashboard/history" className="shrink-0 text-sm font-medium text-primary hover:underline">View history</Link></div>
      {loading && !overview ? <p role="status" className="p-8 text-sm text-muted-foreground">Loading recent activity…</p> : overview?.recent_sessions.length ? <ul className="divide-y">{overview.recent_sessions.map((session) => <li key={session.id}><Link to={'/chat/' + session.id} state={{ refreshChat: true }} aria-label={'Resume ' + session.title} className="group flex items-center gap-4 p-5 transition-colors hover:bg-muted/50 focus-visible:bg-muted">
        <div className="hidden rounded-xl bg-muted p-3 sm:block"><MessageSquareText className="h-5 w-5 text-muted-foreground" /></div><div className="min-w-0 flex-1"><h3 className="truncate font-medium">{session.title}</h3><p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground"><span className="flex items-center gap-1"><Clock3 className="h-3 w-3" /><time dateTime={session.updated_at}>{timestamp(session.updated_at)}</time></span><span>{session.message_count} messages</span><span>{session.token_count.toLocaleString()} recorded tokens</span></p></div><ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary" />
      </Link></li>)}</ul> : <div className="p-10 text-center"><MessageSquareText className="mx-auto mb-3 h-8 w-8 text-muted-foreground/60" /><p className="font-medium">{error ? 'Activity is temporarily unavailable' : 'Your next conversation starts here'}</p><p className="mt-2 text-sm text-muted-foreground">{error ? 'Use Refresh to try again.' : 'Add a source, ask a question, and your recent activity will appear here.'}</p></div>}
    </section>
  </div>
}
