import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 개발 중 /api 요청은 로컬 FastAPI(8000)로 넘겨요. 배포에서는 nginx가 같은 경로를 처리해요.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
});
