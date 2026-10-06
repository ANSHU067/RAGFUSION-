import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ChevronLeft, ChevronRight, Clock3, Edit3, FileClock, Loader2, Search, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { historyApi } from '@/services/historyApi'
import { Link } from 'react-router-dom'
import { useAsyncScope } from '@/hooks/useAsyncScope'
import { isCanceled, getApiError } from '@/services/api'
import { parseTimestamp } from '@/lib/dates'

const pageSizes = [5, 10, 20]
const statusVariant = (status) => status === 'completed' ? 'success' : status === 'failed' ? 'destructive' : 'info'
const formatDate = (value) => { const date = parseTimestamp(value); return date ? date.toLocaleString() : '—' }

export default function HistoryPage() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('all')
  const [date, setDate] = useState('all')
  const [sort, setSort] = useState('newest')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(5)
  const [filterReferenceTime] = useState(() => Date.now())
  const [editing, setEditing] = useState(null)
  const [draft, setDraft] = useState('')
  const [deleting, setDeleting] = useState(null)
  const [deletePending, setDeletePending] = useState(false)
  const [renamePending, setRenamePending] = useState(false)
  const begin = useAsyncScope()

  useEffect(() => {
    const controller = new AbortController()
    historyApi.list({}, { signal: controller.signal }).then((items) => {
      if (!controller.signal.aborted) setSessions(items)
    }).catch((err) => {
      if (!controller.signal.aborted && !isCanceled(err)) setError(getApiError(err, 'We could not load history. Please try again.'))
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [])

  const filtered = useMemo(() => {
    const dateThreshold = date === 'today' ? filterReferenceTime - 86400000 : date === 'week' ? filterReferenceTime - 604800000 : 0
    return sessions.filter((item) => {
      const searchable = `${item.title} ${item.session}`.toLowerCase()
      return (!query || searchable.includes(query.toLowerCase())) && (type === 'all' || item.type === type) && (status === 'all' || item.status === status) && (!dateThreshold || item.createdAt >= dateThreshold)
    }).sort((a, b) => {
      if (sort === 'oldest') return a.createdAt - b.createdAt
      if (sort === 'az') return a.title.localeCompare(b.title)
      if (sort === 'za') return b.title.localeCompare(a.title)
      return b.createdAt - a.createdAt
    })
  }, [sessions, query, type, status, date, sort, filterReferenceTime])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const activePage = Math.min(page, totalPages)
  const visible = filtered.slice((activePage - 1) * pageSize, activePage * pageSize)
  const recent = [...sessions].sort((a, b) => b.createdAt - a.createdAt).slice(0, 3)
  const updateFilter = (setter) => (event) => { setter(event.target.value); setPage(1) }

  const startEdit = (item) => { setEditing(item.id); setDraft(item.title) }
  const saveEdit = async (id) => {
    const task = begin('mutation')
    if (!task) return
    setRenamePending(true)
    try {
      const updated = await historyApi.rename(id, draft, { signal: task.signal })
      if (!task.active()) return
      setSessions((items) => items.map((item) => item.id === id ? { ...item, title: updated.title } : item))
      setEditing(null)
      toast.success('Session renamed')
    } catch (requestError) {
      if (task.active() && !isCanceled(requestError)) toast.error(getApiError(requestError, 'Unable to rename session'))
    } finally { task.done(); if (task.active()) setRenamePending(false) }
  }
  const remove = async () => {
    if (!deleting || deletePending) return
    const task = begin('mutation')
    if (!task) return
    setDeletePending(true)
    try {
      await historyApi.remove(deleting.id, { signal: task.signal })
      if (!task.active()) return
      setSessions((items) => items.filter((item) => item.id !== deleting.id))
      setDeleting(null)
      toast.success('Session deleted')
    } catch (err) {
      if (task.active() && !isCanceled(err)) toast.error(getApiError(err, 'Unable to delete session'))
    } finally {
      task.done(); if (task.active()) setDeletePending(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">History</h1>
        <p className="mt-1 text-muted-foreground">Find, organize, and revisit your previous sessions.</p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          <CardContent className="space-y-4 pt-6">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="relative w-full lg:max-w-sm">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input value={query} onChange={updateFilter(setQuery)} placeholder="Search title or session" className="pl-9" aria-label="Search history" />
              </div>
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={sort} onChange={updateFilter(setSort)} aria-label="Sort history">
                <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="az">Alphabetical (A–Z)</option><option value="za">Alphabetical (Z–A)</option>
              </select>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={type} onChange={updateFilter(setType)} aria-label="Filter by session type"><option value="all">All types</option><option value="document">Documents</option><option value="youtube">YouTube</option><option value="chat">Chats</option></select>
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={status} onChange={updateFilter(setStatus)} aria-label="Filter by status"><option value="all">All statuses</option><option value="completed">Completed</option><option value="processing">Processing</option><option value="failed">Failed</option></select>
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={date} onChange={updateFilter(setDate)} aria-label="Filter by date"><option value="all">Any date</option><option value="today">Last 24 hours</option><option value="week">Last 7 days</option></select>
            </div>
          </CardContent>
          <div className="overflow-x-auto border-t">
            {loading ? <div className="grid min-h-56 place-items-center text-sm text-muted-foreground" role="status"><Loader2 className="mr-2 size-4 animate-spin" />Loading history…</div> : error ? <div className="grid min-h-56 place-items-center text-sm text-destructive" role="alert"><AlertTriangle className="mr-2 size-4" />{error}</div> : visible.length ? (
              <table className="w-full min-w-[42.5rem] text-left text-sm">
                <thead className="bg-muted/40 text-muted-foreground"><tr><th className="px-6 py-3 font-medium">Title</th><th className="px-4 py-3 font-medium">Session</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Last activity</th><th className="px-6 py-3 text-right font-medium"><span className="sr-only">Actions</span></th></tr></thead>
                <tbody className="divide-y">{visible.map((item) => <tr key={item.id} className="hover:bg-muted/30">
                  <td className="px-6 py-4 font-medium">{editing === item.id ? <div className="flex min-w-52 gap-2"><Input value={draft} onChange={(event) => setDraft(event.target.value)} aria-label="Session title" autoFocus /><Button size="sm" disabled={renamePending || deletePending} onClick={() => saveEdit(item.id)}>Save</Button><Button size="sm" variant="ghost" disabled={renamePending} onClick={() => setEditing(null)}>Cancel</Button></div> : <Link to={`/chat/${item.id}`} state={{ refreshChat: true }} className="text-primary hover:underline">{item.title}</Link>}</td>
                  <td className="px-4 py-4 text-muted-foreground">{item.session}</td><td className="px-4 py-4"><Badge variant={statusVariant(item.status)} className="capitalize">{item.status}</Badge></td><td className="px-4 py-4 text-muted-foreground">{formatDate(item.createdAt)}</td>
                  <td className="px-6 py-4"><div className="flex justify-end gap-1"><Button variant="ghost" size="icon-sm" onClick={() => startEdit(item)} aria-label={`Rename ${item.title}`}><Edit3 className="size-4" /></Button><Button variant="ghost" size="icon-sm" onClick={() => setDeleting(item)} aria-label={`Delete ${item.title}`}><Trash2 className="size-4 text-destructive" /></Button></div></td>
                </tr>)}</tbody>
              </table>
            ) : <div className="grid min-h-56 place-items-center p-6 text-center text-sm text-muted-foreground"><div><FileClock className="mx-auto mb-3 size-10 opacity-50" />No sessions match these filters.</div></div>}
          </div>
          {!loading && !error && filtered.length > 0 && <CardContent className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between"><label className="flex items-center gap-2 text-sm text-muted-foreground">Rows <select className="h-8 rounded-md border bg-background px-2" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1) }}>{pageSizes.map((size) => <option key={size}>{size}</option>)}</select></label><div className="flex items-center gap-1"><Button variant="outline" size="sm" disabled={activePage === 1} onClick={() => setPage(activePage - 1)}><ChevronLeft />Previous</Button>{Array.from({ length: totalPages }, (_, index) => index + 1).map((number) => <Button key={number} variant={number === activePage ? 'default' : 'outline'} size="icon-sm" onClick={() => setPage(number)} aria-label={`Page ${number}`} aria-current={number === activePage ? 'page' : undefined}>{number}</Button>)}<Button variant="outline" size="sm" disabled={activePage === totalPages} onClick={() => setPage(activePage + 1)}>Next<ChevronRight /></Button></div></CardContent>}
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Clock3 className="size-5 text-primary" />Recent sessions</CardTitle></CardHeader>
          <CardContent>{recent.length ? <ul className="space-y-4">{recent.map((item) => <li key={item.id}><Link to={`/chat/${item.id}`} state={{ refreshChat: true }} className="block truncate text-sm font-medium text-primary hover:underline">{item.title}</Link><p className="mt-1 text-xs text-muted-foreground">{item.session} · {formatDate(item.createdAt)}</p></li>)}</ul> : <p className="text-sm text-muted-foreground">Your recent sessions will appear here.</p>}</CardContent>
        </Card>
      </div>

      {deleting && <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="delete-history-title"><Card className="w-full max-w-md"><CardHeader><CardTitle id="delete-history-title">Delete session?</CardTitle></CardHeader><CardContent><p className="text-sm text-muted-foreground">“{deleting.title}” will be removed from your history.</p><div className="mt-6 flex justify-end gap-2"><Button variant="outline" disabled={deletePending} onClick={() => setDeleting(null)}>Cancel</Button><Button variant="destructive" disabled={deletePending} onClick={remove}>{deletePending ? 'Deleting…' : 'Delete'}</Button></div></CardContent></Card></div>}
    </div>
  )
}
