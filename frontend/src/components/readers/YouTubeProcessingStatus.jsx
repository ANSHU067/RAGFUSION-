import { AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { ProgressBar } from '@/components/upload'

export function YouTubeProcessingStatus({ video }) {
  const status = video?.status || 'pending'
  const complete = status === 'completed'
  const failed = status === 'failed'

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        {complete ? <CheckCircle className="size-4 text-emerald-500" /> : failed ? <AlertTriangle className="size-4 text-destructive" /> : <Loader2 className="size-4 animate-spin text-primary" />}
        {complete ? 'Ready for chat' : failed ? video?.error || 'Video processing failed' : 'Video processing'}
      </div>
      {!complete && !failed && <ProgressBar className="mt-3" value={video?.progress || 0} label="Transcribing" />}
    </div>
  )
}