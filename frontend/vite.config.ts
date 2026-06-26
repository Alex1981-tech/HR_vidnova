import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const apiProxyTarget = process.env.HR_API_PROXY_TARGET || 'http://localhost:8050';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5178,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: false,
      },
      '/admin': {
        target: apiProxyTarget,
        changeOrigin: false,
      },
      '/media': {
        target: apiProxyTarget,
        changeOrigin: false,
      },
    },
  },
});
