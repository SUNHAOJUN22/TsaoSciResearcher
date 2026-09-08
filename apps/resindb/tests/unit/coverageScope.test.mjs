import { describe, expect, it } from 'vitest';

import {
  isProductionTypeScriptFile,
  normalizeRepositoryPath,
} from '../../scripts/coverage-scope.mjs';

describe('whole-source coverage scope', () => {
  it('includes runtime TypeScript and TSX production modules', () => {
    expect(isProductionTypeScriptFile('src/lib/quantityRecord.ts')).toBe(true);
    expect(isProductionTypeScriptFile('src/components/App.tsx')).toBe(true);
    expect(isProductionTypeScriptFile('src/lib/latest.ts')).toBe(true);
  });

  it('excludes declarations, tests, specs and fixture-only test directories', () => {
    const excluded = [
      'src/types/generated.d.ts',
      'src/lib/quantityRecord.test.ts',
      'src/lib/quantityRecord.spec.tsx',
      'src/lib/__tests__/quantityRecord.contract.test.ts',
      'src/lib/__mocks__/quantityRecord.ts',
    ];
    for (const filePath of excluded) {
      expect(isProductionTypeScriptFile(filePath), filePath).toBe(false);
    }
  });

  it('normalizes Windows and POSIX repository paths consistently', () => {
    expect(normalizeRepositoryPath('src\\lib\\quantityRecord.ts')).toBe('src/lib/quantityRecord.ts');
    expect(isProductionTypeScriptFile('src\\lib\\__tests__\\quantityRecord.test.ts')).toBe(false);
  });

  it('does not confuse ordinary names containing the word test with test modules', () => {
    expect(isProductionTypeScriptFile('src/lib/latestResult.ts')).toBe(true);
    expect(isProductionTypeScriptFile('src/components/TestIndicator.tsx')).toBe(true);
  });
});
