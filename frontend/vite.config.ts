import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';
import vue from '@vitejs/plugin-vue';
import type { ProxyOptions } from 'vite';

// Optional loopback-only bridge to the existing read-only module API. No CORS,
// remote origin, credentials, V4 port or API budget changes are needed.
const target = process.env.V5_MODULE_API_ORIGIN;
if (target && !/^http:\/\/(127\.0\.0\.1|localhost):[1-9][0-9]{0,4}$/.test(target)) {
  throw new Error('V5_MODULE_API_ORIGIN must be an explicit loopback HTTP origin');
}
const proxy: Record<string, ProxyOptions> | undefined = target ? {
  '/api/v4/manager/m18/v2': {
    target,
    changeOrigin: true,
    configure: server => {
      server.on('proxyReq', request => {
        request.removeHeader('origin');
        request.removeHeader('cookie');
        request.removeHeader('authorization');
      });
    },
  },
} : undefined;
export default defineConfig({
  plugins: [vue()],
  test: { environment: 'jsdom' },
  server: { host: '127.0.0.1', proxy },
  preview: { host: '127.0.0.1', proxy },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        dailyResearchCommand: resolve(__dirname, 'daily-research-command/index.html'),
        managerSelection: resolve(__dirname, 'manager-selection/index.html'),
      },
    },
  },
});
