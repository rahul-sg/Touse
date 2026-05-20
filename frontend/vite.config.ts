import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Read .env from project root (one level up from frontend/)
  envDir: '..',
})
