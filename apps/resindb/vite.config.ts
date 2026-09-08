/// <reference types="vitest" />
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createReadStream } from 'node:fs';
import { cp, stat } from 'node:fs/promises';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const governedData = path.join(__dirname, 'data');

function governedDataPlugin(): Plugin {
  return {
    name: 'resindb-governed-data',
    configureServer(server) {
      server.middlewares.use('/data', async (req: IncomingMessage, res: ServerResponse, next) => {
        try {
          const relative = decodeURIComponent((req.url ?? '/').split('?')[0]).replace(/^\/+/, '');
          const resolved = path.resolve(governedData, relative);
          if (!resolved.startsWith(`${governedData}${path.sep}`)) return next();
          const info = await stat(resolved);
          if (!info.isFile()) return next();
          res.setHeader('Content-Type', resolved.endsWith('.json') ? 'application/json; charset=utf-8' : 'application/octet-stream');
          res.setHeader('Cache-Control', 'no-store');
          createReadStream(resolved).pipe(res);
          return;
        } catch {
          return next();
        }
      });
    },
    async closeBundle() {
      await cp(governedData, path.join(__dirname, 'dist', 'data'), { recursive: true, force: true });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '');
  return {
    base: env.VITE_BASE_PATH || '/',
    server: { port: 3000, host: '127.0.0.1', proxy: { '/api/science': { target: 'http://127.0.0.1:8765', changeOrigin: true } } },
    plugins: [react(), tailwindcss(), governedDataPlugin()],
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './tests/setup.ts',
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'json-summary'],
        all: true,
        include: ['src/**/*.{ts,tsx}'],
        exclude: [
          'src/**/*.d.ts',
          'src/**/__tests__/**',
          'src/**/__mocks__/**',
          'src/**/*.{test,spec}.{ts,tsx}',
        ],
        thresholds: { statements: 24, branches: 12, functions: 14, lines: 24 },
      },
    },
    resolve: { alias: { '@': path.resolve(__dirname, './src') } },
    build: {
      outDir: 'dist',
      chunkSizeWarningLimit: 900,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined;
            if (id.includes('/react/') || id.includes('/react-dom/') || id.includes('/scheduler/')) return 'react-core';
            if (id.includes('/echarts/') || id.includes('/zrender/') || id.includes('/echarts-for-react/')) return 'echarts-core';
            if (id.includes('/recharts/') || id.includes('/d3-')) return 'data-visualization';
            if (id.includes('/jspdf/') || id.includes('/html2canvas/')) return 'reporting';
            if (id.includes('/react-markdown/') || id.includes('/remark-') || id.includes('/micromark')) return 'markdown';
            if (id.includes('/lucide-react/') || id.includes('/motion/')) return 'ui-toolkit';
            return undefined;
          },
        },
      },
    },
  };
});
