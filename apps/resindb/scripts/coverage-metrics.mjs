import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

import {
  isProductionTypeScriptFile,
  normalizeRepositoryPath,
} from './coverage-scope.mjs';

const root = path.resolve(import.meta.dirname, '..');
const sourcePath = path.join(root, 'coverage', 'coverage-final.json');
const artifactDir = path.join(root, 'artifacts');
const sourceRoot = path.join(root, 'src');

function percentage(covered, total) {
  return total === 0 ? 100 : Number(((covered / total) * 100).toFixed(2));
}

function summarizeCounter(counter) {
  const values = Object.values(counter);
  const covered = values.filter((value) => value > 0).length;
  return { covered, total: values.length, percent: percentage(covered, values.length) };
}

function summarizeBranches(branches) {
  const values = Object.values(branches).flat();
  const covered = values.filter((value) => value > 0).length;
  return { covered, total: values.length, percent: percentage(covered, values.length) };
}

function toRepositoryRelative(filePath) {
  const absolute = path.isAbsolute(filePath) ? filePath : path.resolve(root, filePath);
  return normalizeRepositoryPath(path.relative(root, absolute));
}

async function collectProductionSources(directory) {
  const sources = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      sources.push(...await collectProductionSources(target));
    } else if (isProductionTypeScriptFile(target)) {
      sources.push(toRepositoryRelative(target));
    }
  }
  return sources;
}

const coverage = JSON.parse(await readFile(sourcePath, 'utf8'));
const totals = {
  statements: { covered: 0, total: 0 },
  branches: { covered: 0, total: 0 },
  functions: { covered: 0, total: 0 },
  lines: { covered: 0, total: 0 },
};

for (const fileCoverage of Object.values(coverage)) {
  const statements = summarizeCounter(fileCoverage.s);
  const branches = summarizeBranches(fileCoverage.b);
  const functions = summarizeCounter(fileCoverage.f);
  const lineHits = new Map();
  for (const [statementId, count] of Object.entries(fileCoverage.s)) {
    const line = fileCoverage.statementMap[statementId]?.start?.line;
    if (line) lineHits.set(line, Math.max(lineHits.get(line) ?? 0, count));
  }
  const lines = summarizeCounter(Object.fromEntries(lineHits));
  for (const [name, metric] of Object.entries({ statements, branches, functions, lines })) {
    totals[name].covered += metric.covered;
    totals[name].total += metric.total;
  }
}

for (const metric of Object.values(totals)) metric.percent = percentage(metric.covered, metric.total);

const productionSources = [...new Set(await collectProductionSources(sourceRoot))].sort();
const instrumentedSources = new Set(
  Object.keys(coverage)
    .map(toRepositoryRelative)
    .filter((filePath) => filePath.startsWith('src/') && isProductionTypeScriptFile(filePath)),
);
const missingProductionSources = productionSources.filter((filePath) => !instrumentedSources.has(filePath));
const unexpectedInstrumentedSources = [...instrumentedSources]
  .filter((filePath) => !productionSources.includes(filePath))
  .sort();

const report = {
  schemaVersion: 3,
  generatedAt: new Date().toISOString(),
  coverageScope: 'production-typescript-excluding-tests-and-declarations',
  instrumentedSourceFileCount: instrumentedSources.size,
  productionSourceFileCount: productionSources.length,
  scopeComplete: missingProductionSources.length === 0 && unexpectedInstrumentedSources.length === 0,
  missingProductionSources,
  unexpectedInstrumentedSources,
  thresholds: { statements: 24, branches: 12, functions: 14, lines: 24 },
  totals,
};

await mkdir(artifactDir, { recursive: true });
await writeFile(path.join(artifactDir, 'coverage-summary.json'), `${JSON.stringify(report, null, 2)}\n`);
if (!report.scopeComplete) {
  throw new Error(
    `Coverage scope incomplete: instrumented ${instrumentedSources.size} of ${productionSources.length} production source files; `
      + `missing=${missingProductionSources.length}, unexpected=${unexpectedInstrumentedSources.length}`,
  );
}
console.log(
  `Whole-source coverage (${productionSources.length} production files): ${totals.lines.percent}% lines, `
    + `${totals.statements.percent}% statements, ${totals.branches.percent}% branches, ${totals.functions.percent}% functions.`,
);
