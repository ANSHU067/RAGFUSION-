import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatDistanceToNow(value, { addSuffix = false } = {}) {
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  const units = [
    ['year', 31536000],
    ['month', 2592000],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
    ['second', 1],
  ]
  const [unit, seconds] = units.find(([, interval]) => elapsedSeconds >= interval) ?? units[units.length - 1]
  const amount = Math.floor(elapsedSeconds / seconds)
  const label = `${amount} ${unit}${amount === 1 ? '' : 's'}`

  return addSuffix ? `${label} ago` : label
}
