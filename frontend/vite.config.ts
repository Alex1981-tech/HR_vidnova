import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const apiProxyTarget = process.env.HR_API_PROXY_TARGET || 'http://localhost:8050';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5178,
    // Docker bind-mount не пропускає inotify-події → vite не бачив змін і віддавав
    // застарілий кеш модулів (HMR мовчав, правки з'являлися лише після рестарту
    // контейнера). Polling змушує vite опитувати файли й коректно тригерити HMR.
    watch: {
      usePolling: true,
      interval: 300,
    },
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
