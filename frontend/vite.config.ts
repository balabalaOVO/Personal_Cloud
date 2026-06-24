import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Base path: '/' for production (served from FastAPI root),
  // can be overridden via VITE_BASE env var
  base: process.env.VITE_BASE || '/',
  server: {
    port: 5173,
    // In dev mode, proxy /api to the FastAPI backend
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
