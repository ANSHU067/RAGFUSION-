import React from 'react'
import { cn } from '@/lib/utils'
import { Loader2, Bot } from 'lucide-react'

export function TypingIndicator({ 
  message = 'Thinking...',
  showDots = true,
  className,
  variant = 'default' 
}) {
  const variants = {
    default: 'flex items-center gap-2 text-sm text-muted-foreground',
    inline: 'inline-flex items-center gap-1.5 text-xs text-muted-foreground',
    minimal: 'flex items-center gap-1.5 text-xs text-muted-foreground',
  }

  return (
    <div className={cn(variants[variant], className)}>
      <div className="flex items-center gap-1">
        <Bot className="h-4 w-4 text-primary/70" aria-hidden="true" />
        <span>{message}</span>
        {showDots && (
          <span className="flex gap-0.5 ml-1" aria-hidden="true">
            <DotAnimation delay={0} />
            <DotAnimation delay={150} />
            <DotAnimation delay={300} />
          </span>
        )}
      </div>
    </div>
  )
}

function DotAnimation({ delay }) {
  return (
    <div
      className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce"
      style={{ animationDelay: `${delay}ms` }}
    />
  )
}

export function StreamingIndicator({ 
  className,
  tokenCount = 0,
  model 
}) {
  return (
    <div className={cn('flex items-center gap-2 text-xs text-muted-foreground', className)}>
      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" aria-hidden="true" />
      <span>Generating response...</span>
      {tokenCount > 0 && (
        <span className="font-mono font-medium text-primary">
          {tokenCount} tokens
        </span>
      )}
      {model && (
        <span className="px-1.5 py-0.5 bg-accent rounded text-[10px] uppercase tracking-wider">
          {model}
        </span>
      )}
    </div>
  )
}

export function ThinkingIndicator({ className }) {
  return (
    <div className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
      <div className="flex gap-0.5">
        <ThinkingDot />
        <ThinkingDot delay={100} />
        <ThinkingDot delay={200} />
      </div>
      <span>Analyzing...</span>
    </div>
  )
}

function ThinkingDot({ delay = 0 }) {
  return (
    <div
      className="w-1.5 h-1.5 bg-primary/50 rounded-full"
      style={{
        animation: `pulse 1.5s ease-in-out infinite`,
        animationDelay: `${delay}ms`
      }}
    />
  )
}