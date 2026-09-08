/* Regression against the actual TypeScript implementation, with no external network. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { webcrypto, createHash } = require('node:crypto');
const root = path.resolve(__dirname, '..');
const ts = require(require.resolve('typescript', { paths: [path.join(root, 'apps/resindb'), ...module.paths] }));
const source = fs.readFileSync(path.join(root, 'apps/resindb/src/services/aiGovernance.ts'), 'utf8');
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
let audit;
const exported = {};
const context = { exports: exported, module: { exports: exported }, TextEncoder, crypto: webcrypto,
  require: (name) => {
    if (name !== '@/lib/logger') throw new Error('unexpected import');
    return { logger: { info: (_, value) => { audit = value; } } };
  },
};
vm.runInNewContext(output, context, { timeout: 1000 });
(async () => {
  for (let index = 0; index < 5; index++) {
    const payload = { density: 0.9, nested: { temperature: 25 } };
    let sent;
    const pending = exported.governedAiFetch({ model: 'test-only', purpose: 'material-summary', payload,
      fetchImpl: async (target, options) => { sent = { target, options }; return {}; } });
    payload.manufacturer = 'SYNTHETIC-FORBIDDEN-TEST';
    payload.nested.grade = 'SYNTHETIC-FORBIDDEN-TEST';
    payload.excess = 'x'.repeat(70000);
    await pending;
    const body = sent.options.body;
    assert.equal(sent.target, '/api/ai/proxy');
    assert.deepEqual(JSON.parse(body).payload, { density: 0.9, nested: { temperature: 25 } });
    assert.equal(audit.payloadSha256, createHash('sha256').update(body).digest('hex'));
    assert.equal(audit.payloadBytes, Buffer.byteLength(body));
    assert.equal(sent.options.headers.Authorization, undefined);
  }
  console.log(JSON.stringify({ test: 'actual-TypeScript-immutable-egress', passed: 5, network_requests: 0 }));
})().catch((error) => { console.error(error); process.exitCode = 1; });
