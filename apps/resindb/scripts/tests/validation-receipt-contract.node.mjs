import assert from 'node:assert/strict';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import {
  REQUIRED_CORE_GATES, noHighAuditFindings, validateBranchProof,
  validBuildBudgets, validCiContext, validCoreGates, validTestEvidence,
} from '../validation-receipt-contract.mjs';

const sha = 'a'.repeat(40);
const proof = `${sha}\trefs/heads/main\n`;
const context = {schemaVersion: 3, repository: 'owner/repo', sha, ref: 'refs/heads/main', runId: 1, runAttempt: 1};

test('single-main proof binds the exact commit, including CRLF transport', () => {
  assert.equal(validateBranchProof(proof, sha), true);
  assert.equal(validateBranchProof(proof.replace('\n', '\r\n'), sha), true);
  assert.equal(validateBranchProof(proof, 'b'.repeat(40)), false);
});
for (const invalid of ['', null, `${sha} refs/heads/dev`, `${sha} refs/tags/main`, `${sha} refs/heads/main extra`, proof + proof, proof + `${sha} refs/heads/work\n`, 'refs/heads/main']) {
  test(`invalid branch proof fails closed: ${JSON.stringify(invalid)}`, () => {
    assert.equal(validateBranchProof(invalid, sha), false);
  });
}
test('manual-main and push-main use the same permanent branch gate', () => {
  const workflow = readFileSync(new URL('../../.github/workflows/ci.yml', import.meta.url), 'utf8');
  assert.match(workflow, /name: Prove main is the sole remote branch\n\s+if: github.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /validateBranchProof/);
  assert.doesNotMatch(workflow, /wc -l < artifacts\/branch-proof/);
});
test('context binds repository, exact SHA and ref independently of the receipt', () => {
  assert.equal(validCiContext(context, {sha, repository: 'owner/repo', ref: context.ref}), true);
  assert.equal(validCiContext({...context, ref: 'refs/pull/45/merge'}), true);
  assert.equal(validCiContext(context, {sha: 'b'.repeat(40)}), false);
  assert.equal(validCiContext(context, {repository: 'other/repo'}), false);
  assert.equal(validCiContext(context, {ref: 'refs/pull/45/merge'}), false);
});
test('context rejects another run or attempt for the same commit', () => {
  const identity = {sha, repository: context.repository, ref: context.ref, runId: 1, runAttempt: 1};
  assert.equal(validCiContext(context, identity), true);
  assert.equal(validCiContext(context, {...identity, runId: 2}), false);
  assert.equal(validCiContext(context, {...identity, runAttempt: 2}), false);
});
for (const delta of [{}, {sha: 'local-worktree'}, {runId: true}, {runAttempt: 0}, {ref: ''}, {repository: 'local'}, {schemaVersion: '3'}]) {
  test(`malformed or incomplete CI context: ${JSON.stringify(delta)}`, () => {
    assert.equal(validCiContext(Object.keys(delta).length ? {...context, ...delta} : {}), false);
  });
}
test('PASS text cannot replace complete core gate evidence', () => {
  const base = {schemaVersion: 1, status: 'PASS', gates: [...REQUIRED_CORE_GATES]};
  assert.equal(validCoreGates(base, false), true);
  assert.equal(validCoreGates(base, true), false);
  assert.equal(validCoreGates({...base, gates: [...base.gates, 'single-main-branch']}, true), true);
  assert.equal(validCoreGates({...base, gates: []}, false), false);
  assert.equal(validCoreGates({...base, gates: [...base.gates, base.gates[0]]}, false), false);
  for (const omitted of REQUIRED_CORE_GATES) {
    assert.equal(validCoreGates({...base, gates: base.gates.filter((gate) => gate !== omitted)}, false), false, omitted);
  }
});
test('explicit integer zero is the only passing high/critical audit count', () => {
  assert.equal(noHighAuditFindings({metadata: {vulnerabilities: {high: 0, critical: 0}}}), true);
  for (const invalid of [undefined, null, false, '0', -1, 0.5, NaN, Infinity, 1]) {
    assert.equal(noHighAuditFindings({metadata: {vulnerabilities: {high: invalid, critical: 0}}}), false);
    assert.equal(noHighAuditFindings({metadata: {vulnerabilities: {high: 0, critical: invalid}}}), false);
  }
  assert.equal(noHighAuditFindings({metadata: {vulnerabilities: {}}}), false);
});
test('test totals reconcile without Boolean or string coercion', () => {
  const valid = {success: true, numTotalTests: 2, numPassedTests: 2, numFailedTests: 0};
  assert.equal(validTestEvidence(valid), true);
  for (const delta of [{success: 'false'}, {numTotalTests: true}, {numPassedTests: 1}, {numFailedTests: '0'}, {numTotalTests: 0}, {numTotalTests: NaN}]) {
    assert.equal(validTestEvidence({...valid, ...delta}), false);
  }
});
test('missing build budgets are rejected rather than crashing or coercing', () => {
  const valid = {entry: {gzipBytes: 10}, echarts: {bytes: 20}, budgets: {entryGzipBytes: 10, echartsRawBytes: 20}};
  assert.equal(validBuildBudgets(valid), true);
  for (const invalid of [null, {}, {...valid, budgets: undefined}, {...valid, entry: {gzipBytes: true}}, {...valid, entry: {gzipBytes: 11}}, {...valid, echarts: {bytes: '20'}}, {...valid, budgets: {entryGzipBytes: Infinity, echartsRawBytes: 20}}]) {
    assert.equal(validBuildBudgets(invalid), false);
  }
});


