import { describe, expect, it } from 'vitest';
import { calculateTopsis, calculateTopsisDetailed } from '@/lib/topsisAnalyzer';

type Row = { id: string; cost?: number; benefit?: number };
const columns = [
  { key: 'cost', isLowBest: true, unit: 'USD/kg' },
  { key: 'benefit', isLowBest: false, unit: 'MPa' },
];
const value = (row: Row, key: string) => {
  const result = row[key as 'cost' | 'benefit'];
  return typeof result === 'number' ? result : null;
};

describe('TOPSIS missing-data contract', () => {
  it('excludes missing criteria instead of rewarding zero cost', () => {
    const rows: Row[] = [
      { id: 'complete', cost: 10, benefit: 10 },
      { id: 'missing-cost', benefit: 10 },
      { id: 'comparison', cost: 20, benefit: 8 },
    ];
    const analysis = calculateTopsisDetailed(rows, columns, value);
    expect(analysis.scores.has('complete')).toBe(true);
    expect(analysis.scores.has('missing-cost')).toBe(false);
    expect(analysis.alternatives.find((item) => item.id === 'missing-cost')).toMatchObject({
      eligible: false,
      score: null,
    });
  });

  it('does not improve ranking when a cost value is deleted', () => {
    const complete: Row[] = [
      { id: 'candidate', cost: 10, benefit: 10 },
      { id: 'other', cost: 20, benefit: 9 },
    ];
    const missing: Row[] = [
      { id: 'candidate', benefit: 10 },
      { id: 'other', cost: 20, benefit: 9 },
    ];
    expect(calculateTopsis(complete, columns, value).has('candidate')).toBe(true);
    expect(calculateTopsis(missing, columns, value).has('candidate')).toBe(false);
  });

  it('requires provenance for explicit imputation', () => {
    expect(() => calculateTopsisDetailed(
      [{ id: 'a' }],
      [{ key: 'cost', isLowBest: true, missingPolicy: 'IMPUTE', imputation: { value: 5, provenanceRefs: [] } }],
      value,
    )).toThrow('Imputation provenance required');
  });

  it('rejects duplicate alternative ids and invalid weights', () => {
    expect(() => calculateTopsisDetailed(
      [{ id: 'a', cost: 1 }, { id: 'a', cost: 2 }],
      [{ key: 'cost', isLowBest: true }],
      value,
    )).toThrow('Duplicate or empty');
    expect(() => calculateTopsisDetailed(
      [{ id: 'a', cost: 1 }],
      [{ key: 'cost', isLowBest: true, weight: -1 }],
      value,
    )).toThrow('Invalid TOPSIS weight');
  });

  it('handles constant columns deterministically', () => {
    const analysis = calculateTopsisDetailed(
      [{ id: 'a', cost: 1 }, { id: 'b', cost: 1 }],
      [{ key: 'cost', isLowBest: true }],
      value,
    );
    expect(analysis.scores.get('a')).toBe(0.5);
    expect(analysis.scores.get('b')).toBe(0.5);
  });
});
