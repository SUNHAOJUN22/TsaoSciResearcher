import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { basename, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const catalogPath = join(root, 'docs/compute-module-catalog.json');
const workerRoot = join(root, 'src/workers');
const testRoot = join(root, 'tests');
const artifactRoot = join(root, 'artifacts');
const failures = [];

const read = (path) => readFileSync(join(root, path), 'utf8');
const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
if (catalog.schemaVersion !== 'resindb-compute-catalog-1.0.0') {
  failures.push('compute catalog schemaVersion drift');
}
if (!/^\d{4}-\d{2}-\d{2}$/.test(catalog.updatedAt)) failures.push('compute catalog updatedAt');
if (!Array.isArray(catalog.modules) || catalog.modules.length < 20) failures.push('compute catalog is incomplete');

const ids = new Set();
const workers = new Set();
const chartSource = read('src/components/charts/DataVisualizerLegacy.tsx');
function walk(directory) {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory() ? walk(path) : [path];
    });
}

const allTestSource = walk(testRoot)
  .filter((path) => path.endsWith('.ts'))
  .map((path) => readFileSync(path, 'utf8'))
  .join('\n');

for (const module of catalog.modules ?? []) {
  if (!module || typeof module !== 'object') {
    failures.push('compute catalog contains a non-object module');
    continue;
  }
  if (ids.has(module.id)) failures.push(`duplicate compute module id: ${module.id}`);
  ids.add(module.id);
  if (workers.has(module.worker)) failures.push(`duplicate compute worker mapping: ${module.worker}`);
  workers.add(module.worker);

  for (const field of ['id', 'kind', 'worker', 'displaySurface', 'inputContract', 'outputContract', 'mathematicalContract', 'scientificBoundary']) {
    if (typeof module[field] !== 'string' || !module[field].trim()) {
      failures.push(`${module.id ?? 'unknown'}: missing ${field}`);
    }
  }
  if (!existsSync(join(root, module.worker))) failures.push(`${module.id}: worker file missing`);
  if (!existsSync(join(root, module.displaySurface))) failures.push(`${module.id}: display surface missing`);
  if (module.hook !== null && !existsSync(join(root, module.hook))) failures.push(`${module.id}: hook file missing`);
  if (module.chartId !== null && !chartSource.includes(`\"${module.chartId}\"`) && !chartSource.includes(`'${module.chartId}'`)) {
    failures.push(`${module.id}: chart id ${module.chartId} is not wired into DataVisualizer`);
  }

  const workerStem = basename(module.worker, '.ts');
  if (module.kind !== 'infrastructure' && !allTestSource.includes(workerStem)) {
    failures.push(`${module.id}: scientific worker has no direct test reference`);
  }
}

const actualWorkers = readdirSync(workerRoot)
  .filter((name) => name.endsWith('Worker.ts'))
  .map((name) => `src/workers/${name}`)
  .sort();
for (const worker of actualWorkers) {
  if (!workers.has(worker)) failures.push(`${worker}: missing from compute catalog`);
}
for (const worker of workers) {
  if (!actualWorkers.includes(worker)) failures.push(`${worker}: catalog points to a non-worker file`);
}

const criticalRoots = ['src/compute', 'src/workers', 'src/data'];
const explicitAny = [];
for (const relativeRoot of criticalRoots) {
  const directory = join(root, relativeRoot);
  const stack = [directory];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const path = join(current, entry.name);
      if (entry.isDirectory()) stack.push(path);
      else if (/\.(?:ts|tsx)$/.test(entry.name)) {
        const lines = readFileSync(path, 'utf8').split(/\r?\n/);
        lines.forEach((line, index) => {
          if (/(?:\:\s*any\b|<any>|\bas any\b)/.test(line)) {
            explicitAny.push(`${path.slice(root.length + 1)}:${index + 1}`);
          }
        });
      }
    }
  }
}
if (explicitAny.length) failures.push(`explicit any remains in critical compute/data paths: ${explicitAny.join(', ')}`);

const audit = {
  schemaVersion: 'compute-surface-audit-1.0.0',
  catalogModules: catalog.modules?.length ?? 0,
  workerFiles: actualWorkers.length,
  chartMappedModules: (catalog.modules ?? []).filter((module) => module.chartId !== null).length,
  explicitAny,
  failures,
  acceptance: failures.length ? 'FAIL' : 'PASS',
};
mkdirSync(artifactRoot, { recursive: true });
writeFileSync(join(artifactRoot, 'compute-surface-audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
console.log(JSON.stringify(audit, null, 2));
if (failures.length) throw new Error(`compute surface audit failed:\n${failures.join('\n')}`);
