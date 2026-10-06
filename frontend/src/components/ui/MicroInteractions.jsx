import * as React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, Copy } from 'lucide-react'

export function RippleEffect({ children, color = 'currentColor', ...props }) {
  const [ripples, setRipples] = React.useState([])

  const handleClick = (event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const ripple = {
      id: Date.now(),
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }
    setRipples((prev) => [...prev, ripple])
    setTimeout(() => {
      setRipples((prev) => prev.filter((r) => r.id !== ripple.id))
    }, 600)
  }

  return (
    <div onClick={handleClick} {...props} style={{ position: 'relative', overflow: 'hidden', ...props.style }}>
      {children}
      <AnimatePresence>
        {ripples.map((ripple) => (
          <motion.div
            key={ripple.id}
            className="absolute rounded-full pointer-events-none"
            style={{
              left: ripple.x,
              top: ripple.y,
              width: 0,
              height: 0,
              backgroundColor: color,
              opacity: 0.3,
              transform: 'translate(-50%, -50%)',
            }}
            initial={{ scale: 0, opacity: 0.3 }}
            animate={{ scale: 20, opacity: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}

export function ToggleSwitch({ checked, onChange, disabled = false, className = '', size = 'md', ...props }) {
  const sizes = {
    sm: { track: 'w-8 h-4', thumb: 'w-3 h-3', translate: 'translate-x-4' },
    md: { track: 'w-11 h-6', thumb: 'w-5 h-5', translate: 'translate-x-5' },
    lg: { track: 'w-14 h-7', thumb: 'w-6 h-6', translate: 'translate-x-7' },
  }

  const { track, thumb, translate } = sizes[size]

  return (
    <motion.button
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative inline-flex items-center ${className}`}
      style={{ ...props.style }}
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      {...props}
    >
      <motion.div
        className={`${track} rounded-full border-2 transition-colors`}
        style={{
          backgroundColor: checked ? 'var(--primary)' : 'var(--muted)',
          borderColor: checked ? 'var(--primary)' : 'var(--border)',
        }}
        animate={{
          backgroundColor: checked ? 'var(--primary)' : 'var(--muted)',
          borderColor: checked ? 'var(--primary)' : 'var(--border)',
        }}
        transition={{ duration: 0.2 }}
      >
        <motion.div
          className={`${thumb} rounded-full bg-background shadow-lg flex items-center justify-center`}
          animate={{ x: checked ? translate : 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        >
          <AnimatePresence mode="wait">
            {checked ? (
              <motion.svg
                key="check"
                className="h-3 w-3 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                initial={{ pathLength: 0, scale: 0 }}
                animate={{ pathLength: 1, scale: 1 }}
                exit={{ pathLength: 0, scale: 0 }}
                transition={{ duration: 0.2 }}
              >
                <path d="M20 6L9 17l-5-5" />
              </motion.svg>
            ) : (
              <motion.div key="empty" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }} />
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </motion.button>
  )
}

export function CopyButton({ text, onCopy, className = '', ...props }) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    onCopy?.(text)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <motion.button
      onClick={handleCopy}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${className}`}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      {...props}
    >
      <AnimatePresence mode="wait">
        {copied ? (
          <motion.div
            key="copied"
            initial={{ scale: 0, rotate: -90 }}
            animate={{ scale: 1, rotate: 0 }}
            exit={{ scale: 0, rotate: 90 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            className="text-green-500"
          >
            <Check className="h-4 w-4" />
          </motion.div>
        ) : (
          <motion.div
            key="copy"
            initial={{ scale: 0, rotate: 90 }}
            animate={{ scale: 1, rotate: 0 }}
            exit={{ scale: 0, rotate: -90 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            className="text-muted-foreground"
          >
            <Copy className="h-4 w-4" />
          </motion.div>
        )}
      </AnimatePresence>
      <span>{copied ? 'Copied!' : 'Copy'}</span>
    </motion.button>
  )
}

export function LikeButton({ liked, onLike, count = 0, className = '', ...props }) {
  return (
    <motion.button
      onClick={() => onLike(!liked)}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-colors ${liked ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent hover:text-foreground'} ${className}`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      {...props}
    >
      <AnimatePresence mode="wait">
        {liked ? (
          <motion.svg
            key="liked"
            className="h-5 w-5 fill-current"
            viewBox="0 0 24 24"
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            exit={{ scale: 0, rotate: 180 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 1 0 7.78L12 21.59l-8.84-9.2a5.5 5.5 0 0 1 0-7.78 5.5 5.5 0 0 1 7.78 0L12 10.59l8.84-5.98a5.5 5.5 0 0 1 7.78 0z" />
          </motion.svg>
        ) : (
          <motion.svg
            key="unliked"
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            initial={{ scale: 0, rotate: 180 }}
            animate={{ scale: 1, rotate: 0 }}
            exit={{ scale: 0, rotate: -180 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 1 0 7.78L12 21.59l-8.84-9.2a5.5 5.5 0 0 1 0-7.78 5.5 5.5 0 0 1 7.78 0L12 10.59l8.84-5.98a5.5 5.5 0 0 1 7.78 0z" />
          </motion.svg>
        )}
      </AnimatePresence>
      <motion.span
        key={count}
        className="text-sm font-medium tabular-nums"
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -10, opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        {count}
      </motion.span>
    </motion.button>
  )
}

export function ExpandableCard({ title, children, defaultExpanded = false, className = '', ...props }) {
  const [expanded, setExpanded] = React.useState(defaultExpanded)

  return (
    <motion.div
      className={`rounded-xl border border-border bg-card overflow-hidden ${className}`}
      {...props}
    >
      <motion.button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-accent/50 transition-colors"
        whileHover={{ x: 4 }}
        whileTap={{ scale: 0.99 }}
      >
        <span className="font-medium text-foreground">{title}</span>
        <motion.svg
          className="h-5 w-5 text-muted-foreground flex-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <path d="M6 9l6 6 6-6" />
        </motion.svg>
      </motion.button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="px-6 pb-4 border-t border-border"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function TooltipTrigger({ children, content, position = 'top', className = '', ...props }) {
  const [visible, setVisible] = React.useState(false)
  const triggerRef = React.useRef(null)
  const tooltipRef = React.useRef(null)

  return (
    <div className="relative inline-block" {...props}>
      <motion.div
        ref={triggerRef}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className={className}
        whileHover={{ scale: 1.02 }}
      >
        {children}
      </motion.div>
      <AnimatePresence>
        {visible && (
          <motion.div
            ref={tooltipRef}
            className="absolute z-50 px-3 py-2 text-xs font-medium text-popover-foreground bg-popover rounded-md shadow-lg border border-border pointer-events-none"
            style={{
              [position === 'top' || position === 'bottom' ? 'left' : 'top']: '50%',
              [position === 'top' || position === 'bottom' ? 'transform' : '']: position === 'top' || position === 'bottom' ? 'translateX(-50%)' : 'translateY(-50%)',
              [position === 'top' ? 'bottom' : position === 'bottom' ? 'top' : position === 'left' ? 'right' : 'left']: '100%',
              margin: position === 'top' ? '0 0 8px' : position === 'bottom' ? '8px 0 0' : position === 'left' ? '0 8px 0 0' : '0 0 0 8px',
            }}
            initial={{ opacity: 0, [position === 'top' || position === 'bottom' ? 'y' : 'x']: position === 'top' ? 8 : position === 'bottom' ? -8 : position === 'left' ? 8 : -8 }}
            animate={{ opacity: 1, [position === 'top' || position === 'bottom' ? 'y' : 'x']: 0 }}
            exit={{ opacity: 0, [position === 'top' || position === 'bottom' ? 'y' : 'x']: position === 'top' ? -8 : position === 'bottom' ? 8 : position === 'left' ? -8 : 8 }}
            transition={{ duration: 0.15 }}
            role="tooltip"
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function AnimatedCounter({ value, duration = 1, className = '', ...props }) {
  const [displayValue, setDisplayValue] = React.useState(0)

  React.useEffect(() => {
    let startTime = null
    let animationFrameId = null
    const startValue = displayValue
    const endValue = value

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayValue(Math.round(startValue + (endValue - startValue) * eased))
      if (progress < 1) {
        animationFrameId = requestAnimationFrame(animate)
      }
    }

    animationFrameId = requestAnimationFrame(animate)
    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId)
    }
  }, [value, duration, displayValue])

  return (
    <motion.span
      className={className}
      {...props}
    >
      {displayValue.toLocaleString()}
    </motion.span>
  )
}

export function StaggeredList({ items, children, delay = 0.1, className = '', ...props }) {
  return (
    <motion.ul
      className={className}
      {...props}
      initial="hidden"
      animate="show"
      variants={{
        hidden: { opacity: 0 },
        show: {
          opacity: 1,
          transition: { staggerChildren: delay },
        },
      }}
    >
      {items.map((item, index) => (
        <motion.li
          key={item.id || index}
          variants={{
            hidden: { opacity: 0, x: -20 },
            show: { opacity: 1, x: 0, transition: { duration: 0.3, ease: 'easeOut' } },
          }}
        >
          {children(item, index)}
        </motion.li>
      ))}
    </motion.ul>
  )
}

export function FocusRing({ children, className = '', ...props }) {
  return (
    <motion.div
      className={`relative ${className}`}
      {...props}
      whileFocus={{
        boxShadow: '0 0 0 3px var(--ring)',
        transition: { duration: 0.15 },
      }}
    >
      {children}
    </motion.div>
  )
}

export function DraggableItem({ children, onDragEnd, className = '', ...props }) {
  const [isDragging, setIsDragging] = React.useState(false)
  const [dragPosition, setDragPosition] = React.useState({ x: 0, y: 0 })

  const handleDragStart = (e) => {
    setIsDragging(true)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDrag = (e) => {
    setDragPosition({ x: e.clientX, y: e.clientY })
  }

  const handleDragEnd = (e) => {
    setIsDragging(false)
    setDragPosition({ x: 0, y: 0 })
    onDragEnd?.(e)
  }

  return (
    <motion.div
      draggable
      onDragStart={handleDragStart}
      onDrag={handleDrag}
      onDragEnd={handleDragEnd}
      className={className}
      {...props}
      animate={{
        x: isDragging ? dragPosition.x : 0,
        y: isDragging ? dragPosition.y : 0,
        scale: isDragging ? 1.05 : 1,
        boxShadow: isDragging ? '0 20px 40px rgba(0,0,0,0.2)' : 'none',
        zIndex: isDragging ? 100 : 1,
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      whileDrag={{ cursor: 'grabbing' }}
    >
      {children}
    </motion.div>
  )
}