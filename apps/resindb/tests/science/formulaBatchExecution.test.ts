import { describe, expect, it } from 'vitest';
import { FormulaEngine } from '@/lib/formulaParser';
import type { FormulaConfig, Product } from '@/types/index';

const formulas: FormulaConfig[] = [
  { id: 'derived', name: 'Derived', expression: "Props['A'] * 2", unit: '' },
  { id: 'combined', name: 'Combined', expression: "Props['Derived'] + Props['B']", unit: '' },
];

const product: Product = {
  id: 'formula-batch',
  gradeName: 'Formula batch',
  manufacturer: 'Test',
  manufacturerId: 'test',
  categoryIds: [],
  createdAt: '2026-01-01',
  updatedAt: '2026-01-01',
  properties: {
    A: { value: 3 },
    B: { value: 5 },
  },
};

describe('reusable numeric formula execution', () => {
  it('matches Product execution and reuses the supplied result object', () => {
    const engine = new FormulaEngine();
    const productResult = engine.compileGraph(formulas)(product);
    const properties = engine.createPropertyDictionary(product);
    const reusableResults: Record<string, number> = {};
    const numericExecutor = engine.compilePropertyGraph(formulas);

    const first = numericExecutor(properties, reusableResults);
    expect(first).toBe(reusableResults);
    expect(first).toEqual(productResult);

    properties.A = 4;
    const second = numericExecutor(properties, reusableResults);
    expect(second).toBe(reusableResults);
    expect(second).toEqual({ derived: 8, combined: 13 });
  });

  it('supports explicit restoration when a base property shares a formula name', () => {
    const engine = new FormulaEngine();
    const collidingFormulas: FormulaConfig[] = [
      { id: 'derived', name: 'Derived', expression: "Props['A'] * 3", unit: '' },
      { id: 'final', name: 'Final', expression: "Props['Derived'] + Props['A']", unit: '' },
    ];
    const numericExecutor = engine.compilePropertyGraph(collidingFormulas);
    const properties = { A: 2, Derived: 100 };
    const results: Record<string, number> = {};

    numericExecutor(properties, results);
    expect(results).toEqual({ derived: 6, final: 8 });

    properties.A = 4;
    properties.Derived = 100;
    numericExecutor(properties, results);
    expect(results).toEqual({ derived: 12, final: 16 });
  });
});
