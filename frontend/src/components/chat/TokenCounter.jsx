import React from 'react'
import { cn } from '@/lib/utils'
import { Zap, Loader2 } from 'lucide-react'

export function TokenCounter({ 
  inputTokens = 0, 
  outputTokens = 0, 
  totalTokens = 0,
  maxTokens = 4096,
  showBreakdown = false,
  className 
}) {
  const usagePercent = maxTokens > 0 ? Math.min((totalTokens / maxTokens) * 100, 100) : 0
  const isHighUsage = usagePercent > 80
  const isCriticalUsage = usagePercent > 95

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Zap className="h-3 w-3" aria-hidden="true" />
        <span className={cn('font-mono font-medium', isCriticalUsage && 'text-orange-500', isHighUsage && !isCriticalUsage && 'text-yellow-500')}>
          {formatNumber(totalTokens)} tokens
        </span>
        {showBreakdown && (
          <>
            <span className="text-muted-foreground/50">·</span>
            <span className="text-muted-foreground">in: {formatNumber(inputTokens)}</span>
            <span className="text-muted-foreground">out: {formatNumber(outputTokens)}</span>
          </>
        )}
      </div>
      
      <div className="relative w-24 h-1.5 bg-accent rounded-full overflow-hidden" role="progressbar" aria-valuenow={usagePercent} aria-valuemin={0} aria-valuemax={100} aria-label="Token usage">
        <div 
          className={cn(
            'h-full rounded-full transition-all duration-300',
            isCriticalUsage ? 'bg-red-500' : isHighUsage ? 'bg-yellow-500' : 'bg-primary'
          )}
          style={{ width: `${usagePercent}%` }}
        />
      </div>

      {isHighUsage && (
        <span className="text-xs text-orange-500 font-medium">
          {isCriticalUsage ? 'Limit reached' : 'Near limit'}
        </span>
      )}
    </div>
  )
}

export function StreamingTokenCounter({ 
  tokens = 0, 
  isStreaming = false,
  className 
}) {
  return (
    <div className={cn('flex items-center gap-1.5 text-xs text-muted-foreground', className)}>
      <span className="font-mono font-medium">{formatNumber(tokens)} tokens</span>
      {isStreaming && (
        <Loader2 className="h-3 w-3 animate-spin text-primary" aria-hidden="true" />
      )}
    </div>
  )
}

function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}