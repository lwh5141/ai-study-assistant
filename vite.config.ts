import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure(proxy) {
          let lastWarn = 0
          proxy.on('error', (err) => {
            const now = Date.now()
            // ECONNREFUSED → 后端未启动，每 10 秒最多提示一次
            if ((err as NodeJS.ErrnoException).code === 'ECONNREFUSED') {
              if (now - lastWarn > 10000) {
                console.warn(
                  '\x1b[33m[vite]\x1b[0m 后端未响应 (http://localhost:8000)，请先启动后端',
                )
                lastWarn = now
              }
              return
            }
            // 其他代理错误正常输出
            console.warn(`[vite] proxy error: ${err.message}`)
          })
        },
      },
    },
  },
})
