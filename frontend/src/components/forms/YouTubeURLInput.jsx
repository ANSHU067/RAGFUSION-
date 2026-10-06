import { useState, useCallback } from 'react'
import { Video, AlertCircle, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const YOUTUBE_REGEX = /^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})(?:\S*)?$/

export function YouTubeURLInput({ value, onChange, onSubmit, disabled, error, ...props }) {
  const [validationError, setValidationError] = useState('')
  const [videoId, setVideoId] = useState('')

  const validateUrl = useCallback((url) => {
    if (!url.trim()) return ''
    const match = url.match(YOUTUBE_REGEX)
    if (!match) {
      return 'Please enter a valid YouTube URL (e.g., https://youtube.com/watch?v=...)'
    }
    return ''
  }, [])

  const extractVideoId = useCallback((url) => {
    const match = url.match(YOUTUBE_REGEX)
    return match ? match[1] : null
  }, [])

  const handleChange = (e) => {
    const val = e.target.value
    onChange?.(val)
    const extracted = extractVideoId(val)
    if (extracted !== videoId) setVideoId(extracted)
    const err = validateUrl(val)
    if (err !== validationError) setValidationError(err)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const err = validateUrl(value)
    if (err) {
      setValidationError(err)
      return
    }
    onSubmit?.(value)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const hasError = error || validationError

  return (
    <form onSubmit={handleSubmit} className="space-y-3" {...props}>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Video className="h-5 w-5 text-red-500" aria-hidden="true" />
        </div>
        <Input
          type="url"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="https://youtube.com/watch?v=... or https://youtu.be/..."
          disabled={disabled || hasError}
          className="pl-10 pr-10"
          aria-invalid={hasError ? 'true' : 'false'}
          aria-describedby={hasError ? 'yt-error' : validationError ? 'yt-validation' : videoId ? 'yt-valid' : undefined}
        />
        {hasError && (
          <AlertCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-destructive" aria-hidden="true" />
        )}
        {videoId && !hasError && (
          <CheckCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-emerald-500" aria-hidden="true" />
        )}
      </div>
      {validationError && (
        <p id="yt-validation" className="text-sm text-destructive" role="alert">
          {validationError}
        </p>
      )}
      {videoId && !hasError && !validationError && (
        <p id="yt-valid" className="text-sm text-emerald-500" role="status">
          Valid YouTube video detected
        </p>
      )}
      {error && (
        <p id="yt-error" className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <Button type="submit" disabled={disabled || hasError || !value.trim()} className="w-full">
        Index video
      </Button>
    </form>
  )
}