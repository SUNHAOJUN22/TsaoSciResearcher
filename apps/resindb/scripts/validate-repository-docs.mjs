#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const README_PATH = resolve(ROOT, 'README.md');
const PACKAGE_PATH = resolve(ROOT, 'package.json');
const VALIDATION_PATH = resolve(ROOT, 'docs/VALIDATION.md');
const IMAGE_DIR = resolve(ROOT, 'docs/images');
const EXPECTED_SCREENSHOTS = [
  'ui-dashboard-zh-light.png',
  'ui-dashboard-en-dark.png',
  'ui-product-detail.png',
  'ui-scientific-analytics.png',
  'ui-phase2l-rheology-proxy.png',
  'ui-phase2l-dependency-heatmap.png',
  'ui-kmeans-profile-audit.png',
  'ui-kmeans-device-calibration.png',
].sort();
const EXPECTED_AI_DIAGRAMS = [
  'ai-platform-architecture.svg',
  'ai-material-statistics.svg',
  'ai-polymer-lammps-workflow.svg',
  'ai-delivery-validation.svg',
].sort();
const FORBIDDEN = [
  '.github/workflows/v19-skill-contract.yml',
  '.github/workflows/native-full-qualification.yml',
  '.github/workflows/exact-tree-export.yml',
  'scripts/prepare-ci-manifest.mjs',
  '.github/apply-final-v2.trigger', '.github/workflows/apply-final-v2.yml',
  '.github/apply-final-small.trigger', '.github/workflows/apply-final-small.yml',
  '.github/apply-final-optimization.trigger', '.github/workflows/apply-final-optimization.yml',
  '.github/diagnose-final-blobs.trigger', '.github/workflows/diagnose-final-blobs.yml',
  '.github/diagnose-original-head.trigger', '.github/workflows/diagnose-original-head.yml',
  '.github/final-source-export.trigger', '.github/workflows/final-source-export.yml',
  '.github/remediate-lockfile-20260726.trigger', '.github/workflows/remediate-lockfile-20260726.yml',
  'reports/_final_source_export', 'reports/patch-diagnostic.json', '.resindb-delete-manifest.txt',
  '.github/.resindb-final-patch', '.github/.resindb-v320-delta',
  '.github/.resindb-stage1-delta',
  'scripts/readme-visuals.bundle.json',
  'scripts/generate-readme-visuals.mjs',
  'scripts/bundle-readme-visuals.mjs',
  'docs/README_VISUAL_DESIGN_SYSTEM.md',
];
const FORBIDDEN_PATH_PATTERNS = [
  /^\.github\/\.resindb-[^/]*(?:delta|patch|transport)[^/]*(?:\/|$)/i,
];

function fail(message) { throw new Error(message); }

function listRepositoryPaths(relativeRoot) {
  const absoluteRoot = resolve(ROOT, relativeRoot);
  if (!existsSync(absoluteRoot)) return [];
  const paths = [];
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const absolutePath = resolve(directory, entry.name);
      const repositoryPath = relative(ROOT, absolutePath).split(sep).join('/');
      paths.push(repositoryPath);
      if (entry.isDirectory()) visit(absolutePath);
    }
  };
  visit(absoluteRoot);
  return paths;
}

function validateLinks(text) {
  const patterns = [/<(?:img|a)\b[^>]*(?:src|href)="([^"]+)"/gi, /!?\[[^\]]*]\(([^)]+)\)/g];
  const missing = [];
  const seen = new Set();
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      const raw = match[1];
      const target = raw.trim().split(/\s+/, 1)[0].replace(/^<|>$/g, '').split('#', 1)[0].split('?', 1)[0];
      if (!target || /^(https?:|mailto:|data:|#)/.test(target) || seen.has(target)) continue;
      seen.add(target);
      if (!existsSync(resolve(ROOT, target))) missing.push(target);
    }
  }
  if (missing.length) fail(`README contains missing local targets: ${JSON.stringify(missing.sort())}`);
}

const readme = readFileSync(README_PATH, 'utf8');
const packageJson = JSON.parse(readFileSync(PACKAGE_PATH, 'utf8'));
const validation = readFileSync(VALIDATION_PATH, 'utf8');
const version = packageJson.version;
if (version !== '3.2.0' || !readme.includes(`version-${version}-`) || !validation.includes(`\`${version}\``)) {
  fail('Version drift between package, README and validation contract');
}
validateLinks(readme);

const actualScreenshots = readdirSync(IMAGE_DIR)
  .filter((name) => /^ui-.*\.png$/.test(name))
  .sort();
