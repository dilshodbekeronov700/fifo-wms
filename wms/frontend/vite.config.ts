import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5175,
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
