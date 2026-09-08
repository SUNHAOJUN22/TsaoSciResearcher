const fs = require('node:fs'); const path = require('node:path'); const vm = require('node:vm');
const assert = require('node:assert/strict'); const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const ts = require(require.resolve('typescript', { paths: [path.join(root, 'apps/resindb'), ...module.paths] }));
const source = fs.readFileSync(path.join(root, 'apps/resindb/src/sharedCanonical.ts'), 'utf8');
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const exported = {}; vm.runInNewContext(output, { exports: exported, module: { exports: exported }, TextEncoder }, { timeout: 1000 });
const vectors = JSON.parse(fs.readFileSync(path.join(root, 'contracts/canonical-vectors.json'), 'utf8'));
for (const entry of vectors.vectors) {
  const bytes = Buffer.from(exported.canonicalBytes(entry.value));
  assert.equal(bytes.toString('hex'), entry.bytes_hex);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), entry.sha256);
}
console.log(JSON.stringify({ test: 'cross-language-canonical-identity', passed: vectors.vectors.length }));
