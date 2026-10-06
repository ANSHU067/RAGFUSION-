import { Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function UploadHistory({ history = [], onItemAction, className }) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="size-4" />
          Upload history
        </CardTitle>
      </CardHeader>
      <CardContent>
        {history.length ? (
          <ul className="space-y-3">
            {history.map((item) => (
              <li key={item.id} className="flex justify-between gap-3 text-sm">
                
                {/* Clickable item name */}
                <button 
                  onClick={() => onItemAction?.('preview', item)} 
                  className="truncate text-left hover:underline"
                >
                  {item.filename || item.name || item.title || item.url}
                </button>
                
                {/* Formatting for the upload date */}
                <time className="shrink-0 text-muted-foreground">
                  {item.createdAt || item.created_at
                    ? new Date(item.createdAt || item.created_at).toLocaleDateString()
                    : 'Recently'}
                </time>
                
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No uploads yet.</p>
        )}
      </CardContent>
    </Card>
  )
}