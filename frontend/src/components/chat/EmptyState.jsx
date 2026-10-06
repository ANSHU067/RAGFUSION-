import React from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { MessageSquare, Search, Upload, Sparkles, HelpCircle, ArrowRight, BookOpen, Zap } from 'lucide-react'

export function EmptyState({ 
  variant = 'default',
  title, 
  description, 
  action,
  secondaryAction,
  className,
  illustration
}) {
  const variants = {
    default: {
      icon: MessageSquare,
      title: 'Start a conversation',
      description: 'Ask questions about your documents, get summaries, or explore your knowledge base.',
      illustration: (
        <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
          <MessageSquare className="h-12 w-12 text-primary/60" />
        </div>
      ),
    },
    search: {
      icon: Search,
      title: 'No results found',
      description: 'Try adjusting your search terms or filters to find what you\'re looking for.',
      illustration: (
        <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-muted/50 to-muted/20 flex items-center justify-center">
          <Search className="h-12 w-12 text-muted-foreground/50" />
        </div>
      ),
    },
    upload: {
      icon: Upload,
      title: 'No documents yet',
      description: 'Upload your first document to start building your knowledge base.',
      illustration: (
        <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-green-500/20 to-green-500/5 flex items-center justify-center">
          <Upload className="h-12 w-12 text-green-500/60" />
        </div>
      ),
    },
    welcome: {
      icon: Sparkles,
      title: 'Welcome to RAGFUSION',
      description: 'Your AI-powered document workspace. Upload documents, ask questions, and get instant answers with citations.',
      illustration: (
        <div className="w-28 h-28 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-primary/20 via-purple-500/20 to-pink-500/20 flex items-center justify-center">
          <Sparkles className="h-14 w-14 text-primary/60" />
        </div>
      ),
    },
    error: {
      icon: HelpCircle,
      title: 'Something went wrong',
      description: 'We encountered an error. Please try again or contact support if the problem persists.',
      illustration: (
        <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-destructive/20 to-destructive/5 flex items-center justify-center">
          <HelpCircle className="h-12 w-12 text-destructive/60" />
        </div>
      ),
    },
    noChats: {
      icon: BookOpen,
      title: 'No chats yet',
      description: 'Start your first conversation by asking a question or creating a new chat.',
      illustration: (
        <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-500/5 flex items-center justify-center">
          <BookOpen className="h-12 w-12 text-blue-500/60" />
        </div>
      ),
    },
    noWorkspace: {
      icon: Zap,
      title: 'No workspace selected',
      description: 'Create or select a workspace to start chatting with your documents.',
      illustration: (
        <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-yellow-500/20 to-yellow-500/5 flex items-center justify-center">
          <Zap className="h-12 w-12 text-yellow-500/60" />
        </div>
      ),
    },
  }

  const config = variants[variant] || variants.default

  return (
    <div className={cn(
      'flex flex-col items-center justify-center text-center py-16 px-4',
      className
    )}>
      {illustration || config.illustration}
      
      <h3 className="text-xl font-semibold text-foreground mb-2">
        {title || config.title}
      </h3>
      
      <p className="text-muted-foreground max-w-sm mb-6 leading-relaxed">
        {description || config.description}
      </p>

      {(action || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full max-w-sm">
          {action && (
            <Button 
              onClick={action.onClick}
              className="w-full sm:w-auto gap-2"
              size="lg"
            >
              {action.label}
              {action.icon && <ArrowRight className="h-4 w-4" />}
            </Button>
          )}
          {secondaryAction && (
            <Button 
              variant="outline" 
              onClick={secondaryAction.onClick}
              className="w-full sm:w-auto"
              size="lg"
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

export function ChatEmptyState({ onNewChat, onUploadDocs }) {
  return (
    <EmptyState
      variant="welcome"
      action={{ label: 'New Chat', onClick: onNewChat, icon: ArrowRight }}
      secondaryAction={{ label: 'Upload Documents', onClick: onUploadDocs }}
    />
  )
}

export function SearchEmptyState({ onClearFilters }) {
  return (
    <EmptyState
      variant="search"
      action={{ label: 'Clear Filters', onClick: onClearFilters }}
    />
  )
}

export function UploadEmptyState({ onUpload }) {
  return (
    <EmptyState
      variant="upload"
      action={{ label: 'Upload Documents', onClick: onUpload, icon: ArrowRight }}
    />
  )
}

export function ErrorEmptyState({ onRetry, onContactSupport }) {
  return (
    <EmptyState
      variant="error"
      action={{ label: 'Try Again', onClick: onRetry, icon: ArrowRight }}
      secondaryAction={{ label: 'Contact Support', onClick: onContactSupport }}
    />
  )
}

export function NoChatsEmptyState({ onNewChat }) {
  return (
    <EmptyState
      variant="noChats"
      action={{ label: 'Start New Chat', onClick: onNewChat, icon: ArrowRight }}
    />
  )
}

export function NoWorkspaceEmptyState({ onCreateWorkspace, onSelectWorkspace }) {
  return (
    <EmptyState
      variant="noWorkspace"
      action={{ label: 'Create Workspace', onClick: onCreateWorkspace, icon: ArrowRight }}
      secondaryAction={{ label: 'Browse Workspaces', onClick: onSelectWorkspace }}
    />
  )
}

export function StarterPrompts({ prompts, onSelect, className }) {
  return (
    <div className={cn('space-y-4', className)}>
      <p className="text-sm font-medium text-muted-foreground">Try asking:</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {prompts.map((prompt, index) => (
          <Button
            key={index}
            variant="outline"
            className="w-full justify-start text-left h-auto py-3 px-4 gap-3 hover:bg-accent hover:border-primary/50 transition-all"
            onClick={() => onSelect(prompt)}
          >
            <span className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
              <MessageSquare className="h-4 w-4 text-primary" />
            </span>
            <span className="text-sm">{prompt}</span>
          </Button>
        ))}
      </div>
    </div>
  )
}
