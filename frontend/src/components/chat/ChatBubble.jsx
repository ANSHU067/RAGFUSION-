import React from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Copy, Loader2, RotateCcw, ThumbsDown, ThumbsUp } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { TokenCounter } from './TokenCounter'
import { MessageTimestamp } from './MessageTimestamp'

export function ChatBubble({ 
  message, 
  isStreaming = false,
  onRegenerate,
  onCopy,
  showTokenCount = false
}) {
  const { role, content, timestamp, citations, tokens, model, status } = message
  const isUser = role === 'user'
  const isAssistant = role === 'assistant'
  const isError = status === 'error'

  const uniqueCitations = [...new Map(
    (citations || []).map((citation, index) => [
      `${citation.source_type || 'source'}:${citation.source_id || index}`,
      citation,
    ])
  ).values()]

  const citationLabel = (citation) => citation.source_name
    || citation.title
    || citation.filename
    || citation.metadata?.title
    || citation.metadata?.filename
    || citation.metadata?.url
    || citation.metadata?.youtube_url
    || 'Unknown source'

  const citationUrl = (citation) => {
    const candidate = citation.url || citation.metadata?.url || citation.metadata?.youtube_url
    if (!candidate) return null
    try {
      const parsed = new URL(candidate)
      return ['http:', 'https:'].includes(parsed.protocol) ? parsed.toString() : null
    } catch {
      return null
    }
  }

  return (
    <article className={cn('mx-auto flex w-full max-w-3xl px-1 sm:px-2', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('flex min-w-0 max-w-[min(88%,42rem)] flex-col', isUser ? 'items-end' : 'items-start')}>
        <div 
          className={cn(
            'relative max-w-full',
            isUser 
              ? 'rounded-3xl bg-muted/70 px-4 py-2.5 text-foreground dark:bg-[#2f2f2f]'
              : 'px-0 py-1'
          )}
        >
          <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
            <MarkdownRenderer content={content} isStreaming={isStreaming} />
          </div>

          {uniqueCitations.length > 0 && (
            <div className="mt-3 pt-1">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Sources</p>
              <div className="flex flex-wrap gap-2">
                {uniqueCitations.map((citation, index) => {
                  const label = citationLabel(citation)
                  const url = citationUrl(citation)
                  return url ? (
                    <a key={`${citation.source_type}:${citation.source_id || index}`} href={url} target="_blank" rel="noreferrer" className="text-[10px] font-medium bg-background border border-border px-2 py-1 rounded-md shadow-sm hover:border-primary/50">
                      {label}
                    </a>
                  ) : (
                    <span key={`${citation.source_type}:${citation.source_id || index}`} className="text-[10px] font-medium bg-background border border-border px-2 py-1 rounded-md shadow-sm">
                      {label}
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          <div className={cn('flex items-center gap-2 mt-2', isUser ? 'justify-end' : 'justify-start')}>
            {isAssistant && showTokenCount && tokens && (
              <TokenCounter 
                inputTokens={tokens.input} 
                outputTokens={tokens.output} 
                totalTokens={tokens.total}
              />
            )}

            {isAssistant && model && (
              <span className="text-xs text-muted-foreground px-2 py-0.5 bg-accent rounded">
                {model}
              </span>
            )}

            {isAssistant && <div className="flex items-center gap-0.5">
              <Button variant="ghost" size="icon" className="size-8 rounded-full text-muted-foreground hover:text-foreground" aria-label="Copy response" onClick={() => onCopy?.(content)}><Copy className="size-3.5" /></Button>
              <Button variant="ghost" size="icon" className="size-8 rounded-full text-muted-foreground hover:text-foreground" aria-label="Good response" title="Feedback is unavailable" disabled><ThumbsUp className="size-3.5" /></Button>
              <Button variant="ghost" size="icon" className="size-8 rounded-full text-muted-foreground hover:text-foreground" aria-label="Poor response" title="Feedback is unavailable" disabled><ThumbsDown className="size-3.5" /></Button>
              {onRegenerate && <Button variant="ghost" size="icon" className="size-8 rounded-full text-muted-foreground hover:text-foreground" aria-label="Regenerate response" onClick={onRegenerate}><RotateCcw className="size-3.5" /></Button>}
            </div>}

            {isError && (
              <Button 
                variant="outline" 
                size="sm" 
                className="text-destructive border-destructive"
                onClick={onRegenerate}
              >
                <Loader2 className="mr-2 h-3.5 w-3.5" />
                Retry
              </Button>
            )}

            {!isUser && <MessageTimestamp value={message.created_at ?? timestamp} className="text-[11px] text-muted-foreground" />}
          </div>
        </div>
      </div>
    </article>
  )
}
