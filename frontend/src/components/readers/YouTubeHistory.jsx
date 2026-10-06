import { Video as Youtube } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function YouTubeHistory({ history = [], onItemAction, className }) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Youtube className="size-4" />
          YouTube history
        </CardTitle>
      </CardHeader>
      <CardContent>
        {history.length ? (
          <ul className="space-y-3">
            {history.map((video) => (
              <li key={video.id} className="flex items-center justify-between gap-3">
                <button
                  onClick={() => onItemAction?.('preview', video)}
                  className="min-w-0 truncate text-left text-sm hover:underline"
                >
                  {video.title || video.url}
                </button>
                <span className="shrink-0 text-xs capitalize text-muted-foreground">
                  {video.status || 'pending'}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No YouTube videos have been indexed yet.</p>
        )}
      </CardContent>
    </Card>
  )
}