import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Menu, Sun, Moon, Monitor, User, LogOut, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel } from '@/components/ui/dropdown-menu'
import { useTheme } from '@/context/ThemeContext'
import { Toaster } from '@/components/ui/sonner'
import { useAuth } from '@/context/AuthContext'
import { avatarColorClass } from '@/lib/profile'

const getInitials = (name) => {
  if (!name) return 'U'
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
}

export function Navbar({ onMenuClick }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const section = pathname.startsWith('/documents') ? 'Documents' : pathname.startsWith('/youtube') ? 'YouTube' : pathname.startsWith('/website') ? 'Website' : pathname.startsWith('/chat') ? 'Chat' : pathname.includes('/history') ? 'History' : pathname.includes('/settings') ? 'Settings' : pathname.includes('/profile') ? 'Profile' : 'Overview'
  const { user, logout } = useAuth()
  const {
    theme,
    resolvedTheme,
    setLightTheme,
    setDarkTheme,
    setSystemTheme
  } = useTheme()

  // Define userName for safe access across the component
  const userName = 
    user?.display_name || 
    user?.full_name || 
    user?.username || 
    user?.name || 
    'User'

  return (
    <header className="sticky top-0 z-30 w-full border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="container-wide">
        <div className="flex h-16 items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={onMenuClick}
            aria-label="Open menu"
            aria-expanded={undefined}
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>

          <div className="min-w-0"><span className="hidden text-xs text-muted-foreground sm:block">Workspace</span><span className="block truncate text-sm font-semibold">{section}</span></div>
          </div>

          {/* Right Side Actions */}
          <div className="ml-auto flex shrink-0 items-center gap-3">
            {/* Theme Toggle */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-9 w-9" aria-label="Toggle theme">
                  {resolvedTheme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>Appearance</DropdownMenuLabel>
                <DropdownMenuItem onClick={setLightTheme} className={`cursor-pointer ${theme === 'light' ? 'bg-accent' : ''}`}>
                  <Sun className="mr-2 h-4 w-4" />
                  Light
                </DropdownMenuItem>
                <DropdownMenuItem onClick={setDarkTheme} className={`cursor-pointer ${theme === 'dark' ? 'bg-accent' : ''}`}>
                  <Moon className="mr-2 h-4 w-4" />
                  Dark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={setSystemTheme} className={`cursor-pointer ${theme === 'system' ? 'bg-accent' : ''}`}>
                  <Monitor className="mr-2 h-4 w-4" />
                  System
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-9 w-9 rounded-full p-0" aria-label="User menu">
                  <Avatar className="h-8 w-8">
                    {/* Fixed: userName is now safely defined and used */}
                    <AvatarFallback className={'text-xs ' + avatarColorClass(user?.avatar_color)}>{getInitials(userName)}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-2">
                  {/* Fixed: Use curly braces so React evaluates the variable instead of printing raw text */}
                  <p className="font-medium text-sm">
                    {userName}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {user?.email || ''}
                  </p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/profile">
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/settings">
                    <Settings className="mr-2 h-4 w-4" />
                    AI settings
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuSeparator />
                <DropdownMenuLabel>Preferences</DropdownMenuLabel>
                <DropdownMenuItem onClick={setLightTheme} className={`cursor-pointer ${theme === 'light' ? 'bg-accent' : ''}`}>
                  <Sun className="mr-2 h-4 w-4" />
                  Light mode
                </DropdownMenuItem>
                <DropdownMenuItem onClick={setDarkTheme} className={`cursor-pointer ${theme === 'dark' ? 'bg-accent' : ''}`}>
                  <Moon className="mr-2 h-4 w-4" />
                  Dark mode
                </DropdownMenuItem>
                <DropdownMenuItem onClick={setSystemTheme} className={`cursor-pointer ${theme === 'system' ? 'bg-accent' : ''}`}>
                  <Monitor className="mr-2 h-4 w-4" />
                  System default
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild className="text-destructive focus:text-destructive">
                  <button onClick={() => {
                    if (logout) logout()
                    navigate('/login')
                  }} className="w-full flex items-center cursor-pointer">
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign out
                  </button>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
      <Toaster position="top-right" />
    </header>
  )
}
