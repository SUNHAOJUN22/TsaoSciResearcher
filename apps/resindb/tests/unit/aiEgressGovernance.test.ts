import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');

describe('AI egress source governance', () => {
  it('contains no browser secret persistence or external provider fetch', () => {
    const service = readFileSync(resolve(root, 'src/services/aiService.ts'), 'utf8');
    const governance = readFileSync(resolve(root, 'src/services/aiGovernance.ts'), 'utf8');
    expect(service).not.toContain('VITE_AI_API_KEY');
    expect(service).not.toContain('VITE_AI_API_ENDPOINT');
    expect(service).not.toContain('Authorization:');
    expect(service).not.toContain('Bearer ');
    expect(governance).toContain("GOVERNED_AI_PROXY_PATH = '/api/ai/proxy'");
    expect(governance).toContain('MAX_AI_REQUEST_BYTES = 64 * 1024');
  });

  it('does not retain remediation transport in the review tree', () => {
    const workflows = readdirSync(resolve(root, '.github/workflows'));
    expect(workflows.filter((name) => name.startsWith('remediation-'))).toEqual([]);
  });
});
