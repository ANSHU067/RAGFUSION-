import { Sun, Moon, Monitor } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuLabel } from '@/components/ui/dropdown-menu'
import { useTheme } from '@/context/ThemeContext'

export function ThemeSwitcher({ variant = 'dropdown', className }) {
  const { theme, resolvedTheme, setLightTheme, setDarkTheme, setSystemTheme } = useTheme()

  if (variant === 'compact') {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-9 w-9" aria-label="Toggle theme">
            {resolvedTheme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>Appearance</DropdownMenuLabel>
          <DropdownMenuItem onClick={setLightTheme} className={theme === 'light' ? 'bg-accent' : ''} cursor-pointer>
            <Sun className="mr-2 h-4 w-4" />
            Light
          </DropdownMenuItem>
          <DropdownMenuItem onClick={setDarkTheme} className={theme === 'dark' ? 'bg-accent' : ''} cursor-pointer>
            <Moon className="mr-2 h-4 w-4" />
            Dark
          </DropdownMenuItem>
          <DropdownMenuItem onClick={setSystemTheme} className={theme === 'system' ? 'bg-accent' : ''} cursor-pointer>
            <Monitor className="mr-2 h-4 w-4" />
            System
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  return (
    <div className={className}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-foreground">Theme</span>
        <div className="flex items-center gap-1 bg-accent rounded-lg p-1" role="group" aria-label="Theme selector">
          <Button
            variant={theme === 'light' ? 'default' : 'ghost'}
            size="sm"
            onClick={setLightTheme}
            className="gap-1"
            aria-pressed={theme === 'light'}
          >
            <Sun className="h-4 w-4" />
            <span className="hidden sm:inline">Light</span>
          </Button>
          <Button
            variant={theme === 'dark' ? 'default' : 'ghost'}
            size="sm"
            onClick={setDarkTheme}
            className="gap-1"
            aria-pressed={theme === 'dark'}
          >
            <Moon className="h-4 w-4" />
            <span className="hidden sm:inline">Dark</span>
          </Button>
          <Button
            variant={theme === 'system' ? 'default' : 'ghost'}
            size="sm"
            onClick={setSystemTheme}
            className="gap-1"
            aria-pressed={theme === 'system'}
          >
            <Monitor className="h-4 w-4" />
            <span className="hidden sm:inline">System</span>
          </Button>
        </div>
      </div>
    </div>
  )
}