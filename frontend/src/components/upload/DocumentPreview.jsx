import { X, FileText, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
export function DocumentPreview({ document, onClose, className }) {
  if (!document) return null
  const url = document.previewUrl || document.url
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Document preview"><Card className={`max-h-[90vh] w-full max-w-4xl ${className || ''}`}><CardHeader className="flex flex-row items-center justify-between border-b"><CardTitle className="truncate">{document.name || document.title || 'Document preview'}</CardTitle><div className="flex gap-1">{url && <Button asChild variant="ghost" size="icon" aria-label="Download document"><a href={url} download><Download className="size-4" /></a></Button>}<Button variant="ghost" size="icon" onClick={onClose} aria-label="Close preview"><X className="size-4" /></Button></div></CardHeader><CardContent className="min-h-80 p-0">{url ? <iframe title="Document preview" src={url} className="h-[70vh] w-full" /> : <div className="grid h-80 place-items-center text-muted-foreground"><div className="text-center"><FileText className="mx-auto mb-3 size-10" />A preview is not available for this document.</div></div>}</CardContent></Card></div>
}
export function DocumentPreviewPanel(props) { return <DocumentPreview {...props} /> }
