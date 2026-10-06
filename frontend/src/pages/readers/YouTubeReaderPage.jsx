import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle, Loader2, Plus, Trash2, Video } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { YouTubeURLInput } from '@/components/forms'
import { YouTubeHistory, YouTubePreview, YouTubeSourceMetadata, YouTubeProcessingStatus, TranscriptPanel, SummaryPanel } from '@/components/readers'
import { youtubeSourceApi } from '@/services/youtubeSourceApi'
import { toast } from 'sonner'

const statusStyle = (status) => status === 'completed' ? 'success' : status === 'failed' ? 'destructive' : status === 'processing' ? 'info' : 'secondary'

export default function YouTubeReaderPage() {
  const [videos, setVideos] = useState([])
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [preview, setPreview] = useState(null)
  const [transcript, setTranscript] = useState(null)
  const [transcriptLoading, setTranscriptLoading] = useState(false)
  const [transcriptError, setTranscriptError] = useState('')
  const actionInFlight = useRef(new Set())
  const [busyIds, setBusyIds] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setVideos(await youtubeSourceApi.list())
    } catch {
      setError('We could not load YouTube sources. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    let active = true
    setTranscript(null)
    setTranscriptError('')
    if (!selected || selected.status !== 'completed') return () => { active = false }
    setTranscriptLoading(true)
    youtubeSourceApi.getTranscript(selected.id).then((data) => {
      if (active) setTranscript(data)
    }).catch(() => {
      if (active) setTranscriptError('We could not load this transcript.')
    }).finally(() => {
      if (active) setTranscriptLoading(false)
    })
    return () => { active = false }
  }, [selected])

  const addVideo = async (submittedUrl) => {
    setSaving(true)
    setError('')
    try {
      const video = await youtubeSourceApi.create(submittedUrl)
      setVideos((items) => [video, ...items.filter((item) => item.id !== video.id)])
      setUrl('')
      setSelected(video)
      toast.success('Video added and queued for transcript extraction')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to add this video.')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id) => {
    if (actionInFlight.current.has(id)) return
    actionInFlight.current.add(id)
    setBusyIds((ids) => [...ids, id])
    try {
      await youtubeSourceApi.remove(id)
      setVideos((items) => items.filter((item) => item.id !== id))
      if (selected?.id === id) setSelected(null)
      toast.success('Video removed')
    } catch {
      toast.error('Unable to remove video')
    } finally {
      actionInFlight.current.delete(id)
      setBusyIds((ids) => ids.filter((value) => value !== id))
    }
  }

  const stats = useMemo(() => ({
    total: videos.length,
    ready: videos.filter((video) => video.status === 'completed').length,
    processing: videos.filter((video) => video.status === 'processing' || video.status === 'pending').length,
    failed: videos.filter((video) => video.status === 'failed').length,
  }), [videos])

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">YouTube Reader</h1>
        <p className="mt-1 text-muted-foreground">Extract transcripts from YouTube videos for grounded conversations.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="size-5 text-primary" />
            Add a YouTube video
          </CardTitle>
        </CardHeader>
        <CardContent>
          <YouTubeURLInput value={url} onChange={setUrl} onSubmit={addVideo} disabled={saving} />
          {error && (
            <p className="mt-3 flex items-center gap-2 text-sm text-destructive" role="alert">
              <AlertTriangle className="size-4" />
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[['Total', stats.total, Video], ['Ready', stats.ready, CheckCircle], ['Processing', stats.processing, Loader2], ['Failed', stats.failed, AlertTriangle]].map(([label, value, Icon]) => (
          <Card key={label}>
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="text-2xl font-semibold">{value}</p>
              </div>
              <Icon className={`size-5 ${label === 'Ready' ? 'text-emerald-500' : label === 'Failed' ? 'text-destructive' : 'text-primary'}`} />
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <TranscriptPanel video={selected} data={transcript} loading={transcriptLoading} error={transcriptError} />
        <SummaryPanel video={selected} data={transcript} loading={transcriptLoading} error={transcriptError} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card>
          <CardHeader>
            <CardTitle>Indexed videos</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="grid min-h-48 place-items-center text-sm text-muted-foreground" role="status">
                <Loader2 className="mr-2 size-4 animate-spin" />
                Loading YouTube sources…
              </div>
            ) : videos.length ? (
              <ul className="divide-y">
                {videos.map((video) => (
                  <li key={video.id} className="flex items-center gap-3 py-4">
                    <button
                      onClick={() => setSelected(video)}
                      className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    >
                      <Video className="size-5 shrink-0 text-primary" />
                      <span className="min-w-0">
                        <span className="block truncate font-medium">{video.title || video.url}</span>
                        <span className="block truncate text-sm text-muted-foreground">{video.url}</span>
                      </span>
                    </button>
                    <Badge variant={statusStyle(video.status)} className="hidden sm:inline-flex capitalize">
                      {video.status}
                    </Badge>
                    <Button variant="outline" size="sm" disabled={busyIds.includes(video.id)} onClick={() => setPreview(video)}>
                      Preview
                    </Button>
                    <Button variant="ghost" size="icon" disabled={busyIds.includes(video.id)} onClick={() => remove(video.id)} aria-label={`Remove ${video.title || video.url}`}>
                      <Trash2 className="size-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="grid min-h-48 place-items-center text-center text-sm text-muted-foreground">
                <div>
                  <Video className="mx-auto mb-3 size-10 opacity-50" />
                  No videos yet. Add a YouTube URL above to start extracting transcripts.
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <aside className="space-y-6">
          {selected ? (
            <>
              <YouTubeSourceMetadata source={selected} onAction={(action, video) => action === 'view' && setPreview(video)} />
              <YouTubeProcessingStatus video={selected} />
            </>
          ) : (
            <Card>
              <CardContent className="p-6 text-sm text-muted-foreground">
                Select a video to inspect its metadata and processing status.
              </CardContent>
            </Card>
          )}
          <YouTubeHistory history={videos} onItemAction={(_, video) => setSelected(video)} />
        </aside>
      </section>

      {preview && (
        <YouTubePreview
          video={preview}
          onClose={() => setPreview(null)}
          onOpenInNewTab={() => window.open(preview.url, '_blank', 'noopener,noreferrer')}
        />
      )}
    </div>
  )
}
