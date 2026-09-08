import { describe, expect, it } from 'vitest';
import { createKMeansAssignmentSession } from '@/compute/kmeansAssignment';

describe('K-Means assignment numerical boundaries', () => {
  it.each([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    'rejects a non-finite matrix value: %s',
    (invalidValue) => {
      expect(() => createKMeansAssignmentSession({
        matrix: new Float64Array([0, 0, invalidValue, 1]),
        sampleCount: 2,
        dimensions: 2,
        maxClusters: 2,
      })).toThrow('matrix must contain only finite values');
    },
  );

  it('rejects non-finite centroids before either backend executes', () => {
    const session = createKMeansAssignmentSession({
      matrix: new Float64Array([0, 0, 1, 1]),
      sampleCount: 2,
      dimensions: 2,
      maxClusters: 2,
      preference: 'typescript',
    });
    const assignments = new Int32Array(2);
    assignments.fill(-1);
    expect(() => session.assignAndAccumulate(
      new Float64Array([0, 0, Number.POSITIVE_INFINITY, 1]),
      2,
      assignments,
      new Float64Array(4),
      new Uint32Array(2),
    )).toThrow('centroids must contain only finite values');
  });
});
