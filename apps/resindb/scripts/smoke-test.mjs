import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const viteBin = path.join(projectRoot, 'node_modules', 'vite', 'bin', 'vite.js');
const host = '127.0.0.1';
const port = 4173;
const url = `http://${host}:${port}`;

const preview = spawn(
  process.execPath,
  [viteBin, 'preview', '--host', host, '--port', String(port), '--strictPort'],
  {
    cwd: projectRoot,
    env: { ...process.env, NODE_ENV: 'production' },
    stdio: ['ignore', 'pipe', 'pipe'],
  },
);

let stderr = '';
preview.stdout.on('data', (chunk) => process.stdout.write(chunk));
preview.stderr.on('data', (chunk) => {
  stderr += chunk.toString();
  process.stderr.write(chunk);
});

const sleep = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitForPreview() {
  for (let attempt = 1; attempt <= 40; attempt += 1) {
    if (preview.exitCode !== null) {
      throw new Error(
        `Preview server exited before becoming ready (code ${preview.exitCode}).\n${stderr}`,
      );
    }

    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_000) });
      const html = await response.text();
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      if (!html.includes('id="root"')) {
        throw new Error('HTML response does not contain the React #root mount element');
      }
      console.log(`Smoke test passed: ${url} returned the production application shell.`);
      return;
    } catch (error) {
      if (attempt === 40) throw error;
      await sleep(500);
    }
  }
}

function stopPreview() {
  if (preview.exitCode === null) preview.kill('SIGTERM');
}

process.on('SIGINT', () => {
  stopPreview();
  process.exit(130);
});
process.on('SIGTERM', () => {
  stopPreview();
  process.exit(143);
});

try {
  await waitForPreview();
} finally {
  stopPreview();
}
