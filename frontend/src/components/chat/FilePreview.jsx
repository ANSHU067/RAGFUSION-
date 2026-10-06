import React from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileText, Image, Video, Download, X, ZoomIn, FileType, Music } from 'lucide-react'

const fileTypeConfig = {
  pdf: { icon: FileText, color: 'text-red-500', bg: 'bg-red-500/10', label: 'PDF' },
  doc: { icon: FileText, color: 'text-blue-500', bg: 'bg-blue-500/10', label: 'Word' },
  docx: { icon: FileText, color: 'text-blue-500', bg: 'bg-blue-500/10', label: 'Word' },
  txt: { icon: FileText, color: 'text-gray-500', bg: 'bg-gray-500/10', label: 'Text' },
  md: { icon: FileText, color: 'text-gray-500', bg: 'bg-gray-500/10', label: 'Markdown' },
  jpg: { icon: Image, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Image' },
  jpeg: { icon: Image, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Image' },
  png: { icon: Image, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Image' },
  gif: { icon: Image, color: 'text-green-500', bg: 'bg-green-500/10', label: 'GIF' },
  webp: { icon: Image, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Image' },
  mp4: { icon: Video, color: 'text-purple-500', bg: 'bg-purple-500/10', label: 'Video' },
  webm: { icon: Video, color: 'text-purple-500', bg: 'bg-purple-500/10', label: 'Video' },
  mov: { icon: Video, color: 'text-purple-500', bg: 'bg-purple-500/10', label: 'Video' },
  mp3: { icon: Music, color: 'text-orange-500', bg: 'bg-orange-500/10', label: 'Audio' },
  wav: { icon: Music, color: 'text-orange-500', bg: 'bg-orange-500/10', label: 'Audio' },
  ogg: { icon: Music, color: 'text-orange-500', bg: 'bg-orange-500/10', label: 'Audio' },
}

function getFileConfig(filename) {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  return fileTypeConfig[ext] || { icon: FileType, color: 'text-muted-foreground', bg: 'bg-muted', label: ext.toUpperCase() || 'FILE' }
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function FilePreview({ 
  file, 
  url, 
  onRemove, 
  onDownload,
  onOpen,
  className,
  variant = 'card',
  isLoading = false
}) {
  const config = getFileConfig(file.name)
  const Icon = config.icon
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].some(ext => file.name.toLowerCase().endsWith(ext))
  const isPdf = file.name.toLowerCase().endsWith('.pdf')

  if (variant === 'inline') {
    return (
      <div className={cn('flex items-center gap-3 p-2 bg-accent/50 rounded-lg border', className)}>
        <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', config.bg)}>
          <Icon className={cn('h-5 w-5', config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{file.name}</p>
          <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
        </div>
        <div className="flex items-center gap-1">
          {onDownload && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onDownload} aria-label="Download">
              <Download className="h-3.5 w-3.5" />
            </Button>
          )}
          {onOpen && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onOpen} aria-label="Open">
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
          )}
          {onRemove && (
            <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive" onClick={onRemove} aria-label="Remove">
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={cn('relative group', className)}>
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        {isImage && url && (
          <div className="relative aspect-video overflow-hidden bg-muted">
            <img 
              src={url} 
              alt={file.name}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="absolute bottom-3 left-3 right-3 flex justify-between">
                <div className="flex gap-2">
                  <Button variant="default" size="sm" className="gap-1" onClick={onDownload}>
                    <Download className="h-3.5 w-3.5" />
                    <span>Download</span>
                  </Button>
                  <Button variant="default" size="sm" className="gap-1" onClick={() => window.open(url, '_blank')}>
                    <ZoomIn className="h-3.5 w-3.5" />
                    <span>View</span>
                  </Button>
                </div>
                {onRemove && (
                  <Button variant="destructive" size="icon" className="h-8 w-8" onClick={onRemove} aria-label="Remove file">
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {!isImage && (
          <div className="aspect-video flex flex-col items-center justify-center p-6 bg-muted/50">
            <div className={cn('w-20 h-20 rounded-2xl flex items-center justify-center mb-4', config.bg)}>
              <Icon className={cn('h-10 w-10', config.color)} />
            </div>
            <p className="text-lg font-medium text-center truncate w-full px-4">{file.name}</p>
            <p className="text-sm text-muted-foreground mt-1">{formatFileSize(file.size)}</p>
          </div>
        )}

        <div className="p-4 border-t border-border bg-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={cn(config.bg, config.color)}>
                {config.label}
              </Badge>
              <span className="text-sm text-muted-foreground">{formatFileSize(file.size)}</span>
            </div>
            <div className="flex items-center gap-2">
              {isPdf && url && (
                <Button variant="outline" size="sm" className="gap-1" onClick={() => window.open(url, '_blank')}>
                  <FileText className="h-3.5 w-3.5" />
                  Open PDF
                </Button>
              )}
              {onDownload && (
                <Button variant="outline" size="sm" className="gap-1" onClick={onDownload}>
                  <Download className="h-3.5 w-3.5" />
                  Download
                </Button>
              )}
              {onRemove && (
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10" onClick={onRemove} aria-label="Remove file">
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-xl">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      )}
    </div>
  )
}

export function FilePreviewGrid({ 
  files, 
  onRemove, 
  onDownload,
  onOpen,
  className,
  maxPreview = 6
}) {
  const displayFiles = files.slice(0, maxPreview)
  const remaining = files.length - maxPreview

  return (
    <div className={cn('grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3', className)}>
      {displayFiles.map((file, index) => (
        <FilePreview
          key={`${file.name}-${index}`}
          file={file}
          url={file.url || file.preview}
          onRemove={() => onRemove?.(file, index)}
          onDownload={() => onDownload?.(file)}
          onOpen={() => onOpen?.(file)}
          variant="card"
        />
      ))}
      {remaining > 0 && (
        <div className="col-span-2 sm:col-span-3 lg:col-span-4 xl:col-span-6 flex items-center justify-center bg-accent/50 border border-border rounded-xl p-6">
          <Button variant="outline" onClick={() => {}} className="w-full">
            <span className="font-medium">+{remaining} more files</span>
          </Button>
        </div>
      )}
    </div>
  )
}

export function FileDropZone({ 
  onFilesSelected, 
  accept = '.pdf,.txt,.md,.doc,.docx,.jpg,.jpeg,.png,.gif,.webp',
  multiple = true,
  maxFiles = 10,
  maxSize = 50 * 1024 * 1024,
  className,
  children
}) {
  const [isDragging, setIsDragging] = React.useState(false)
  const fileInputRef = React.useRef(null)

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      validateAndAddFiles(files)
    }
  }

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      validateAndAddFiles(files)
    }
    e.target.value = ''
  }

  const validateAndAddFiles = (files) => {
    const validFiles = files
      .slice(0, maxFiles)
      .filter(file => {
        if (file.size > maxSize) {
          return false
        }
        return true
      })
    
    if (validFiles.length > 0) {
      onFilesSelected(validFiles)
    }
  }

  const openFileDialog = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className={cn('relative', className)}>
      <input
        ref={fileInputRef}
        type="file"
        multiple={multiple}
        accept={accept}
        onChange={handleFileSelect}
        className="hidden"
        id="file-drop-input"
      />
      
      <label 
        htmlFor="file-drop-input"
        className={cn(
          'flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all',
          isDragging 
            ? 'border-primary bg-primary/5' 
            : 'border-border hover:border-primary/50 hover:bg-accent/50'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        {children || (
          <>
            <div className={cn('w-16 h-16 rounded-full flex items-center justify-center mb-4', isDragging ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground')}>
              <FileText className="h-8 w-8" />
            </div>
            <p className="text-lg font-medium text-center mb-1">
              {isDragging ? 'Drop files here' : 'Drag & drop files here, or click to browse'}
            </p>
            <p className="text-sm text-muted-foreground text-center max-w-md">
              Supports PDF, DOC, TXT, MD, images, and more. Max {formatFileSize(maxSize)} per file.
            </p>
          </>
        )}
      </label>
    </div>
  )
}
