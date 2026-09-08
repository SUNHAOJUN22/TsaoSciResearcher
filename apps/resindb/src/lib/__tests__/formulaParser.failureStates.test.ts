import { describe, expect, it } from 'vitest';
import { FormulaEngine } from '@/lib/formulaParser';
import type { FormulaConfig, Product } from '@/types/index';

const product = (properties: Product['properties']): Product => ({
  id: 'P-1', gradeName: 'Example', manufacturerId: 'M-1', manufacturer: 'M',
  categoryIds: ['C-1'], createdAt: '2026-08-12', updatedAt: '2026-08-12', properties,
});

describe('FormulaEngine structured failure states', () => {
  it('returns UNKNOWN for a missing dependency instead of zero', () => {
    const engine = new FormulaEngine();
    const formulas: FormulaConfig[] = [{ id: 'F-1', name: 'Specific', expression: "props['A'] / props['B']", unit: 'MPa' }];
    const result = engine.compileResultGraph(formulas)(product({ A: { value: 5 } }));
    expect(result['F-1'].status).toBe('UNKNOWN');
    expect(result['F-1'].value).toBeNull();
    expect(engine.compileGraph(formulas)(product({ A: { value: 5 } }))).not.toHaveProperty('F-1');
  });

  it('keeps a real zero as OK', () => {
    const engine = new FormulaEngine();
    const result = engine.compileResultGraph([
      { id: 'F-0', name: 'Zero', expression: "props['A'] - props['A']", unit: 'MPa' },
    ])(product({ A: { value: 5 } }));
    expect(result['F-0']).toMatchObject({ status: 'OK', value: 0 });
  });

  it('returns INVALID for domain/non-finite errors', () => {
    const engine = new FormulaEngine();
    const result = engine.compileResultGraph([
      { id: 'F-DIV', name: 'Div', expression: "props['A'] / props['B']", unit: '1' },
    ])(product({ A: { value: 1 }, B: { value: 0 } }));
    expect(result['F-DIV'].status).toBe('INVALID');
    expect(result['F-DIV'].value).toBeNull();
  });

  it('returns INVALID for a cycle and for missing output units', () => {
    const engine = new FormulaEngine();
    const cycle = engine.compileResultGraph([
      { id: 'F-A', name: 'A', expression: "props['B'] + 1", unit: '1' },
      { id: 'F-B', name: 'B', expression: "props['A'] + 1", unit: '1' },
    ])(product({}));
    expect(cycle['F-A'].status).toBe('INVALID');
    expect(cycle['F-B'].status).toBe('INVALID');

    engine.clearCache();
    const noUnit = engine.compileResultGraph([
      { id: 'F-U', name: 'NoUnit', expression: "props['A'] + 1" },
    ])(product({ A: { value: 1 } }));
    expect(noUnit['F-U']).toMatchObject({ status: 'INVALID', value: null, reason: 'MISSING_OUTPUT_UNIT' });
  });
});
