import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // SSE 流式支持：禁用代理缓冲，增加超时
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            // 标记 SSE 请求
            if (req.url?.includes('/chat/stream')) {
              proxyReq.setHeader('Accept', 'text/event-stream')
            }
          })
          proxy.on('proxyRes', (proxyRes) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              // 禁用缓冲
              proxyRes.headers['X-Accel-Buffering'] = 'no'
              proxyRes.headers['Cache-Control'] = 'no-cache'
            }
          })
        },
        timeout: 180000,       // 3 分钟
      },
    },
  },
})
