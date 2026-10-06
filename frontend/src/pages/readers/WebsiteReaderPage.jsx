import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Globe, ArrowUpRight, LoaderCircle, Trash2, MessageSquareText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { websiteApi } from '@/services/website'
import { getApiError, isCanceled } from '@/services/api'

const working = (status) => !['ready', 'failed', 'pending'].includes(status)
export default function WebsiteReaderPage() {
  const [url, setUrl] = useState('')
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const scope = useRef(null)
  const rows = useRef([])
  const lock = useRef('')
  const revision = useRef(0)
  const replaceItems = (next) => { rows.current = next; setItems(next) }
  useEffect(() => {
    const controller = new AbortController()
    scope.current = controller
    let timer
    const refresh = async () => {
      const captured = revision.current
      try {
        const data = await websiteApi.list({ signal: controller.signal })
        if (controller.signal.aborted) return
        if (captured === revision.current) { replaceItems(data.items); setTotal(data.total) }
      } catch (err) {
        if (!controller.signal.aborted && !isCanceled(err)) setError(getApiError(err, 'Unable to load websites.'))
        return // No automatic retry bursts after authorization or rate-limit failures.
      } finally { if (!controller.signal.aborted) setLoading(false) }
      timer = setTimeout(poll, 5000)
    }
    const poll = () => {
      if (controller.signal.aborted) return
      if (lock.current || rows.current.some((row) => working(row.status))) void refresh()
      else timer = setTimeout(poll, 5000)
    }
    void refresh()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [])
  const run = async (key, action) => {
    const controller = scope.current
    if (lock.current || !controller || controller.signal.aborted) return
    lock.current = key; setBusy(key); setError(''); ++revision.current
    try { await action(controller) }
    catch (err) { if (!controller.signal.aborted && !isCanceled(err)) setError(getApiError(err, 'Website request failed.')) }
    finally { if (!controller.signal.aborted) { lock.current = ''; setBusy(''); ++revision.current } }
  }
  const update = (item) => { ++revision.current; replaceItems([item, ...rows.current.filter((row) => row.id !== item.id)]) }
  const process = async (item, controller) => {
    try {
      const ready = await websiteApi.process(item.id, { signal: controller.signal })
      if (!controller.signal.aborted) update(ready)
    } catch (err) {
      // Read back the actual persisted failure/status, rather than inventing one.
      if (!controller.signal.aborted && !isCanceled(err)) {
        const data = await websiteApi.list({ signal: controller.signal }).catch(() => null)
        if (!controller.signal.aborted && data) { ++revision.current; replaceItems(data.items); setTotal(data.total) }
      }
      throw err
    }
  }
  const submit = (event) => {
    event.preventDefault()
    void run('submit', async (controller) => {
      const item = await websiteApi.create(url.trim(), { signal: controller.signal })
      if (controller.signal.aborted) return
      update(item); setTotal((value) => value + 1); setUrl('')
      await process(item, controller)
    })
  }
  return <div className="mx-auto max-w-6xl space-y-8">
    <header className="flex items-center gap-4"><div className="rounded-2xl bg-primary/10 p-4 text-primary"><Globe className="h-7 w-7" /></div><div><p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Knowledge sources</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Website reader</h1></div></header>
    <section className="rounded-2xl border bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Bring a webpage into your workspace</h2>
      <p className="mt-2 text-sm text-muted-foreground">Index the text from one public HTML page, then ask questions with source citations. Use the final page URL; redirects are disabled. Maximum page size: 2 MiB.</p>
      <form onSubmit={submit} className="mt-5 flex flex-col gap-3 sm:flex-row">
        <div className="min-w-0 flex-1"><label htmlFor="website-url" className="mb-1 block text-sm font-medium">Page URL</label><input id="website-url" type="url" required maxLength={2048} value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/article" disabled={!!busy} className="w-full rounded-lg border bg-background px-3 py-2" /></div>
        <Button type="submit" disabled={!!busy || loading} className="sm:self-end">{busy === 'submit' ? <><LoaderCircle className="mr-2 h-4 w-4 animate-spin" />Processing page…</> : 'Scrape website'}</Button>
      </form>
    </section>
    {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</p>}
    <section aria-labelledby="websites-heading"><div className="mb-4 flex items-center justify-between"><h2 id="websites-heading" className="text-xl font-semibold">Your websites</h2><span className="text-sm text-muted-foreground">{total} sources</span></div>
      {loading ? <p role="status">Loading websites…</p> : !items.length ? <div className="rounded-2xl border border-dashed p-12 text-center text-muted-foreground">Add your first page to start building your website knowledge base.</div> : <ul className="space-y-3">
        {items.map((item) => <li key={item.id} className="flex flex-col gap-4 rounded-xl border bg-card p-5 sm:flex-row sm:items-center">
          <div className="min-w-0 flex-1"><h3 className="truncate font-semibold">{item.title || item.url}</h3><a href={item.url} target="_blank" rel="noopener noreferrer" className="mt-1 flex items-center gap-1 text-sm text-muted-foreground"><span className="truncate">{item.url}</span><ArrowUpRight className="h-3 w-3 shrink-0" /></a><p role="status" className="mt-2 text-xs capitalize">{working(item.status) && <LoaderCircle className="mr-1 inline h-3 w-3 animate-spin" />}{item.status}{item.status === 'ready' && ` · ${item.metadata?.total_chunks ?? 0} chunks indexed`}</p></div>
          <div className="flex items-center gap-2">
            {item.status === 'ready' && <Button asChild variant="outline" size="sm"><Link to={`/chat?source=website:${item.id}`}><MessageSquareText className="mr-2 h-4 w-4" />Chat with website</Link></Button>}
            {['pending', 'failed'].includes(item.status) && <Button size="sm" disabled={!!busy} onClick={() => run(item.id, (controller) => process(item, controller))}>{busy === item.id ? 'Processing…' : item.status === 'failed' ? 'Retry' : 'Process'}</Button>}
            <Button variant="ghost" size="icon" aria-label={`Remove ${item.title || item.url}`} disabled={!!busy || working(item.status)} onClick={() => run(item.id, async (controller) => { await websiteApi.remove(item.id, { signal: controller.signal }); if (!controller.signal.aborted) { ++revision.current; replaceItems(rows.current.filter((row) => row.id !== item.id)); setTotal((value) => value - 1) } })}><Trash2 className="h-4 w-4" /></Button>
          </div>
        </li>)}
      </ul>}
      {total > items.length && <p className="mt-3 text-xs text-muted-foreground">Showing the latest {items.length} websites.</p>}
    </section>
  </div>
}
