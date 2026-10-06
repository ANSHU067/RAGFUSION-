import { useEffect, useState } from 'react'
import { formatMessageTimestamp } from '@/lib/dates'

export function MessageTimestamp({ value, className }) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(timer)
  }, [])
  const { label, dateTime, title } = formatMessageTimestamp(value, now)
  return <time className={className || 'text-xs text-muted-foreground'} dateTime={dateTime} title={title}>{label}</time>
}
