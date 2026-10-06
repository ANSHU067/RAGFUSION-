// Older API versions emitted naive UTC strings. Treat those as UTC explicitly;
// never let the browser interpret them as local wall-clock timestamps.
export function parseTimestamp(value) {
  if (value === null || value === undefined || value === '') return null
  let normalized = value
  if (typeof value === 'string') {
    const parts = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/)
    if (!parts) return null
    const [, year, month, day, hour, minute] = parts.map(Number)
    if (month < 1 || month > 12 || day < 1 || day > new Date(Date.UTC(year, month, 0)).getUTCDate() || hour > 23 || minute > 59) return null
    if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(value)) normalized = value + 'Z'
  } else if (typeof value !== 'number' && !(value instanceof Date)) return null
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatMessageTimestamp(value, now = new Date(), locale) {
  const date = parseTimestamp(value)
  if (!date) return { label: 'Just now', dateTime: undefined, title: undefined }
  const today = date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()
  const options = { hour: 'numeric', minute: '2-digit' }
  if (!today) { options.month = 'short'; options.day = 'numeric' }
  if (date.getFullYear() !== now.getFullYear()) options.year = 'numeric'
  return { label: new Intl.DateTimeFormat(locale, options).format(date), dateTime: date.toISOString(), title: date.toLocaleString(locale) }
}
