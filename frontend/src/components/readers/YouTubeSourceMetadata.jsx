import { ExternalLink, Video } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function YouTubeSourceMetadata({ source, onAction, className }) {
  if (!source) return null

  const getStatusBadge = (status) => {
    const variants = {
      completed: 'success',
      processing: 'info',
      pending: 'secondary',
      failed: 'destructive',
    }
    return <Badge variant={variants[status] || 'secondary'} className="capitalize">{status}</Badge>
  }

  const fields = [
    ['Status', getStatusBadge(source.status || 'pending')],
    ['Transcript length', source.transcriptLength ? `${source.transcriptLength.toLocaleString()} chars` : '—'],
    ['Chunks', source.chunks ?? '—'],
    ['Duration', source.duration ? `${Math.floor(source.duration / 60)}:${String(source.duration % 60).padStart(2, '0')}` : '—'],
    ['Added', source.createdAt ? new Date(source.createdAt).toLocaleString() : '—'],
    ['Last processed', source.lastProcessed ? new Date(source.lastProcessed).toLocaleString() : '—'],
  ]

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Video className="size-5 text-red-500" />
          {source.title || 'YouTube video metadata'}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <a
          className="block truncate text-sm text-primary underline"
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {source.url}
        </a>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          {fields.map(([term, detail], idx) => (
            <div key={`${term}-${idx}`}>
              <dt className="text-muted-foreground">{term}</dt>
              <dd className="mt-1 font-medium">{detail}</dd>
            </div>
          ))}
        </dl>
        <Button variant="outline" onClick={() => onAction?.('view', source)}>
          <ExternalLink className="mr-2 size-4" />
          Open video
        </Button>
      </CardContent>
    </Card>
  )
}