function runReceipt(t, override = {}, prepare = () => {}) {
  const root = mkdtempSync(join(tmpdir(), 'resindb-receipt-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  mkdirSync(join(root, 'scripts'));
  mkdirSync(join(root, 'artifacts'));
  for (const name of ['generate-validation-receipt.mjs', 'validation-receipt-contract.mjs']) {
    copyFileSync(new URL(`../${name}`, import.meta.url), join(root, 'scripts', name));
  }
  const screenshots = Object.fromEntries(['dashboard', 'emptyState', 'productDetail', 'analytics', 'dependencyMap', 'dashboardEnDark', 'mobile'].map((scene, i) => [scene, `scene${i}.png`]));
  const fixtures = {
    'ci-context.json': context,
    'ci-gates.json': {schemaVersion: 1, status: 'PASS', gates: [...REQUIRED_CORE_GATES, 'single-main-branch']},
    'test-results.json': {success: true, numTotalTests: 1, numPassedTests: 1, numFailedTests: 0},
    'coverage-summary.json': {scopeComplete: true, coverageScope: 'production-typescript-excluding-tests-and-declarations'},
    'build-metrics.json': {entry: {gzipBytes: 10}, echarts: {bytes: 20}, budgets: {entryGzipBytes: 10, echartsRawBytes: 20}, externalResinDataBytes: 1},
    'ui-smoke-manifest.json': {screenshots},
    'npm-audit-prod.json': {metadata: {vulnerabilities: {high: 0, critical: 0}}},
    'npm-audit-all.json': {metadata: {vulnerabilities: {high: 0, critical: 0}}},
    'kmeans-backend-benchmark.json': {schemaVersion: 'kmeans-backend-benchmark-report-1.0.0', timingGate: 'informational-only', equivalence: {status: 'PASS'}, cases: [{equivalence: 'PASS'}], reportDigest: 'a'.repeat(64)},
    'compute-surface-audit.json': {acceptance: 'PASS', catalogModules: 26, workerFiles: 26},
    'scientific-ui-audit.json': {acceptance: 'PASS'},
  };
  for (const [name, value] of Object.entries(fixtures)) {
    writeFileSync(join(root, 'artifacts', name), JSON.stringify(value));
  }
  for (const file of Object.values(screenshots)) {
    // The receipt checks presence; real image validation belongs to Chromium CI.
    writeFileSync(join(root, 'artifacts', file), 'synthetic-presence-fixture');
  }
  writeFileSync(join(root, 'artifacts', 'branch-proof.txt'), proof);
  for (const [name, raw] of Object.entries(override)) {
    writeFileSync(join(root, 'artifacts', name), raw);
  }
  prepare(root);
  const result = spawnSync(process.execPath, [join(root, 'scripts/generate-validation-receipt.mjs')], {
    cwd: root,
    encoding: 'utf8',
    timeout: 5000,
    env: {...process.env, CI: '1', GITHUB_REPOSITORY: context.repository, GITHUB_SHA: sha, GITHUB_REF: context.ref, GITHUB_RUN_ID: String(context.runId), GITHUB_RUN_ATTEMPT: String(context.runAttempt)},
  });
  assert.equal(result.error, undefined);
  return {...result, root};
}

test('receipt CLI emits PASS only with a complete synthetic contract fixture', (t) => {
  const result = runReceipt(t);
  assert.equal(result.status, 0, result.stderr);
  const receipt = JSON.parse(readFileSync(join(result.root, 'artifacts/validation-receipt.json'), 'utf8'));
  assert.equal(receipt.acceptance, 'PASS');
  assert.equal(receipt.runId, context.runId);
  assert.equal(receipt.runAttempt, context.runAttempt);
  assert.equal(Object.values(receipt.checks).every((value) => value === true), true);
});

for (const field of ['runId', 'runAttempt']) {
  test(`receipt CLI rejects stale ${field} despite a matching commit`, (t) => {
    const stale = {...context, [field]: context[field] + 1};
    const result = runReceipt(t, {'ci-context.json': JSON.stringify(stale)});
    assert.equal(result.status, 1, result.stderr);
    const receipt = JSON.parse(readFileSync(join(result.root, 'artifacts/validation-receipt.json'), 'utf8'));
    assert.equal(receipt.acceptance, 'EVIDENCE_INCOMPLETE');
    assert.equal(receipt.checks.context, false);
  });
}

const requiredReports = {
  'ci-context.json': 'context',
  'ci-gates.json': 'coreGates',
  'test-results.json': 'tests',
  'coverage-summary.json': 'wholeSourceCoverage',
  'build-metrics.json': 'buildBudgets',
  'ui-smoke-manifest.json': 'uiEvidence',
  'npm-audit-prod.json': 'productionAudit',
  'npm-audit-all.json': 'completeAudit',
  'kmeans-backend-benchmark.json': 'kmeansBenchmarkEvidence',
  'compute-surface-audit.json': 'computeSurface',
  'scientific-ui-audit.json': 'scientificUi',
};
for (const [name, check] of Object.entries(requiredReports)) {
  for (const raw of ['null', '[]', 'false', '42', '"PASS"', '{malformed']) {
    test(`receipt CLI rejects ${name} with non-object or malformed JSON: ${raw}`, (t) => {
      const result = runReceipt(t, {[name]: raw});
      assert.equal(result.status, 1);
      assert.match(result.stdout, /Validation receipt: EVIDENCE_INCOMPLETE/);
      assert.doesNotMatch(result.stderr, /TypeError|SyntaxError/);
      const receipt = JSON.parse(readFileSync(join(result.root, 'artifacts/validation-receipt.json'), 'utf8'));
      assert.equal(receipt.acceptance, 'EVIDENCE_INCOMPLETE');
      assert.equal(receipt.checks[check], false);
    });
  }
}

const sceneNames = ['dashboard', 'emptyState', 'productDetail', 'analytics', 'dependencyMap', 'dashboardEnDark', 'mobile'];
const sceneManifest = () => Object.fromEntries(sceneNames.map((scene, i) => [scene, `scene${i}.png`]));

for (const [label, screenshots] of [
  ['array instead of a scene map', Array.from({length: 7}, (_, i) => `scene${i}.png`)],
  ['unrecognized scenes instead of required scenes', Object.fromEntries(Array.from({length: 7}, (_, i) => [`unknown${i}`, `scene${i}.png`]))],
  ['the same file reused for every scene', Object.fromEntries(sceneNames.map((scene) => [scene, 'scene0.png']))],
  ['parent traversal to existing files', Object.fromEntries(sceneNames.map((scene, i) => [scene, `../artifacts/scene${i}.png`]))],
  ['directories instead of screenshots', Object.fromEntries(sceneNames.map((scene) => [scene, '.']))],
  ['numeric worker counts', null],
]) {
  test(`receipt rejects invalid nested evidence: ${label}`, (t) => {
    const override = screenshots === null
      ? {'compute-surface-audit.json': JSON.stringify({acceptance: 'PASS', catalogModules: '26', workerFiles: '26'})}
      : {'ui-smoke-manifest.json': JSON.stringify({screenshots})};
    const result = runReceipt(t, override);
    assert.equal(result.status, 1, result.stdout);
    const receipt = JSON.parse(readFileSync(join(result.root, 'artifacts/validation-receipt.json'), 'utf8'));
    assert.equal(receipt.acceptance, 'EVIDENCE_INCOMPLETE');
    assert.equal(receipt.checks[screenshots === null ? 'computeSurface' : 'uiEvidence'], false);
  });
}

for (const kind of ['empty', 'directory', 'symlink', 'outside-absolute', 'wrong-extension']) {
  test(`receipt requires nonempty regular in-artifact PNG paths: ${kind}`, (t) => {
    const screenshots = sceneManifest();
    if (kind === 'wrong-extension') screenshots.dashboard = 'ci-context.json';
    const result = runReceipt(t, {'ui-smoke-manifest.json': JSON.stringify({screenshots})}, (root) => {
      const image = join(root, 'artifacts/scene0.png');
      if (kind === 'outside-absolute') {
        screenshots.dashboard = image;
        writeFileSync(join(root, 'artifacts/ui-smoke-manifest.json'), JSON.stringify({screenshots}));
      } else if (kind !== 'wrong-extension') {
        rmSync(image);
        if (kind === 'empty') writeFileSync(image, '');
        if (kind === 'directory') mkdirSync(image);
        if (kind === 'symlink') symlinkSync('scene1.png', image);
      }
    });
    assert.equal(result.status, 1, result.stdout);
    const receipt = JSON.parse(readFileSync(join(result.root, 'artifacts/validation-receipt.json'), 'utf8'));
    assert.equal(receipt.checks.uiEvidence, false);
    assert.doesNotMatch(result.stderr, /TypeError|SyntaxError/);
  });
}
