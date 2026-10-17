import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'url'

const srcDirectory = fileURLToPath(new URL('./src', import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': srcDirectory,
    },
  },
  // HeroScene is one lazy-loaded renderer bundle. Keep it intact so React
  // Three Fiber's CommonJS initialization order cannot be split into a cycle.
  build: {
    chunkSizeWarningLimit: 1200,
  },
  // Let the bundler preserve dependency initialization order. Forcing the
  // renderer into size-limited chunks split React's CommonJS wrappers into
  // a cycle that crashed the application before React could mount.
})
