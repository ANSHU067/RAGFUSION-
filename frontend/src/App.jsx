import { RouterProvider } from 'react-router-dom'
import ErrorBoundary from '@/pages/errors/ErrorBoundary'
import { router } from '@/routes'

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider
        router={router}
        fallbackElement={
          <div className="flex h-screen items-center justify-center">
            Loading...
          </div>
        }
      />
    </ErrorBoundary>
  )
}