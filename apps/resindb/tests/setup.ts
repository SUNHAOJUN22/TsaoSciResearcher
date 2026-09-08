import '@testing-library/jest-dom';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const originalFetch = globalThis.fetch.bind(globalThis);

/**
 * Vitest/jsdom has no HTTP server for Vite's public/ assets. Mirror the browser
 * contract by serving external resin JSON files from root data/resins.
 */
globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const rawUrl = typeof input === 'string' || input instanceof URL ? String(input) : input.url;
  const url = new URL(rawUrl, 'http://127.0.0.1');
  if (url.pathname.startsWith('/data/resins/')) {
    const fileName = path.basename(url.pathname);
    const filePath = path.resolve(process.cwd(), 'data', 'resins', fileName);
    try {
      const content = await readFile(filePath, 'utf8');
      return new Response(content, {
        status: 200,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      });
    } catch {
      return new Response(JSON.stringify({ error: 'not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      });
    }
  }
  return originalFetch(input, init);
};
