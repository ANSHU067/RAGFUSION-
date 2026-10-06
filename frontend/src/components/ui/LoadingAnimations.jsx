import * as React from 'react'
import { motion } from 'framer-motion'
import { Brain } from 'lucide-react'

export function Spinner({ size = 24, className = '', color = 'currentColor' }) {
  return (
    <motion.svg
      className={`animate-spin ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ color }}
      role="status"
      aria-label="Loading"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <motion.path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        initial={{ rotate: 0 }}
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        style={{ transformOrigin: '12px 12px' }}
      />
    </motion.svg>
  )
}

export function PulseDots({ count = 3, size = 8, className = '', color = 'currentColor' }) {
  return (
    <div className={`flex items-center gap-1 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className="rounded-full"
          style={{ width: size, height: size, backgroundColor: color }}
          initial={{ scale: 0.5, opacity: 0.5 }}
          animate={{ scale: [0.5, 1, 0.5], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 0.6, delay: i * 0.15, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}
    </div>
  )
}

export function PulseRing({ size = 40, className = '', color = 'currentColor' }) {
  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }} role="status" aria-label="Loading">
      <motion.div
        className="absolute inset-0 rounded-full border-2"
        style={{ borderColor: color }}
        initial={{ scale: 0, opacity: 1 }}
        animate={{ scale: [0, 1], opacity: [1, 0] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
      />
      <motion.div
        className="absolute inset-0 rounded-full border-2"
        style={{ borderColor: color }}
        initial={{ scale: 0, opacity: 1 }}
        animate={{ scale: [0, 1], opacity: [1, 0] }}
        transition={{ duration: 1.5, delay: 0.75, repeat: Infinity, ease: 'easeOut' }}
      />
    </div>
  )
}

export function Skeleton({ className = '', width = '100%', height = '1rem', borderRadius = '0.375rem' }) {
  return (
    <motion.div
      className={className}
      style={{ width, height, borderRadius, background: 'linear-gradient(90deg, var(--muted) 25%, var(--accent) 50%, var(--muted) 75%)', backgroundSize: '200% 100%' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      aria-hidden="true"
    >
      <motion.div
        initial={{ backgroundPosition: '200% 0' }}
        animate={{ backgroundPosition: '-200% 0' }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
        style={{ width: '100%', height: '100%', borderRadius }}
      />
    </motion.div>
  )
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`space-y-4 ${className}`} aria-hidden="true">
      <Skeleton width="40%" height="1.5rem" />
      <Skeleton width="60%" height="1rem" />
      <Skeleton width="80%" height="1rem" />
      <Skeleton width="100%" height="1rem" />
      <Skeleton width="100%" height="1rem" />
    </div>
  )
}

export function SkeletonTable({ rows = 5, columns = 4, className = '' }) {
  return (
    <div className={className} aria-hidden="true">
      <div className="space-y-3">
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton key={i} height="1rem" width="80%" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, row) => (
          <div key={row} className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
            {Array.from({ length: columns }).map((_, i) => (
              <Skeleton key={i} height="1rem" width="90%" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ProcessingSteps({ steps, currentStep = 0, className = '' }) {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-live="polite">
      {steps.map((step, index) => (
        <motion.div
          key={step}
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1, duration: 0.3 }}
        >
          <motion.div
            className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium"
            style={{
              backgroundColor: index < currentStep ? 'var(--primary)' : index === currentStep ? 'var(--primary)' : 'var(--muted)',
              color: index <= currentStep ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
            }}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: index * 0.1, type: 'spring', stiffness: 260, damping: 20 }}
          >
            {index < currentStep ? (
              <motion.svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <motion.path d="M20 6L9 17l-5-5" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.2 }} />
              </motion.svg>
            ) : index === currentStep ? (
              <Spinner size={14} color="var(--primary-foreground)" />
            ) : (
              <span>{index + 1}</span>
            )}
          </motion.div>
          <motion.span
            className="text-sm"
            style={{ color: index <= currentStep ? 'var(--foreground)' : 'var(--muted-foreground)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.1 }}
          >
            {step}
          </motion.span>
          {index === currentStep && (
            <motion.span className="text-xs text-muted-foreground" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ repeat: Infinity, duration: 1 }}>
              Processing...
            </motion.span>
          )}
        </motion.div>
      ))}
    </div>
  )
}

export function AIThinking({ className = '', size = 40 }) {
  return (
    <div className={`flex items-center gap-2 ${className}`} role="status" aria-label="AI is thinking">
      <motion.div
        className="relative"
        style={{ width: size, height: size }}
      >
        <motion.svg
          className="absolute inset-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{ color: 'var(--primary)' }}
        >
          <motion.circle
            cx="12"
            cy="12"
            r="10"
            initial={{ pathLength: 0, rotate: -90 }}
            animate={{ pathLength: 1, rotate: 270 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            style={{ transformOrigin: '12px 12px' }}
          />
        </motion.svg>
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          initial={{ scale: 0, rotate: 0 }}
          animate={{ scale: 1, rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        >
          <Brain className="h-6 w-6" style={{ color: 'var(--primary)' }} />
        </motion.div>
      </motion.div>
      <motion.span
        className="text-sm font-medium"
        initial={{ opacity: 0.5 }}
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        Thinking...
      </motion.span>
    </div>
  )
}

export function ProgressBar({ progress = 0, className = '', showLabel = true, animated = true }) {
  return (
    <div className={`w-full ${className}`} role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Progress">
      <div className="flex items-center justify-between mb-1">
        {showLabel && <span className="text-sm font-medium">Progress</span>}
        {showLabel && <span className="text-sm text-muted-foreground">{Math.round(progress)}%</span>}
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-primary rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: animated ? 0.5 : 0, ease: 'easeOut' }}
          style={{ 
            background: 'linear-gradient(90deg, var(--primary), var(--primary)/70%)',
            backgroundSize: '200% 100%',
          }}
        >
          {animated && (
            <motion.div
              className="absolute inset-0"
              style={{
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
                backgroundSize: '200% 100%',
              }}
              initial={{ backgroundPosition: '200% 0' }}
              animate={{ backgroundPosition: '-200% 0' }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
          )}
        </motion.div>
      </div>
    </div>
  )
}

export function LoadingOverlay({ isVisible = true, message = 'Loading...', className = '' }) {
  if (!isVisible) return null

  return (
    <motion.div
      className={`fixed inset-0 z-50 flex items-center justify-center ${className}`}
      style={{ background: 'rgba(var(--background), 0.8)', backdropFilter: 'blur(4px)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      role="dialog"
      aria-modal="true"
      aria-label={message}
    >
      <motion.div
        className="flex flex-col items-center gap-4 p-6 rounded-xl border border-border bg-background shadow-xl"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 20 }}
      >
        <AIThinking size={60} />
        <p className="text-muted-foreground text-center">{message}</p>
      </motion.div>
    </motion.div>
  )
}