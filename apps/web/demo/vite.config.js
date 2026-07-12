import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: process.env.GITHUB_PAGES === 'true' ? '/difficultai/' : '/',
  plugins: [react()],
  server: {
    port: 3000,
  },
})
