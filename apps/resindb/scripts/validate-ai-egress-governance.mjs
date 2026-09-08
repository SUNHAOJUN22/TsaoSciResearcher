import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const productionRoots = [resolve(root, 'src')];
const failures = [];
const forbidden = [
  ['browser API key environment', /VITE_AI_API_KEY/g],
  ['browser endpoint environment', /VITE_AI_API_ENDPOINT/g],
  ['browser bearer header', /Authorization\s*:/g],
  ['browser bearer token', /Bearer\s+/g],
  ['direct external AI endpoint', /https?:\/\/(?:api\.)?(?:openai|anthropic|googleapis|deepseek)\./gi],
];

function walk(directory) {
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (/\.(?:ts|tsx|js|jsx)$/.test(name)) {
      const text = readFileSync(path, 'utf8');
      for (const [label, pattern] of forbidden) {
        pattern.lastIndex = 0;
        if (pattern.test(text)) failures.push(`${relative(root, path)}: ${label}`);
      }
    }
  }
}

for (const directory of productionRoots) walk(directory);
const governance = readFileSync(resolve(root, 'src/services/aiGovernance.ts'), 'utf8');
for (const required of ["GOVERNED_AI_PROXY_PATH = '/api/ai/proxy'", 'MAX_AI_REQUEST_BYTES = 64 * 1024', 'validateAiAuthorization', 'buildAiAuditRecord']) {
  if (!governance.includes(required)) failures.push(`aiGovernance.ts missing ${required}`);
}
if (failures.length) {
  console.error(JSON.stringify({ acceptance: 'FAIL', failures }, null, 2));
  process.exit(1);
}
console.log(JSON.stringify({ acceptance: 'PASS', scannedRoots: productionRoots.map((path) => relative(root, path)) }));