if (JSON.stringify(actualScreenshots) !== JSON.stringify(EXPECTED_SCREENSHOTS)) {
  fail(`README screenshot inventory mismatch: ${JSON.stringify(actualScreenshots)}`);
}
for (const name of EXPECTED_SCREENSHOTS) {
  const relativePath = `docs/images/${name}`;
  if (readme.split(relativePath).length - 1 !== 1) fail(`${relativePath} must be referenced exactly once`);
  if (statSync(resolve(IMAGE_DIR, name)).size < 20_000) fail(`${relativePath} is too small to be a real UI evidence screenshot`);
}
for (const name of EXPECTED_AI_DIAGRAMS) {
  const relativePath = `docs/images/${name}`;
  if (!existsSync(resolve(IMAGE_DIR, name))) fail(`README AI diagram is missing: ${relativePath}`);
  if (readme.split(relativePath).length - 1 !== 1) fail(`${relativePath} must be referenced exactly once`);
  if (statSync(resolve(IMAGE_DIR, name)).size < 5_000) fail(`${relativePath} is too small for a README technical diagram`);
}
const markdownImages = [...readme.matchAll(/!\[[^\]]*]\(([^)]+)\)/g)]
  .map((match) => match[1])
  .filter((target) => !target.startsWith('http'));
const expectedLocalImageCount = EXPECTED_SCREENSHOTS.length + EXPECTED_AI_DIAGRAMS.length;
if (markdownImages.length !== expectedLocalImageCount) {
  fail(`README local image count must equal ${expectedLocalImageCount}; found ${markdownImages.length}`);
}
const oldSynthetic = readdirSync(IMAGE_DIR).filter((name) => /^resindb-.*\.svg$/.test(name));
if (oldSynthetic.length) fail(`Synthetic README visual residue remains: ${JSON.stringify(oldSynthetic.sort())}`);

for (const phrase of [
  '数据层与代码层分离',
  'Carreau–Yasuda',
  'Gaussian Process',
  'Mahalanobis',
  'Prony',
  '$$',
  'docs/compute-module-catalog.json',
]) {
  if (!readme.includes(phrase)) fail(`README scientific/data contract coverage missing: ${phrase}`);
}

const requiredScripts = {
  'validate:docs': 'node scripts/validate-repository-docs.mjs && node scripts/validate-i18n-visuals.mjs',
  'validate:i18n-visuals': 'node scripts/validate-i18n-visuals.mjs',
  'validate:source': 'node scripts/validate-source-hygiene.mjs',
  'validate:compute': 'node scripts/validate-compute-surface.mjs',
  'audit:all': 'npm audit --audit-level=high',
  'report:pdf': 'node scripts/generate-validation-pdf.mjs',
};
for (const [key, value] of Object.entries(requiredScripts)) {
  if (packageJson.scripts?.[key] !== value) fail(`package script drift: ${key}`);
}
for (const path of [
  'data/manifest.json',
  'data/version.json',
  'data/metadata.json',
  'data/resins/manifest.json',
  'data/schemas/resin-data-document.schema.json',
  'data/schemas/resin-product.schema.json',
  'docs/DATA_ARCHITECTURE.md',
  'docs/COMPUTE_AND_DISPLAY_AUDIT.md',
  'docs/compute-module-catalog.json',
  'schemas/compute-module-catalog.schema.json',
]) {
  if (!existsSync(resolve(ROOT, path))) fail(`Required repository contract is missing: ${path}`);
}

const discoveredPaths = [
  ...listRepositoryPaths('.github'),
  ...listRepositoryPaths('reports'),
];
const residue = [...new Set([
  ...FORBIDDEN.filter((path) => existsSync(resolve(ROOT, path))),
  ...discoveredPaths.filter((path) => FORBIDDEN_PATH_PATTERNS.some((pattern) => pattern.test(path))),
])].sort();
if (residue.length) fail(`Temporary migration/diagnostic residue remains: ${JSON.stringify(residue)}`);
const pythonFiles = readdirSync(resolve(ROOT, 'scripts')).filter((name) => name.endsWith('.py'));
if (pythonFiles.length) fail(`Node-only tooling is incomplete: ${JSON.stringify(pythonFiles)}`);
const ci = readFileSync(resolve(ROOT, '.github/workflows/ci.yml'), 'utf8');
for (const phrase of [
  'branches: [main]',
  'contents: read',
  'npm run validate:docs',
  'npm run validate:source',
  'npm audit --omit=dev --audit-level=high --json',
  'npm audit --audit-level=high --json',
  'npm run report:pdf',
]) {
  if (!ci.includes(phrase)) fail(`Permanent CI missing: ${phrase}`);
}
if (ci.includes('contents: write')) fail('Permanent CI must be read-only');
if (/\bpython(?:3)?\b/i.test(ci)) fail('Permanent CI must not depend on Python');
console.log(
  `Validated README links, ${EXPECTED_SCREENSHOTS.length} real UI screenshots, ${EXPECTED_AI_DIAGRAMS.length} conceptual AI diagrams, version ${version}, `
  + 'canonical data contracts, compute catalog, Node-only tooling and repository hygiene.',
);
