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
const sourceTarget = process.env.V5_SOURCE_API_ORIGIN;
if (sourceTarget && !/^http:\/\/(127\.0\.0\.1|localhost):[1-9][0-9]{0,4}$/.test(sourceTarget)) {
  throw new Error('V5_SOURCE_API_ORIGIN must be an explicit loopback HTTP origin');
}
function readonlyProxy(target: string): ProxyOptions {
 return {target,changeOrigin:true,configure:server=>{
  server.on('proxyReq',request=>{
   request.removeHeader('origin');request.removeHeader('cookie');request.removeHeader('authorization');
  });
 }};
}
const proxy: Record<string, ProxyOptions> = {};
if (target) proxy['/api/v4/manager/m18/v2'] = readonlyProxy(target);
if (sourceTarget) {
 proxy['/api/v5/manager/close-recapture'] = readonlyProxy(sourceTarget);
 proxy['/api/v5/source-bundle/status'] = readonlyProxy(sourceTarget);
 proxy['/api/v5/source-bundle/research-intelligence'] = readonlyProxy(sourceTarget);
 proxy['/api/v5/source-bundle/hk-preselection'] = readonlyProxy(sourceTarget);
 proxy['/api/v5/source-bundle/hk-close-review'] = readonlyProxy(sourceTarget);
 proxy['/api/v5/source-bundle/a-close-replay'] = readonlyProxy(sourceTarget);
 proxy['/api/v5/source-bundle/hk-stage-observed'] = readonlyProxy(sourceTarget);
}
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

