import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/board': { target: 'http://localhost:8000', changeOrigin: true },
      '/trips': { target: 'http://localhost:8000', changeOrigin: true },
      '/companies': { target: 'http://localhost:8000', changeOrigin: true },
      '/destinations': { target: 'http://localhost:8000', changeOrigin: true },
      '/platforms': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})