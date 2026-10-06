import { createBrowserRouter, Navigate } from 'react-router-dom'
import GlobalLayout from '../layouts/GlobalLayout'
import { DashboardLayout } from '@/components/layout'
import NotFound from '@/pages/errors/NotFound'
const lazyPage = (load) => async () => ({ Component: (await load()).default })
export const router = createBrowserRouter([
  { path: '/', element: <GlobalLayout />, children: [
    { index: true, lazy: lazyPage(() => import('../pages/HomePage')) },
    { path: 'login', lazy: lazyPage(() => import('../pages/auth/LoginPage')) },
    { path: 'signup', lazy: lazyPage(() => import('../pages/auth/SignupPage')) },
    ...['forgot-password', 'reset-password'].map((path) => ({ path, lazy: lazyPage(() => import('../pages/auth/RecoveryUnavailablePage')) })),
  ] },
  { path: '/dashboard', element: <DashboardLayout />, children: [
    { index: true, lazy: lazyPage(() => import('../pages/dashboard/DashboardPage')) },
    { path: 'chats', element: <Navigate to="/dashboard/history" replace /> },
    { path: 'history', lazy: lazyPage(() => import('../pages/history/HistoryPage')) },
    { path: 'profile', element: <Navigate to="/profile" replace /> },
    { path: 'settings', element: <Navigate to="/settings" replace /> },
  ] },
  { path: '/documents', element: <DashboardLayout />, children: [
    { index: true, element: <Navigate to="reader" replace /> },
    { path: 'reader', lazy: lazyPage(() => import('../pages/readers/DocumentReaderPage')) },
  ] },
  { path: '/profile', element: <DashboardLayout />, children: [
    { index: true, lazy: lazyPage(() => import('../pages/profile/ProfilePage')) },
  ] },
  { path: '/settings', element: <DashboardLayout />, children: [
    { index: true, lazy: lazyPage(() => import('../pages/settings/SettingsPage')) },
  ] },
  { path: '/youtube', element: <DashboardLayout />, children: [
    { index: true, element: <Navigate to="reader" replace /> },
    { path: 'reader', lazy: lazyPage(() => import('../pages/readers/YouTubeReaderPage')) },
  ] },
  { path: '/chat', element: <DashboardLayout />, children: [
    { index: true, lazy: lazyPage(() => import('../pages/readers/ChatPage')) },
    { path: 'new', lazy: lazyPage(() => import('../pages/readers/ChatPage')) },
    { path: ':sessionId', lazy: lazyPage(() => import('../pages/readers/ChatPage')) },
  ] },
  { path: '/website', element: <DashboardLayout />, children: [
    { index: true, element: <Navigate to="reader" replace /> },
    { path: 'reader', lazy: lazyPage(() => import('../pages/readers/WebsiteReaderPage')) },
  ] },
  { path: '*', element: <NotFound /> },
])
