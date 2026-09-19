import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// pywebview 以 file:// 加载 dist/index.html，必须用相对路径 base
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets',
    chunkSizeWarningLimit: 1500,
  },
  server: {
    port: 5173,
    strictPort: false,
  },
})
