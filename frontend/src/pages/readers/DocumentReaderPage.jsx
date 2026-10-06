import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, FileUp, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  UploadCard, 
  FileList, 
  DocumentPreview, 
  ProcessingStatus, 
  UploadHistory 
} from '@/components/upload'
import { sourceApi } from '@/services/documents'

export default function DocumentReaderPage() {
  // State definitions
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  const actionInFlight = useRef(new Set())
  const [busyFileIds, setBusyFileIds] = useState([])

  // Fetch sources
  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await sourceApi.list({ type: 'document' })
      setSources(result.sources || result || [])
    } catch {
      setError('We could not load your documents. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    load()
  }, [load])

  // Handle document actions (delete, retry, preview)
  const action = async (kind, source) => {
    if (kind !== 'preview' && actionInFlight.current.has(source.id)) return
    if (kind !== 'preview') actionInFlight.current.add(source.id)
    if (kind !== 'preview') setBusyFileIds((ids) => [...ids, source.id])
    try {
      if (kind === 'delete') {
        await sourceApi.delete(source.id)
      }
      
      if (kind === 'retry') {
        await sourceApi.process(source.id)
      }
      
      if (kind === 'preview') {
        setPreview(source)
        return
      }
      
      await load()
    } catch {
      console.error(`Unable to ${kind} this document.`)
    } finally {
      actionInFlight.current.delete(source.id)
      setBusyFileIds((ids) => ids.filter((id) => id !== source.id))
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Document Reader</h1>
        <p className="mt-1 text-muted-foreground">
          Upload, process, and inspect documents in your knowledge base.
        </p>
      </header>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileUp className="size-5 text-primary" />
            Upload documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          <UploadCard onUploadComplete={load} />
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <p role="alert" className="flex items-center gap-2 text-sm text-destructive">
          <AlertTriangle className="size-4" />
          {error}
          <Button variant="link" onClick={load}>Retry</Button>
        </p>
      )}

      {/* Main Content & Sidebar Layout */}
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        {/* Document List */}
        <div className="space-y-4">
          {loading ? (
            <Card>
              <CardContent className="grid min-h-40 place-items-center p-6 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading documents…
              </CardContent>
            </Card>
          ) : (
            <FileList 
              files={sources} 
              onFileSelect={setPreview} 
              onFileAction={action} 
              busyFileIds={busyFileIds}
            />
          )}
        </div>

        {/* Sidebar */}
        <aside className="space-y-4">
          <ProcessingStatus 
            source={sources.find((source) => source.status === 'processing') || { status: 'completed' }} 
          />
          <UploadHistory 
            history={sources} 
            onItemAction={action} 
          />
        </aside>
      </section>

      {/* Document Preview Modal */}
      {preview && (
        <DocumentPreview 
          document={preview} 
          onClose={() => setPreview(null)} 
        />
      )}
    </div>
  )
}
