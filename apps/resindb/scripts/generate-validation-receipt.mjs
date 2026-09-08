import { lstat, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { noHighAuditFindings, validateBranchProof, validBuildBudgets, validCiContext, validCoreGates, validTestEvidence, validScreenshotManifest, validComputeSurface } from './validation-receipt-contract.mjs';

const root = path.resolve(import.meta.dirname, '..');
const artifacts = path.join(root, 'artifacts');
const COVERAGE_SCOPE = 'production-typescript-excluding-tests-and-declarations';

async function readJson(name, fallback = null) {
  try {
    const value = JSON.parse(await readFile(path.join(artifacts, name), 'utf8'));
    return value !== null && typeof value === 'object' && !Array.isArray(value) ? value : fallback;
  } catch {
    return fallback;
  }
}
async function isScreenshotFile(name) {
  try {
    const info = await lstat(path.join(artifacts, name));
    return info.isFile() && !info.isSymbolicLink() && info.size > 0;
  } catch { return false; }
}

const [
  tests,
  coverage,
  build,
  ui,
  prodAudit,
  fullAudit,
  ciGates,
  context,
  kmeansBenchmark,
  computeSurfaceAudit,
  scientificUiAudit,
] = await Promise.all([
  readJson('test-results.json'),
  readJson('coverage-summary.json'),
  readJson('build-metrics.json'),
  readJson('ui-smoke-manifest.json'),
  readJson('npm-audit-prod.json'),
  readJson('npm-audit-all.json'),
  readJson('ci-gates.json'),
  readJson('ci-context.json', { sha: 'local-worktree', repository: 'local' }),
  readJson('kmeans-backend-benchmark.json'),
  readJson('compute-surface-audit.json'),
  readJson('scientific-ui-audit.json'),
]);

let branchProof = '';
try { branchProof = (await readFile(path.join(artifacts, 'branch-proof.txt'), 'utf8')).trim(); } catch {}
const branchProofRequired = context.ref === 'refs/heads/main';
const branchProofValid = validateBranchProof(branchProof, context.sha);
const screenshotManifestValid = validScreenshotManifest(ui);
const screenshotEntries = screenshotManifestValid ? Object.entries(ui.screenshots) : [];
const screenshotChecks = await Promise.all(screenshotEntries.map(async ([scene, file]) => ({
  scene,
  file,
  exists: await isScreenshotFile(file),
})));

function validKMeansBenchmark(report) {
  return report?.schemaVersion === 'kmeans-backend-benchmark-report-1.0.0'
    && report?.timingGate === 'informational-only'
    && report?.equivalence?.status === 'PASS'
    && Array.isArray(report?.cases)
    && report.cases.length > 0
    && report.cases.every((entry) => entry?.equivalence === 'PASS')
    && typeof report?.reportDigest === 'string'
    && /^[0-9a-f]{64}$/.test(report.reportDigest);
}

const checks = {
  context: validCiContext(context, {
    repository: process.env.GITHUB_REPOSITORY,
    sha: process.env.GITHUB_SHA,
    ref: process.env.GITHUB_REF,
    runId: process.env.GITHUB_RUN_ID === undefined ? undefined : Number(process.env.GITHUB_RUN_ID),
    runAttempt: process.env.GITHUB_RUN_ATTEMPT === undefined ? undefined : Number(process.env.GITHUB_RUN_ATTEMPT),
  }),
  coreGates: validCoreGates(ciGates, branchProofRequired),
  tests: validTestEvidence(tests),
  wholeSourceCoverage: coverage?.scopeComplete === true && coverage?.coverageScope === COVERAGE_SCOPE,
  buildBudgets: validBuildBudgets(build),
  externalData: Number.isSafeInteger(build?.externalResinDataBytes) && build.externalResinDataBytes > 0,
  uiEvidence: screenshotManifestValid && screenshotChecks.every((entry) => entry.exists),
  kmeansBenchmarkEvidence: validKMeansBenchmark(kmeansBenchmark),
  computeSurface: validComputeSurface(computeSurfaceAudit),
  scientificUi: scientificUiAudit?.acceptance === 'PASS',
  productionAudit: noHighAuditFindings(prodAudit),
  completeAudit: noHighAuditFindings(fullAudit),
  singleMainBranch: !branchProofRequired || branchProofValid,
};

const receipt = {
  schemaVersion: 2,
  generatedAt: new Date().toISOString(),
  repository: context.repository,
  sha: context.sha,
  runId: context.runId,
  runAttempt: context.runAttempt,
  acceptance: Object.values(checks).every(Boolean) ? 'PASS' : 'EVIDENCE_INCOMPLETE',
  checks,
  tests: tests ? {
    files: tests.testResults?.length ?? tests.numTotalTestSuites,
    total: tests.numTotalTests,
    passed: tests.numPassedTests,
    failed: tests.numFailedTests,
  } : null,
  coverage: coverage ? {
    scope: coverage.coverageScope,
    instrumentedSourceFileCount: coverage.instrumentedSourceFileCount,
    productionSourceFileCount: coverage.productionSourceFileCount,
    totals: coverage.totals,
  } : null,
  build: build ? {
    entryGzipBytes: build.entry?.gzipBytes,
    entryGzipBudgetBytes: build.budgets?.entryGzipBytes,
    echartsBytes: build.echarts?.bytes,
    echartsBudgetBytes: build.budgets?.echartsRawBytes,
    externalResinDataBytes: build.externalResinDataBytes,
  } : null,
  computeSurface: computeSurfaceAudit ? {
    acceptance: computeSurfaceAudit.acceptance,
    catalogModules: computeSurfaceAudit.catalogModules,
    workerFiles: computeSurfaceAudit.workerFiles,
    chartMappedModules: computeSurfaceAudit.chartMappedModules,
  } : null,
  scientificUi: scientificUiAudit ? {
    acceptance: scientificUiAudit.acceptance,
    chartFiles: scientificUiAudit.chartFiles,
    directEchartsInitFiles: scientificUiAudit.directEchartsInitFiles,
  } : null,
  kmeansBenchmark: kmeansBenchmark ? {
    schemaVersion: kmeansBenchmark.schemaVersion,
    runtime: kmeansBenchmark.benchmarkRuntime,
    mode: kmeansBenchmark.mode,
    timingGate: kmeansBenchmark.timingGate,
    equivalence: kmeansBenchmark.equivalence,
    crossoverAnalysis: kmeansBenchmark.crossoverAnalysis,
    environmentFingerprint: kmeansBenchmark.environment?.fingerprint,
    reportDigest: kmeansBenchmark.reportDigest,
  } : null,
  uiScenes: screenshotChecks,
  branchGovernance: {
    required: branchProofRequired,
    proofValid: branchProofValid,
  },
  branchProof,
};

await mkdir(artifacts, { recursive: true });
await writeFile(path.join(artifacts, 'validation-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(`Validation receipt: ${receipt.acceptance}`);
if (process.env.CI && receipt.acceptance !== 'PASS') process.exitCode = 1;
