import { FileText, Loader2, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function SummaryPanel({ video, data, loading, error }) {
  if (!video || video.status !== 'completed') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-5 text-primary" />
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {video?.status === 'processing' ? 'Summary will appear after transcript extraction completes.' : 'Select a completed video to view its summary.'}
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-5 text-primary" />
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3 text-sm">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          Loading summary...
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-5 text-primary" />
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="size-5 text-primary" />
          Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="prose prose-sm dark:prose-invert max-w-none">
        <p>{data?.summary || 'No summary available.'}</p>
      </CardContent>
    </Card>
  )
}