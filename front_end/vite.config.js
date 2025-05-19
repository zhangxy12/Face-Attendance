import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8090', // FastAPI后端
        changeOrigin: true,
        rewrite: (path) => path, // 不重写
      }
    },
    allowedHosts: ["10680706bkfz8.vicp.fun"],
    allowedOrigins: ["http://localhost:8090", "http://127.0.0.1:8090"],
  },
  assetsInclude: ['**/*.png', '**/*.jpg', '**/*.gif'], // 添加你需要处理的图片格式
  resolve: {
    alias: {
      '@': '/src',
      '@dataview/datav-vue3': '@dataview/datav-vue3/dist/datav-vue3.esm.js', // 手动指定入口文件
    },
  },
})