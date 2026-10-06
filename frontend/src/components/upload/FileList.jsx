import { Eye, FileText, MoreVertical, RefreshCw, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu'

// Helper function to map file statuses to Badge variants
const statusVariant = (status) => {
  if (status === 'completed' || status === 'ready') return 'success'
  if (status === 'failed') return 'destructive'
  if (status === 'processing') return 'info'
  return 'secondary'
}

export function FileList({ 
  files = [], 
  onFileSelect, 
  onFileAction, 
  selectedFileIds = [], 
  onSelectionChange, 
  busyFileIds = [],
  className 
}) {
  // Empty State
  if (!files.length) {
    return (
      <Card className={className}>
        <CardContent className="p-10 text-center text-sm text-muted-foreground">
          <FileText className="mx-auto mb-3 size-9 opacity-50" />
          No documents yet. Upload a file to get started.
        </CardContent>
      </Card>
    )
  }

  // Toggle individual file selection
  const toggle = (id) => {
    onSelectionChange?.(
      selectedFileIds.includes(id) 
        ? selectedFileIds.filter((value) => value !== id) 
        : [...selectedFileIds, id]
    )
  }

  return (
    <Card className={className}>
      <CardContent className="p-0">
        <ul className="divide-y">
          {files.map((file) => (
            <li key={file.id} className="flex items-center gap-3 p-4 hover:bg-muted/40">
              
              {/* Checkbox for selection */}
              <input 
                aria-label={`Select ${file.filename || file.name || file.title}`} 
                type="checkbox" 
                checked={selectedFileIds.includes(file.id)} 
                onChange={() => toggle(file.id)} 
                className="size-4 accent-primary" 
              />
              
              <FileText className="size-5 shrink-0 text-primary" />
              
              {/* Clickable file name & size */}
              <button 
                type="button" 
                className="min-w-0 flex-1 text-left" 
                onClick={() => onFileSelect?.(file)}
              >
                <p className="truncate font-medium">
                  {file.filename || file.name || file.title || 'Untitled document'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {file.size ? `${Math.round(file.size / 1024)} KB` : 'Document'}
                </p>
              </button>
              
              {/* Status Badge */}
              <Badge variant={statusVariant(file.status)}>
                {file.status || 'pending'}
              </Badge>
              
              {/* Actions Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    aria-label={`Actions for ${file.filename || file.name || file.title}`}
                  >
                    <MoreVertical className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                
                <DropdownMenuContent align="end">
                  <DropdownMenuItem disabled={busyFileIds.includes(file.id)} onClick={() => onFileAction?.('preview', file)}>
                    <Eye className="mr-2 size-4" />
                    Preview
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem disabled={busyFileIds.includes(file.id)} onClick={() => onFileAction?.('retry', file)}>
                    <RefreshCw className="mr-2 size-4" />
                    Process
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem 
                    className="text-destructive focus:text-destructive" 
                    disabled={busyFileIds.includes(file.id)}
                    onClick={() => onFileAction?.('delete', file)}
                  >
                    <Trash2 className="mr-2 size-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

export const DocumentTable = FileList
