import * as React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

export function HoverCard({
  children,
  asChild = false,
  variant = 'default',
  size = 'md',
  className = '',
  onClick,
  onMouseEnter,
  onMouseLeave,
  ...props
}) {
  const variants = {
    default: {
      whileHover: { y: -2, boxShadow: '0 10px 40px rgba(0,0,0,0.1)', transition: { duration: 0.2, ease: 'easeOut' } },
      whileTap: { scale: 0.98 },
    },
    ghost: {
      whileHover: { backgroundColor: 'var(--accent)', transition: { duration: 0.15 } },
      whileTap: { backgroundColor: 'var(--accent)', scale: 0.98 },
    },
    outline: {
      whileHover: { borderColor: 'var(--primary)', boxShadow: '0 0 0 1px var(--primary), 0 10px 40px rgba(0,0,0,0.05)', transition: { duration: 0.2 } },
      whileTap: { scale: 0.98 },
    },
    lift: {
      whileHover: { y: -8, boxShadow: '0 20px 60px rgba(0,0,0,0.15)', transition: { duration: 0.3, ease: 'easeOut' } },
      whileTap: { scale: 0.98, y: -4 },
    },
    scale: {
      whileHover: { scale: 1.02, transition: { duration: 0.2, ease: 'easeOut' } },
      whileTap: { scale: 0.98 },
    },
    glow: {
      whileHover: { boxShadow: '0 0 30px var(--primary)', transition: { duration: 0.3, ease: 'easeOut' } },
      whileTap: { scale: 0.98 },
    },
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
    xl: 'px-8 py-4 text-lg',
    icon: 'p-2',
  }

  const baseStyles = 'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50'

  const variantStyles = {
    default: 'bg-primary text-primary-foreground hover:bg-primary/90',
    ghost: 'bg-transparent hover:bg-accent text-foreground',
    outline: 'border border-border bg-background hover:bg-accent text-foreground',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    none: '',
  }

  const sizeStyles = sizes[size] || sizes.md
  const variantStyle = variantStyles[variant] || variantStyles.default
  const hoverVariant = variants[variant] || variants.default

  const handleClick = (e) => {
    if (onClick) onClick(e)
  }

  const handleMouseEnter = (e) => {
    if (onMouseEnter) onMouseEnter(e)
  }

  const handleMouseLeave = (e) => {
    if (onMouseLeave) onMouseLeave(e)
  }

  if (asChild) {
    return (
      <motion.div
        className={cn(baseStyles, variantStyle, sizeStyles, className)}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        whileHover={hoverVariant.whileHover}
        whileTap={hoverVariant.whileTap}
        {...props}
      >
        {children}
      </motion.div>
    )
  }

  return (
    <motion.button
      type="button"
      className={cn(baseStyles, variantStyle, sizeStyles, className)}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      whileHover={hoverVariant.whileHover}
      whileTap={hoverVariant.whileTap}
      disabled={props.disabled}
      aria-disabled={props.disabled}
      {...props}
    >
      {children}
    </motion.button>
  )
}

export function HoverLink({
  children,
  href,
  variant = 'default',
  size = 'md',
  className = '',
  onClick,
  ...props
}) {
  const variants = {
    default: {
      whileHover: { x: 4, transition: { duration: 0.2, ease: 'easeOut' } },
      whileTap: { scale: 0.98 },
    },
    underline: {
      whileHover: { x: 4, transition: { duration: 0.2, ease: 'easeOut' } },
      whileTap: { scale: 0.98 },
    },
    lift: {
      whileHover: { y: -2, boxShadow: '0 4px 20px rgba(0,0,0,0.1)', transition: { duration: 0.2, ease: 'easeOut' } },
      whileTap: { scale: 0.98 },
    },
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  }

  const baseStyles = 'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'

  const variantStyles = {
    default: 'text-foreground hover:text-primary',
    underline: 'text-foreground hover:text-primary relative after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0 after:bg-primary after:transition-all hover:after:w-full',
    lift: 'bg-card border border-border hover:border-primary/50 text-foreground',
  }

  const sizeStyles = sizes[size] || sizes.md
  const variantStyle = variantStyles[variant] || variantStyles.default
  const hoverVariant = variants[variant] || variants.default

  return (
    <motion.a
      href={href}
      className={cn(baseStyles, variantStyle, sizeStyles, className)}
      onClick={onClick}
      whileHover={hoverVariant.whileHover}
      whileTap={hoverVariant.whileTap}
      {...props}
    >
      {children}
    </motion.a>
  )
}