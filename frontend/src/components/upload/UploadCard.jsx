import { useState, useCallback, useRef } from 'react'
import { Upload, X, FileText, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { documentsApi } from '@/services/documents'
import { getApiError } from '@/services/api'

const ACCEPTED_TYPES = ['.pdf', '.doc', '.docx', '.txt', '.md']
const MAX_FILE_SIZE = 25 * 1024 * 1024

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getFileIcon = (type) => {
  if (type.includes('pdf')) return <FileText className="h-5 w-5 text-red-500" />
  if (type.includes('word') || type.includes('document')) return <FileText className="h-5 w-5 text-blue-500" />
  if (type.includes('text') || type.includes('markdown')) return <FileText className="h-5 w-5 text-green-500" />
  return <FileText className="h-5 w-5 text-gray-500" />
}

const getFileStatus = (file) => {
  if (file.error) return { icon: <AlertTriangle className="h-4 w-4 text-red-500" />, label: 'Error', class: 'text-red-500' }
  if (file.processing) return { icon: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />, label: 'Processing', class: 'text-blue-500' }
  if (file.uploading) return { icon: <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />, label: 'Uploading', class: 'text-yellow-500' }
  if (file.uploaded) return { icon: <CheckCircle className="h-4 w-4 text-green-500" />, label: 'Ready', class: 'text-green-500' }
  return { icon: <FileText className="h-4 w-4 text-gray-400" />, label: 'Pending', class: 'text-gray-500' }
}

export function UploadCard({
    onFilesChange,
    onUploadComplete,
    maxFiles = 10,
    acceptedTypes = ACCEPTED_TYPES,
    maxSize = MAX_FILE_SIZE
}) {
  const [isDragActive, setIsDragActive] = useState(false)
  const [files, setFiles] = useState([])
  const fileInputRef = useRef(null)

  const validateFile = useCallback((file) => {
    const isValidType = acceptedTypes.some(type => file.type === type || file.name.endsWith(type.replace('.', '')))
    const isValidSize = file.size <= maxSize

    if (!isValidType) {
      return `File type not supported. Accepted: ${acceptedTypes.join(', ')}`
    }
    if (!isValidSize) {
      return `File size exceeds ${formatFileSize(maxSize)} limit`
    }
    return null
  }, [acceptedTypes, maxSize])

  const addFiles = useCallback((newFiles) => {
    const validFiles = []
    const errors = []

    Array.from(newFiles).forEach(file => {
      const error = validateFile(file)
      if (error) {
        errors.push(`${file.name}: ${error}`)
      } else if (files.length + validFiles.length < maxFiles) {
        validFiles.push({
          file,
          id: `${file.name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name: file.name,
          size: file.size,
          type: file.type,
          uploaded: false,
          uploading: false,
          processing: false,
          progress: 0,
          error: null,
        })
      } else {
        errors.push(`Maximum ${maxFiles} files allowed`)
      }
    })

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles])
      onFilesChange?.([...files, ...validFiles])
    }

    errors.forEach(error => toast.error(error))
  }, [files, maxFiles, onFilesChange, validateFile])

  const removeFile = useCallback((id) => {
    setFiles(prev => {
      const updated = prev.filter(f => f.id !== id)
      onFilesChange?.(updated)
      return updated
    })
  }, [onFilesChange])

  const handleDrag = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true)
    } else if (e.type === 'dragleave') {
      setIsDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files)
    }
  }, [addFiles])

  const handleFileSelect = useCallback((e) => {
    if (e.target.files.length > 0) {
      addFiles(e.target.files)
      e.target.value = ''
    }
  }, [addFiles])

  const openFileDialog = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const uploadFiles = useCallback(async (fileIds, onUploadProgress) => {
    const filesToUpload = files.filter(f => fileIds.includes(f.id) && !f.uploaded)
    
    for (const fileObj of filesToUpload) {
      setFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, uploading: true, progress: 0 } : f))
      
      try {
        // FIXED: Properly close the progress callback and await the result
        const data = await documentsApi.upload(fileObj.file, (progress) => {
          setFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, progress } : f))
          onUploadProgress?.(fileObj.id, progress)
        })

        // Set the final state once the await finishes
        setFiles(prev =>
          prev.map(f =>
            f.id === fileObj.id
              ? {
                  ...f,
                  uploading: false,
                  uploaded: true,
                  progress: 100,
                  documentId: data.document_id,
                }
              : f
          )
        )

        onUploadProgress?.(fileObj.id, 100)
        onUploadComplete?.()
      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { ...f, uploading: false, error: getApiError(error, 'Upload failed') } : f
        ))
        onUploadProgress?.(fileObj.id, -1)
      }
    }
  }, [files, onUploadComplete])

  const processFiles = useCallback(async (fileIds, onProcessProgress) => {
    const filesToProcess = files.filter(f => fileIds.includes(f.id) && f.uploaded && !f.processing)
    
    for (const fileObj of filesToProcess) {
      setFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, processing: true, progress: 0 } : f))
      
      try {
        await documentsApi.process(fileObj.documentId)

        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { ...f, processing: false, uploaded: true, progress: 100 } : f
        ))
        onProcessProgress?.(fileObj.id, 100)
      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { ...f, processing: false, error: getApiError(error, 'Processing failed') } : f
        ))
        onProcessProgress?.(fileObj.id, -1)
      }
    }
  }, [files])

  return (
    <Card className={`border-2 transition-colors ${isDragActive ? 'border-primary bg-primary/5' : 'border-dashed border-border'}`}>
      <CardContent className="p-6">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          className="sr-only"
          id="file-upload"
        />

        <label
          htmlFor="file-upload"
          className="flex flex-col items-center justify-center min-h-200px cursor-pointer"
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <p className="text-lg font-medium text-foreground mb-1">
            {isDragActive ? 'Drop files here...' : 'Drag & drop files here, or click to browse'}
          </p>
          <p className="text-sm text-muted-foreground mb-4">
            Supports: {acceptedTypes.join(', ')} • Max {formatFileSize(maxSize)} per file • Up to {maxFiles} files
          </p>
          <Button variant="outline" onClick={openFileDialog}>
            Browse Files
          </Button>
        </label>

        {files.length > 0 && (
          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between">
              <Label className="font-medium mb-0">Selected Files ({files.length}/{maxFiles})</Label>
              <Button variant="ghost" size="sm" onClick={() => { setFiles([]); onFilesChange?.([]) }}>
                <X className="h-3 w-3 mr-1" /> Clear All
              </Button>
            </div>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {files.map((fileObj) => {
                const status = getFileStatus(fileObj)
                const canUpload = !fileObj.uploaded && !fileObj.uploading && !fileObj.error
                const canProcess = fileObj.uploaded && !fileObj.processing && !fileObj.error
                
                return (
                  <div key={fileObj.id} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg border">
                    {getFileIcon(fileObj.type)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{fileObj.name}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{formatFileSize(fileObj.size)}</span>
                        <span>•</span>
                        <span className={status.class}>{status.label}</span>
                      </div>
                      {(fileObj.uploading || fileObj.processing) && (
                        <Progress value={fileObj.progress} className="mt-2 h-1.5" />
                      )}
                      {fileObj.error && (
                        <p className="mt-1 text-sm text-red-500">{fileObj.error}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {canUpload && (
                        <Button size="sm" variant="default" onClick={() => uploadFiles([fileObj.id])}>
                          <Upload className="h-3 w-3 mr-1" /> Upload
                        </Button>
                      )}
                      {canProcess && (
                        <Button size="sm" variant="secondary" onClick={() => processFiles([fileObj.id])}>
                          <Loader2 className="h-3 w-3 mr-1" /> Process
                        </Button>
                      )}
                      {fileObj.uploaded && !fileObj.processing && !fileObj.error && (
                        <Badge variant="success" className="text-xs">Ready</Badge>
                      )}
                      <Button size="icon" variant="ghost" onClick={() => removeFile(fileObj.id)} aria-label={`Remove ${fileObj.name}`}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function FilePreviewGrid({ files, onRemove, className }) {
  return (
    <div className={`grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 ${className || ''}`}>
      {files.map((fileObj) => {
        const status = getFileStatus(fileObj)
        return (
          <div key={fileObj.id} className="relative group p-3 bg-muted/50 rounded-lg border">
            <div className="aspect-square flex items-center justify-center bg-background rounded mb-2">
              {getFileIcon(fileObj.type)}
            </div>
            <p className="text-xs font-medium truncate mb-1" title={fileObj.name}>{fileObj.name}</p>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{formatFileSize(fileObj.size)}</span>
              {/* FIXED: Changed <status.icon /> to {status.icon} since it's an element, not a component type */}
              <span className={`flex items-center gap-1 ${status.class}`}>
                {status.icon} {status.label}
              </span>
            </div>
            {(fileObj.uploading || fileObj.processing) && (
              <Progress value={fileObj.progress} className="absolute bottom-0 left-0 right-0 h-1 rounded-b-lg" />
            )}
            <Button
              size="icon"
              variant="ghost"
              className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => onRemove?.(fileObj.id)}
              aria-label={`Remove ${fileObj.name}`}
            >
              <X className="h-3 w-3 text-muted-foreground" />
            </Button>
          </div>
        )
      })}
    </div>
  )
}
