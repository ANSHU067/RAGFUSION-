import { CheckCircle, Loader2, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ProgressBar({ value = 0, label, className, variant = 'default' }) {
  const percent = Math.max(0, Math.min(100, value))
  const colours = { default: 'bg-primary', success: 'bg-emerald-500', warning: 'bg-amber-500', error: 'bg-destructive' }
  return <div className={cn('space-y-1', className)}>{label && <div className="flex justify-between text-sm"><span>{label}</span><span className="text-muted-foreground">{Math.round(percent)}%</span></div>}<div className="h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-label={label} aria-valuenow={percent} aria-valuemin="0" aria-valuemax="100"><div className={cn('h-full transition-[width] duration-300', colours[variant])} style={{ width: `${percent}%` }} /></div></div>
}

export function MultiStageProgress({ currentStage = 'upload', stageProgress = 0 }) {
  const stages = ['upload', 'chunking', 'embedding', 'indexing']
  const current = stages.indexOf(currentStage)
  return <ol className="space-y-3">{stages.map((stage, index) => <li key={stage} className="flex items-center gap-3"><span className="grid size-7 place-items-center rounded-full bg-muted">{index < current ? <CheckCircle className="size-4 text-emerald-500" /> : index === current ? <Loader2 className="size-4 animate-spin text-primary" /> : index + 1}</span><ProgressBar className="flex-1" label={stage[0].toUpperCase() + stage.slice(1)} value={index < current ? 100 : index === current ? stageProgress : 0} variant={index < current ? 'success' : 'default'} /></li>)}</ol>
}

export function CircularProgress({ value = 0, size = 48, className }) {
  const percent = Math.max(0, Math.min(100, value))
  return <div className={cn('grid place-items-center rounded-full border-4 border-primary text-xs font-semibold', className)} style={{ width: size, height: size }} aria-label={`${Math.round(percent)}% complete`}>{Math.round(percent)}%</div>
}

export function ProcessingStatus({ source }) {
  const failed = source?.status === 'failed'
  const complete = source?.status === 'completed'
  return <div className="flex items-center gap-2 text-sm">{failed ? <AlertTriangle className="size-4 text-destructive" /> : complete ? <CheckCircle className="size-4 text-emerald-500" /> : <Loader2 className="size-4 animate-spin text-primary" />}<span>{failed ? source.error || 'Processing failed' : complete ? 'Ready for chat' : 'Processing source'}</span></div>
}

export function UploadProgressList({ files = [] }) { return <div className="space-y-2">{files.map((file) => <ProgressBar key={file.id} label={file.name} value={file.progress || 0} />)}</div> }
export function ProcessingQueue({ sources = [] }) { return <div className="space-y-2">{sources.map((source) => <ProcessingStatus key={source.id} source={source} />)}</div> }
