import React from 'react'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'

export function ChatWindow({ 
  children, 
  className, 
  autoScroll = true,
  onScrollEnd 
}) {
  const scrollAreaRef = React.useRef(null)
  const endRef = React.useRef(null)

  const scrollToBottom = React.useCallback(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({ top: scrollAreaRef.current.scrollHeight, behavior: 'smooth' })
    }
  }, [])

  React.useEffect(() => {
    if (autoScroll) {
      scrollToBottom()
    }
  }, [children, autoScroll, scrollToBottom])

  return (
    <ScrollArea 
      ref={scrollAreaRef}
      className={cn('flex-1 h-full w-full', className)}
      onScroll={onScrollEnd}
    >
      <div className="flex flex-col gap-4 p-4">
        {children}
        <div ref={endRef} />
      </div>
    </ScrollArea>
  )
}
