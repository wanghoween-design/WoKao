import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器独立端口（5173），/api 代理到后端 FastAPI(8000)
// 生产构建 base 为 '/'，可由后端 server.py 在 / 托管 frontend/dist
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
