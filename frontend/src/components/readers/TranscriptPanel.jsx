import { FileText, Sparkles } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function TranscriptPanel({ video, data, loading, error }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="size-5 text-primary" />
          Transcript
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!video ? (
          <p className="text-sm text-muted-foreground">Select a completed video to read its transcript.</p>
        ) : video.status !== 'completed' ? (
          <p className="text-sm text-muted-foreground">The transcript will appear here when processing is complete.</p>
        ) : loading ? (
          <p className="text-sm text-muted-foreground" role="status">Loading transcript…</p>
        ) : error ? (
          <p className="text-sm text-destructive" role="alert">{error}</p>
        ) : (
          <p className="max-h-72 overflow-y-auto whitespace-pre-wrap pr-2 text-sm leading-6 text-muted-foreground">{data?.transcript}</p>
        )}
      </CardContent>
    </Card>
  )
}

export function SummaryPanel({ video, data, loading, error }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-5 text-primary" />
          Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!video ? (
          <p className="text-sm text-muted-foreground">A concise source summary will appear here.</p>
        ) : video.status !== 'completed' ? (
          <p className="text-sm text-muted-foreground">The summary is generated after the transcript is ready.</p>
        ) : loading ? (
          <p className="text-sm text-muted-foreground" role="status">Generating summary…</p>
        ) : error ? (
          <p className="text-sm text-destructive" role="alert">Summary unavailable. Try selecting the video again.</p>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">{data?.summary || 'No summary is available for this video yet.'}</p>
        )}
      </CardContent>
    </Card>
  )
}
