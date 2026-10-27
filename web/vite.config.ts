import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API runs on :8000 during development (uvicorn api.main:app); in production FastAPI serves dist/.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { chunkSizeWarningLimit: 1200 },
})
