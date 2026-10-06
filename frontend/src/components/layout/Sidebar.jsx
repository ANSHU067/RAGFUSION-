import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronRight, LayoutDashboard, MessageSquareText, Settings, LogOut, User, X, History, Moon, Sun, Monitor, FileText, Video, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useTheme } from '@/context/ThemeContext'
import { HoverCard } from '@/components/ui'
import { useAuth } from '@/context/AuthContext'
import { avatarColorClass } from '@/lib/profile'

// Helper to extract initials from the user's name
const getInitials = (name) => {
  if (!name) return 'U'
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'History', href: '/dashboard/history', icon: History },
  { name: 'Documents', href: '/documents/reader', icon: FileText },
  { name: 'YouTube', href: '/youtube/reader', icon: Video },
  { name: 'Website', href: '/website/reader', icon: Globe },
  { name: 'Chat', href: '/chat', icon: MessageSquareText },
]

const NavItem = ({ item, isActive, isCollapsed, onClose }) => (
  <motion.div
    layout
    initial={{ opacity: 0, x: isCollapsed ? 0 : -20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: isCollapsed ? 0 : -20 }}
    transition={{ duration: 0.2, ease: 'easeOut' }}
  >
    <HoverCard
      asChild
      variant="none"
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
        isActive
          ? 'bg-secondary text-secondary-foreground shadow-sm' 
          : 'bg-transparent text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
        isCollapsed && 'justify-center px-2'
      )}
      onClick={onClose}
      aria-current={isActive ? 'page' : undefined}
      title={isCollapsed ? item.name : undefined}
    >
      <Link
        to={item.href}
        aria-label={item.name}
        className="flex items-center gap-3 w-full transition-colors inherit-text"
      >
        <motion.span
          className="h-5 w-5 shrink-0 flex items-center justify-center transition-colors"
          initial={{ scale: 0.8, rotate: -10 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          <item.icon className="h-5 w-5" aria-hidden="true" />
        </motion.span>
        <AnimatePresence mode="wait">
          {!isCollapsed && (
            <motion.span
              key="label"
              initial={{ opacity: 0, x: -10, width: 0 }}
              animate={{ opacity: 1, x: 0, width: 'auto' }}
              exit={{ opacity: 0, x: -10, width: 0 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}
            >
              {item.name}
            </motion.span>
          )}
        </AnimatePresence>
      </Link>
    </HoverCard>
  </motion.div>
)

export function Sidebar({ isOpen, onClose }) {
  const location = useLocation()
  const { theme, resolvedTheme, toggleTheme } = useTheme()
  const { user, logout } = useAuth() 
  const [isCollapsed, setIsCollapsed] = useState(false)

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed)
  }

  // Unified the fallback check for the user's name
  const userName =
    user?.display_name ||
    user?.full_name ||
    user?.username ||
    user?.name || 
    'User'

  return (
    <motion.aside
      initial={{ x: isOpen ? 0 : -300 }}
      animate={{ x: isOpen ? 0 : -300 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className={cn(
        'fixed left-0 top-0 z-40 h-screen bg-background border-r border-border flex flex-col text-foreground',
        isCollapsed ? 'w-16' : 'w-64'
      )}
      aria-label="Sidebar navigation"
    >
      {/* Header / Logo */}
      <motion.div
        className={cn('flex items-center justify-between h-16 px-4 border-b border-border', isCollapsed && 'justify-center')}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Link to="/dashboard" className={cn('flex min-w-0 items-center gap-2 overflow-hidden font-bold text-xl text-foreground', isCollapsed && 'justify-center')} aria-label="RAGFUSION Dashboard">
          <motion.span
            className="text-primary"
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.2 }}
          >
            {isCollapsed ? 'RF' : 'RAGFUSION'}
          </motion.span>
        </Link>
        <HoverCard
          asChild
          variant="ghost"
          size="icon"
          className={cn('h-8 w-8 cursor-pointer', isCollapsed && 'hidden lg:flex')}
          onClick={toggleCollapse}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!isCollapsed}
        >
          <motion.button
            className="flex items-center justify-center text-muted-foreground hover:text-foreground"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <motion.span
              animate={{ rotate: isCollapsed ? 180 : 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
            >
              {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </motion.span>
          </motion.button>
        </HoverCard>
      </motion.div>

      {/* Primary Navigation */}
      <motion.nav
        className="flex-1 overflow-y-auto py-4 px-3 space-y-1 bg-transparent"
        aria-label="Main navigation"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.2, staggerChildren: 0.05 }}
      >
        {navigation.map((item) => {
          const isActive = location.pathname === item.href || (item.href !== '/dashboard' && location.pathname.startsWith(item.href))
          return (
            <NavItem
              key={item.name}
              item={item}
              isActive={isActive}
              isCollapsed={isCollapsed}
              onClose={onClose}
            />
          )
        })}
      </motion.nav>

      {/* Divider */}
      <motion.div
        className={cn('border-t border-border mx-3', isCollapsed && 'mx-2')}
        initial={{ opacity: 0, scaleX: 0 }}
        animate={{ opacity: 1, scaleX: 1 }}
        transition={{ duration: 0.3, delay: 0.4 }}
        style={{ transformOrigin: 'left' }}
      />

      {/* Add Workspace / New Chat */}
      <motion.div
        className={cn('p-3 space-y-2 bg-transparent', isCollapsed && 'px-2')}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.5, staggerChildren: 0.1 }}
      >

        <HoverCard
          asChild
          variant="none"
          className={cn('w-full justify-start gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors bg-transparent text-muted-foreground hover:bg-secondary/50 hover:text-foreground', isCollapsed && 'justify-center px-3')}
        >
          <Link
            to="/chat"
            className="flex items-center gap-3 w-full transition-colors"
            onClick={() => {
              localStorage.removeItem("ragfusion-chat-session")
              localStorage.removeItem("ragfusion-current-chat")
              window.dispatchEvent(new Event("new-chat"))
              onClose?.()
            }}
          >
            <motion.span
              className="h-4 w-4 shrink-0 flex items-center justify-center"
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              <MessageSquareText className="h-4 w-4" aria-hidden="true" />
            </motion.span>
            <AnimatePresence mode="wait">
              {!isCollapsed && (
                <motion.span
                  key="label"
                  initial={{ opacity: 0, x: -10, width: 0 }}
                  animate={{ opacity: 1, x: 0, width: 'auto' }}
                  exit={{ opacity: 0, x: -10, width: 0 }}
                  transition={{ duration: 0.15, ease: 'easeOut' }}
                  style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}
                >
                  New Chat
                </motion.span>
              )}
            </AnimatePresence>
          </Link>
        </HoverCard>
      </motion.div>

      {/* Divider */}
      <motion.div
        className={cn('border-t border-border mx-3 my-1', isCollapsed && 'mx-2')}
        initial={{ opacity: 0, scaleX: 0 }}
        animate={{ opacity: 1, scaleX: 1 }}
        transition={{ duration: 0.3, delay: 0.6 }}
        style={{ transformOrigin: 'left' }}
      />

      {/* User Section / Theme Toggle / Logout */}
      <motion.div
        className={cn('p-3 bg-transparent', isCollapsed && 'p-2')}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.8 }}
      >
        <motion.div
          className={cn('flex items-center gap-3 mb-3', isCollapsed && 'justify-center')}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
        >
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Avatar className="h-8 w-8" size="default">
              <AvatarFallback className={'text-xs ' + avatarColorClass(user?.avatar_color)}>
                {getInitials(userName)}
              </AvatarFallback>
            </Avatar>
          </motion.div>
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.div
                key="user-info"
                className="flex-1 min-w-0"
                initial={{ opacity: 0, x: -10, width: 0 }}
                animate={{ opacity: 1, x: 0, width: 'auto' }}
                exit={{ opacity: 0, x: -10, width: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
              >
                {/* Fixed: Use the unified userName variable */}
                <p className="text-sm font-medium truncate text-foreground">
                  {userName}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.email || ''}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        <div className="space-y-1">
          <HoverCard
            asChild
            variant="none"
            className={cn('w-full justify-start gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors bg-transparent text-muted-foreground hover:bg-secondary/50 hover:text-foreground', isCollapsed && 'justify-center px-2')}
            onClick={onClose}
            aria-label="Profile"
          >
            <Link
              to="/profile"
              className="flex items-center gap-3 w-full transition-colors"
              onClick={onClose}
            >
              <motion.span
                className="h-5 w-5 shrink-0 flex items-center justify-center transition-colors"
                initial={{ scale: 0.8, rotate: -10 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                <User className="h-5 w-5" aria-hidden="true" />
              </motion.span>
              <AnimatePresence mode="wait">
                {!isCollapsed && (
                  <motion.span
                    key="label"
                    initial={{ opacity: 0, x: -10, width: 0 }}
                    animate={{ opacity: 1, x: 0, width: 'auto' }}
                    exit={{ opacity: 0, x: -10, width: 0 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                    style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}
                  >
                    Profile
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          </HoverCard>

          <HoverCard
            asChild
            variant="none"
            className={cn('w-full justify-start gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors bg-transparent text-muted-foreground hover:bg-secondary/50 hover:text-foreground', isCollapsed && 'justify-center px-2')}
            onClick={onClose}
            aria-label="Settings"
          >
            <Link
              to="/settings"
              className="flex items-center gap-3 w-full transition-colors"
              onClick={onClose}
            >
              <motion.span
                className="h-5 w-5 shrink-0 flex items-center justify-center transition-colors"
                initial={{ scale: 0.8, rotate: -10 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                <Settings className="h-5 w-5" aria-hidden="true" />
              </motion.span>
              <AnimatePresence mode="wait">
                {!isCollapsed && (
                  <motion.span
                    key="label"
                    initial={{ opacity: 0, x: -10, width: 0 }}
                    animate={{ opacity: 1, x: 0, width: 'auto' }}
                    exit={{ opacity: 0, x: -10, width: 0 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                    style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}
                  >
                    Settings
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          </HoverCard>

          <div className="border-t border-border my-2" />

          <HoverCard
            asChild
            variant="ghost"
            size="icon"
            onClick={() => toggleTheme()}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark'} mode`}
            className={cn('text-muted-foreground hover:bg-secondary/50 hover:text-foreground cursor-pointer', isCollapsed && 'mx-auto')}
          >
            <motion.button
              className="flex items-center justify-center"
              whileHover={{ scale: 1.1, rotate: 180 }}
              whileTap={{ scale: 0.9 }}
            >
              <motion.span
                animate={{ rotate: resolvedTheme === 'dark' ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                {resolvedTheme === 'dark' ? <Moon className="h-4 w-4" /> : theme === 'light' ? <Sun className="h-4 w-4" /> : <Monitor className="h-4 w-4" />}
              </motion.span>
            </motion.button>
          </HoverCard>

          <HoverCard
            variant="ghost"
            size="icon"
            asChild
            aria-label="Sign out"
            className={cn('text-muted-foreground hover:bg-secondary/50 hover:text-foreground cursor-pointer', isCollapsed && 'mx-auto')}
          >
            <Link 
              to="/login" 
              onClick={() => {
                if (logout) logout()
                if (onClose) onClose()
              }} 
              className="flex items-center justify-center"
            >
              <motion.span
                className="flex items-center justify-center"
                whileHover={{ scale: 1.1, rotate: -90 }}
                whileTap={{ scale: 0.9 }}
              >
                <LogOut className="h-4 w-4 transition-colors" aria-hidden="true" />
              </motion.span>
            </Link>
          </HoverCard>
        </div>
      </motion.div>

      {/* Mobile close button */}
      <HoverCard
        asChild
        variant="ghost"
        size="icon"
        className="lg:hidden absolute bottom-4 left-1/2 -translate-x-1/2 bg-transparent cursor-pointer"
        onClick={onClose}
        aria-label="Close sidebar"
      >
        <motion.button
          className="flex items-center justify-center text-foreground"
          whileHover={{ scale: 1.1, rotate: 90 }}
          whileTap={{ scale: 0.9 }}
        >
          <X className="h-5 w-5" />
        </motion.button>
      </HoverCard>
    </motion.aside>
  )
}
