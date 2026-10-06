import * as React from 'react'
import { motion } from 'framer-motion'

export function HoverLift({ children, lift = -4, scale = 1.02, ...props }) {
  return (
    <motion.div
      whileHover={{ y: lift, scale, transition: { duration: 0.2, ease: 'easeOut' } }}
      whileTap={{ scale: 0.98 }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function HoverScale({ children, scale = 1.05, ...props }) {
  return (
    <motion.div
      whileHover={{ scale, transition: { duration: 0.2, ease: 'easeOut' } }}
      whileTap={{ scale: 0.95 }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function HoverGlow({ children, color = 'var(--primary)', ...props }) {
  return (
    <motion.div
      whileHover={{
        boxShadow: `0 0 30px ${color}`,
        transition: { duration: 0.3, ease: 'easeOut' },
      }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function HoverRotate({ children, rotate = 3, ...props }) {
  return (
    <motion.div
      whileHover={{ rotate, transition: { duration: 0.2, ease: 'easeOut' } }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function HoverShine({ children, ...props }) {
  return (
    <motion.div
      initial={{ backgroundPosition: '-200% 0' }}
      whileHover={{ backgroundPosition: '200% 0', transition: { duration: 0.6, ease: 'easeOut' } }}
      style={{
        background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)',
        backgroundSize: '200% 100%',
        ...props.style,
      }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function MagneticHover({ children, strength = 0.3, ...props }) {
  const ref = React.useRef(null)

  const handleMouseMove = (event) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const x = event.clientX - rect.left - rect.width / 2
    const y = event.clientY - rect.top - rect.height / 2
    ref.current.style.transform = `translate(${x * strength}px, ${y * strength}px)`
  }

  const handleMouseLeave = () => {
    if (ref.current) {
      ref.current.style.transform = 'translate(0, 0)'
    }
  }

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ transition: 'transform 0.3s ease-out', ...props.style }}
      {...props}
    >
      {children}
    </div>
  )
}

export function HoverUnderline({ children, color = 'currentColor', height = 2, ...props }) {
  return (
    <motion.span
      initial={{ width: '0%' }}
      whileHover={{ width: '100%', transition: { duration: 0.3, ease: 'easeOut' } }}
      style={{
        display: 'inline-block',
        position: 'relative',
        ...props.style,
      }}
      {...props}
    >
      {children}
      <motion.div
        layoutId="underline"
        className="absolute bottom-0 left-0 h-0.5 bg-current"
        style={{ height, backgroundColor: color }}
      />
    </motion.span>
  )
}

export function HoverReveal({ children, hiddenContent, direction = 'up', ...props }) {
  const variants = {
    up: { initial: { y: 20, opacity: 0 }, animate: { y: 0, opacity: 1 } },
    down: { initial: { y: -20, opacity: 0 }, animate: { y: 0, opacity: 1 } },
    left: { initial: { x: 20, opacity: 0 }, animate: { x: 0, opacity: 1 } },
    right: { initial: { x: -20, opacity: 0 }, animate: { x: 0, opacity: 1 } },
  }

  const { initial, animate } = variants[direction]

  return (
    <div {...props}>
      {children}
      <motion.div
        initial={initial}
        animate={animate}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        style={{ overflow: 'hidden' }}
      >
        {hiddenContent}
      </motion.div>
    </div>
  )
}