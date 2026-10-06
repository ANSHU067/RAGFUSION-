import { ExternalLink, RefreshCw, X, Video as Youtube } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function YouTubePreview({ video, onClose, onRefresh, onOpenInNewTab, className, height = '70vh' }) {
  if (!video) return null

  const videoId = video.url?.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/)?.[1]
  const embedUrl = videoId ? `https://www.youtube.com/embed/${videoId}` : video.url

  const open = () => onOpenInNewTab?.() || window.open(video.url, '_blank', 'noopener,noreferrer')

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="YouTube video preview">
      <Card className={`flex w-full max-w-6xl flex-col ${className || ''}`} style={{ height }}>
        <CardHeader className="flex flex-row items-center justify-between border-b">
          <CardTitle className="flex min-w-0 items-center gap-2 truncate">
            <Youtube className="size-5 shrink-0 text-primary" />
            <span className="truncate">{video.title || 'YouTube video'}</span>
          </CardTitle>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" onClick={onRefresh} aria-label="Refresh processing">
              <RefreshCw className="size-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={open} aria-label="Open video in a new tab">
              <ExternalLink className="size-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close preview">
              <X className="size-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="min-h-0 flex-1 p-0">
          <iframe
            title={`Preview of ${video.title || 'YouTube video'}`}
            src={embedUrl}
            className="size-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </CardContent>
      </Card>
    </div>
  )
}

export function YouTubePreviewGrid({ videos = [], onSelect }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {videos.map((video) => (
        <button
          key={video.id}
          onClick={() => onSelect?.(video)}
          className="rounded-xl border p-4 text-left transition-colors hover:bg-muted"
        >
          <Youtube className="mb-3 size-7 text-primary" />
          <p className="truncate font-medium">{video.title || 'YouTube video'}</p>
          <p className="mt-1 truncate text-sm text-muted-foreground">{video.url}</p>
        </button>
      ))}
    </div>
  )
}

export function YouTubePreviewList({ videos = [], onSelect }) {
  return (
    <div className="space-y-2">
      {videos.map((video) => (
        <button
          key={video.id}
          onClick={() => onSelect?.(video)}
          className="flex w-full items-center gap-3 rounded-xl border p-4 text-left hover:bg-muted"
        >
          <Youtube className="size-5 text-primary" />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium">{video.title || 'YouTube video'}</span>
            <span className="block truncate text-sm text-muted-foreground">{video.url}</span>
          </span>
          <span className="text-xs capitalize text-muted-foreground">{video.status || 'pending'}</span>
        </button>
      ))}
    </div>
  )
}