import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In production the admin SPA is served by the backend under /backoffice
// (the backend's own /admin/** paths are the JWT-protected admin API). Local
// `npm run dev` keeps the app at the root for convenience.
export default defineConfig(({ mode }) => ({
  base: mode === 'production' ? '/backoffice/' : '/',
  plugins: [react()],
  resolve: {
    extensions: ['.js', '.jsx']
  }
}))
