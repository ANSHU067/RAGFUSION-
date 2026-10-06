import { useRef, useEffect } from 'react'
import { Mic, Plus, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export function PromptInput({ value, onChange, onSubmit, disabled = false, maxLength = 4000, autoFocus = false }) {
  const input = useRef(null)
  useEffect(() => { if (autoFocus && !disabled) input.current?.focus() }, [autoFocus, disabled])
  const submit = (event) => {
    event.preventDefault()
    if (!disabled && value.trim() && value.length <= maxLength) onSubmit(value.trim())
  }
  return <form onSubmit={submit} className="flex w-full items-end gap-1 rounded-[1.5rem] bg-card/90 px-1.5 py-1 dark:bg-[#212121]">
    <Button type="button" variant="ghost" size="icon" aria-label="Add attachment" title="Attachments are unavailable" className="mb-1 size-9 shrink-0 rounded-full text-muted-foreground" disabled>
      <Plus aria-hidden="true" className="size-5" />
    </Button>
    <Textarea ref={input} aria-label="Chat message" value={value} onChange={(event) => onChange(event.target.value)} maxLength={maxLength} disabled={disabled} placeholder="Message RAGFUSION…" className="max-h-40 min-h-11 resize-none overflow-y-auto rounded-2xl border-0 bg-transparent px-2.5 py-3 text-sm shadow-none focus-visible:ring-0" onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) submit(event) }} />
    <div className="mb-1 flex shrink-0 items-center gap-0.5">
      <span className="hidden rounded-full px-2 text-[11px] text-muted-foreground sm:inline" aria-label="Active model">RAGFUSION</span>
      <Button type="button" variant="ghost" size="icon" aria-label="Voice input" title="Voice input is unavailable" className="size-9 rounded-full text-muted-foreground" disabled>
        <Mic aria-hidden="true" className="size-4" />
      </Button>
      <Button type="submit" size="icon" aria-label="Send message" className="size-10 rounded-full transition-transform hover:scale-105" disabled={disabled || !value.trim() || value.length > maxLength}><Send aria-hidden="true" className="size-4" /></Button>
    </div>
  </form>
}
