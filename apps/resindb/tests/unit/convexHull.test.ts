import { describe, expect, it } from 'vitest';
import { grahamScan, type Point2D } from '@/lib/math/convexHull';

function coordinates(points: Point2D[]): Array<[number, number]> {
  return points.map((point) => [point.x, point.y]);
}

describe('deterministic convex hull', () => {
  it('returns the counter-clockwise square boundary once despite duplicates', () => {
    const points: Point2D[] = [
      { x: 1, y: 1, id: 'top-right' },
      { x: 0, y: 0, id: 'bottom-left-first' },
      { x: 1, y: 0, id: 'bottom-right' },
      { x: 0, y: 1, id: 'top-left' },
      { x: 0, y: 0, id: 'bottom-left-duplicate' },
      { x: 0.5, y: 0.5, id: 'interior' },
    ];

    const hull = grahamScan(points);

    expect(coordinates(hull)).toEqual([
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ]);
    expect(hull[0].id).toBe('bottom-left-first');
  });

  it('reduces an all-collinear cloud to the two extreme endpoints', () => {
    expect(coordinates(grahamScan([
      { x: 2, y: 2 },
      { x: 0, y: 0 },
      { x: 3, y: 3 },
      { x: 1, y: 1 },
    ]))).toEqual([[0, 0], [3, 3]]);
  });

  it('treats scale-level floating noise as collinear instead of creating a false vertex', () => {
    const hull = grahamScan([
      { x: 0, y: 0 },
      { x: 1, y: 1 + 1e-15 },
      { x: 2, y: 2 },
      { x: 1, y: 0 },
    ]);

    expect(coordinates(hull)).toEqual([
      [0, 0],
      [1, 0],
      [2, 2],
    ]);
  });

  it('filters non-finite points and handles fewer than three unique coordinates', () => {
    expect(coordinates(grahamScan([
      { x: Number.NaN, y: 1 },
      { x: 2, y: 2 },
      { x: 1, y: 1 },
      { x: Number.POSITIVE_INFINITY, y: 0 },
      { x: 1, y: 1 },
    ]))).toEqual([[1, 1], [2, 2]]);
  });

  it('does not reorder or mutate the caller array or point objects', () => {
    const points: Point2D[] = [
      { x: 2, y: 0, id: 'a', data: { label: 'A' } },
      { x: 0, y: 0, id: 'b', data: { label: 'B' } },
      { x: 1, y: 2, id: 'c', data: { label: 'C' } },
    ];
    const snapshot = structuredClone(points);

    grahamScan(points);

    expect(points).toEqual(snapshot);
  });

  it('returns the same ordered hull for every input permutation', () => {
    const points: Point2D[] = [
      { x: 0, y: 0 },
      { x: 2, y: 0 },
      { x: 2, y: 2 },
      { x: 0, y: 2 },
      { x: 1, y: 1 },
    ];
    const expected = coordinates(grahamScan(points));
    const reversed = coordinates(grahamScan([...points].reverse()));
    const rotated = coordinates(grahamScan([...points.slice(2), ...points.slice(0, 2)]));

    expect(reversed).toEqual(expected);
    expect(rotated).toEqual(expected);
  });
});
