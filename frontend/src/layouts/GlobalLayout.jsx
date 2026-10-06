import { Link, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { useTheme } from '@/context/ThemeContext'
import { Moon, Sun, Monitor } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { PageTransition } from '@/components/ui/PageTransition'

function ThemeToggle() {
  const { theme, resolvedTheme, setLightTheme, setDarkTheme, setSystemTheme } = useTheme()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Toggle theme">
          {resolvedTheme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onClick={setLightTheme} className={theme === 'light' ? 'bg-accent' : ''}>
          <Sun className="mr-2 h-4 w-4" />
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={setDarkTheme} className={theme === 'dark' ? 'bg-accent' : ''}>
          <Moon className="mr-2 h-4 w-4" />
          Dark
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={setSystemTheme} className={theme === 'system' ? 'bg-accent' : ''}>
          <Monitor className="mr-2 h-4 w-4" />
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

const landingNavItems = [
  ['top', 'Home'],
  ['product', 'Product'],
  ['features', 'Features'],
  ['workflow', 'Workflow'],
  ['pricing', 'Pricing'],
]

export default function GlobalLayout() {
  const location = useLocation()
  const [activeSection, setActiveSection] = useState('top')

  useEffect(() => {
    if (location.pathname !== '/') return

    const updateActiveSection = () => {
      const current = landingNavItems.reduce((active, [id]) => {
        const section = document.getElementById(id)
        return section && section.getBoundingClientRect().top <= 128 ? id : active
      }, 'top')
      setActiveSection(current)
    }

    updateActiveSection()
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    return () => window.removeEventListener('scroll', updateActiveSection)
  }, [location.pathname])

  return (
    <TooltipProvider>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 sticky top-0 z-50">
          <div className="container-wide">
            <div className="flex h-16 items-center justify-between">
              <div className="flex items-center gap-8">
                <Link to="/" className="flex items-center gap-2 font-bold text-xl text-foreground">
                  <span className="text-primary">RAGFUSION</span>
                </Link>
                <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
                  {landingNavItems.map(([id, label]) => <a key={id} href={`/#${id}`} onClick={() => setActiveSection(id)} className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${location.pathname === '/' && activeSection === id ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}>{label}</a>)}
                </nav>
              </div>
              <div className="flex items-center gap-4">
                <Button variant="outline" size="sm" className="hidden sm:inline-flex" asChild><Link to="/login">Sign in</Link></Button>
                <Button size="sm" asChild><Link to="/signup">Get started</Link></Button>
                <ThemeToggle />
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 container-wide py-8">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </main>
        <footer className="border-t border-border bg-muted/20 py-10">
          <div className="container-wide">
            <div className="grid gap-8 md:grid-cols-[1.4fr_repeat(3,1fr)]">
              <div><p className="font-bold text-foreground"><span className="text-primary">RAGFUSION</span></p><p className="mt-3 max-w-xs text-sm leading-6 text-muted-foreground">A trusted AI workspace for documents, videos, and the answers inside them.</p></div>
              <div><p className="text-sm font-semibold text-foreground">Product</p><div className="mt-3 space-y-2 text-sm text-muted-foreground"><a href="#product" className="block hover:text-foreground">Overview</a><a href="#features" className="block hover:text-foreground">Features</a><a href="#pricing" className="block hover:text-foreground">Pricing</a></div></div>
              <div><p className="text-sm font-semibold text-foreground">Developers</p><div className="mt-3 space-y-2 text-sm text-muted-foreground"><a href="#workflow" className="block hover:text-foreground">How it works</a><a href="#" className="block hover:text-foreground">Documentation</a><a href="#" className="block hover:text-foreground">API</a></div></div>
              <div><p className="text-sm font-semibold text-foreground">Company</p><div className="mt-3 space-y-2 text-sm text-muted-foreground"><a href="#" className="block hover:text-foreground">GitHub</a><a href="#" className="block hover:text-foreground">Privacy</a><a href="#" className="block hover:text-foreground">Terms</a></div></div>
            </div>
            <div className="mt-10 flex flex-col justify-between gap-3 border-t pt-5 text-xs text-muted-foreground sm:flex-row"><p>© 2026 RAGFUSION. Built for grounded AI.</p><p>Sources first. Answers second.</p></div>
          </div>
        </footer>
        <Toaster
          position="top-right"
          toastOptions={{
            className: 'bg-background border-border',
            duration: 5000,
            style: {
              background: 'var(--background)',
              border: '1px solid var(--border)',
            },
          }}
        />
      </div>
    </TooltipProvider>
  )
}
