import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

interface ComputeModule {
  id: string;
  worker: string;
  inputContract: string;
  outputContract: string;
  mathematicalContract: string;
  scientificBoundary: string;
}

describe('compute module catalog', () => {
  it('documents every worker with unique identifiers and explicit contracts', () => {
    const catalog = JSON.parse(
      readFileSync('docs/compute-module-catalog.json', 'utf8'),
    ) as { schemaVersion: string; modules: ComputeModule[] };
    expect(catalog.schemaVersion).toBe('resindb-compute-catalog-1.0.0');
    expect(catalog.modules).toHaveLength(26);
    expect(new Set(catalog.modules.map((module) => module.id)).size).toBe(26);
    expect(new Set(catalog.modules.map((module) => module.worker)).size).toBe(26);
    for (const module of catalog.modules) {
      expect(module.inputContract.length).toBeGreaterThan(10);
      expect(module.outputContract.length).toBeGreaterThan(10);
      expect(module.mathematicalContract.length).toBeGreaterThan(5);
      expect(module.scientificBoundary.length).toBeGreaterThan(10);
    }
  });
});
