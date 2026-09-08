import { describe, expect, it } from 'vitest';
import { buildSpearmanPayload } from '@/lib/spearmanPayload';
import type { Product } from '@/types/index';

describe('Spearman payload construction', () => {
  it('omits unknown and invalid observations instead of inventing zeroes', () => {
    const product = {
      id: 'p-1',
      properties: {
        validNumber: { value: 2.5 },
        validText: { value: '-1.25e2' },
        physicalZero: { value: 0 },
        blank: { value: '   ' },
        partial: { value: '12 MPa' },
        boolean: { value: true },
        missing: { value: null },
        nan: { value: Number.NaN },
        infinity: { value: Number.POSITIVE_INFINITY },
      },
    } as unknown as Product;

    expect(buildSpearmanPayload([product], [
      'validNumber',
      'validText',
      'physicalZero',
      'blank',
      'partial',
      'boolean',
      'missing',
      'nan',
      'infinity',
      'absent',
    ])).toEqual([{
      id: 'p-1',
      values: {
        validNumber: 2.5,
        validText: -125,
        physicalZero: 0,
      },
    }]);
  });

  it('does not mutate products or key arrays', () => {
    const product = {
      id: 'p-2',
      properties: { a: { value: '1' }, b: { value: '2' } },
    } as unknown as Product;
    const keys = ['a', 'b'];
    const before = JSON.stringify(product);

    expect(buildSpearmanPayload([product], keys)).toEqual([
      { id: 'p-2', values: { a: 1, b: 2 } },
    ]);
    expect(JSON.stringify(product)).toBe(before);
    expect(keys).toEqual(['a', 'b']);
  });
});
