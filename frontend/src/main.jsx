import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider, AuthProvider, UserProvider, ChatProvider, UploadProvider, useAuth } from './context'
import App from './App'
import './styles/globals.css'
function SessionProviders() {
  const { user, sessionVersion } = useAuth()
  return <UserProvider key={`${user?.id || 'anonymous'}:${sessionVersion}`}><ChatProvider><UploadProvider><App /></UploadProvider></ChatProvider></UserProvider>
}
createRoot(document.getElementById('root')).render(
  <StrictMode><ThemeProvider><AuthProvider><SessionProviders /></AuthProvider></ThemeProvider></StrictMode>,
)
