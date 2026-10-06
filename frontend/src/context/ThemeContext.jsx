import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { LEGACY_STORAGE_PREFIX } from '@/services/branding'

const ThemeContext = createContext(null)

export function ThemeProvider({ children, defaultTheme = 'system', storageKey = 'ragfusion-theme' }) {
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey) || localStorage.getItem(LEGACY_STORAGE_PREFIX + 'theme')
      if (stored) return stored
    }
    return defaultTheme
  })

  const [resolvedTheme, setResolvedTheme] = useState('light')
  const [mounted, setMounted] = useState(false)

  const resolveTheme = useCallback((themeValue) => {
    if (themeValue === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return themeValue
  }, [])

  useEffect(() => {
    setMounted(true)
    const resolved = resolveTheme(theme)
    setResolvedTheme(resolved)
    document.documentElement.classList.toggle('dark', resolved === 'dark')
    localStorage.setItem(storageKey, theme)
    localStorage.removeItem(LEGACY_STORAGE_PREFIX + 'theme')
  }, [theme, resolveTheme, storageKey])

  useEffect(() => {
    if (!mounted) return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e) => {
      if (theme === 'system') {
        const resolved = e.matches ? 'dark' : 'light'
        setResolvedTheme(resolved)
        document.documentElement.classList.toggle('dark', resolved === 'dark')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme, mounted])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      if (prev === 'light') return 'dark'
      if (prev === 'dark') return 'system'
      return 'light'
    })
  }, [])

  const setLightTheme = useCallback(() => setTheme('light'), [])
  const setDarkTheme = useCallback(() => setTheme('dark'), [])
  const setSystemTheme = useCallback(() => setTheme('system'), [])

  if (!mounted) {
    return (
      <ThemeContext.Provider value={{ theme: 'light', resolvedTheme: 'light', toggleTheme: () => {}, setLightTheme: () => {}, setDarkTheme: () => {}, setSystemTheme: () => {} }}>
        {children}
      </ThemeContext.Provider>
    )
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        resolvedTheme,
        toggleTheme,
        setLightTheme,
        setDarkTheme,
        setSystemTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
