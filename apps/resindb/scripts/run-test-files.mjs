import { readdirSync, statSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const vitestBin = path.join(projectRoot, 'node_modules', 'vitest', 'vitest.mjs');
const roots = process.argv.slice(2);

if (roots.length === 0) {
  console.error('Usage: node scripts/run-test-files.mjs <file-or-directory> [...]');
  process.exit(2);
}

function collect(entry) {
  const absolute = path.resolve(projectRoot, entry);
  const stat = statSync(absolute);
  if (stat.isFile()) return /\.test\.[cm]?[jt]sx?$/.test(absolute) ? [absolute] : [];
  return readdirSync(absolute)
    .sort()
    .flatMap((name) => collect(path.join(entry, name)));
}

const files = roots.flatMap(collect).sort();
if (files.length === 0) {
  console.error(`No test files found under: ${roots.join(', ')}`);
  process.exit(2);
}

for (const absolute of files) {
  const file = path.relative(projectRoot, absolute);
  console.log(`\n=== isolated Vitest: ${file} ===`);
  const result = spawnSync(
    process.execPath,
    [vitestBin, 'run', file, '--pool=forks', '--maxWorkers=1', '--fileParallelism=false', '--testTimeout=30000', '--hookTimeout=30000', '--teardownTimeout=10000'],
    {
      cwd: projectRoot,
      stdio: 'inherit',
      env: { ...process.env, CI: '1', TERM: 'dumb' },
      timeout: 120_000,
      killSignal: 'SIGKILL',
    },
  );
  if (result.error) {
    console.error(`Isolated Vitest failed to exit for ${file}:`, result.error);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

console.log(`\nIsolated Vitest completed: ${files.length} file(s).`);
