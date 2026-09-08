export interface Point2D {
  x: number;
  y: number;
  id?: string;
  data?: unknown;
}

interface IndexedPoint {
  point: Point2D;
  index: number;
}

function orientation(first: Point2D, second: Point2D, third: Point2D): number {
  const ax = second.x - first.x;
  const ay = second.y - first.y;
  const bx = third.x - first.x;
  const by = third.y - first.y;
  const cross = ax * by - ay * bx;
  const scale = Math.abs(ax * by) + Math.abs(ay * bx);
  const tolerance = Number.EPSILON * Math.max(1, scale) * 32;
  if (Math.abs(cross) <= tolerance) return 0;
  return cross;
}

/**
 * Deterministic convex hull with the same public API as the former Graham scan.
 *
 * The implementation uses Andrew's monotone chain because lexicographic sorting
 * makes duplicate removal, all-collinear inputs and deterministic ordering
 * explicit. Collinear interior points are omitted; endpoints are retained.
 */
export function grahamScan(points: readonly Point2D[]): Point2D[] {
  const sorted: IndexedPoint[] = [];
  for (let index = 0; index < points.length; index++) {
    const point = points[index];
    if (Number.isFinite(point.x) && Number.isFinite(point.y)) {
      sorted.push({ point, index });
    }
  }
  sorted.sort((left, right) => (
    left.point.x - right.point.x
    || left.point.y - right.point.y
    || left.index - right.index
  ));

  const unique: Point2D[] = [];
  for (const entry of sorted) {
    const previous = unique.at(-1);
    if (previous && previous.x === entry.point.x && previous.y === entry.point.y) continue;
    unique.push(entry.point);
  }
  if (unique.length <= 2) return unique;

  const lower: Point2D[] = [];
  for (const point of unique) {
    while (
      lower.length >= 2
      && orientation(lower[lower.length - 2], lower[lower.length - 1], point) <= 0
    ) {
      lower.pop();
    }
    lower.push(point);
  }

  const upper: Point2D[] = [];
  for (let index = unique.length - 1; index >= 0; index--) {
    const point = unique[index];
    while (
      upper.length >= 2
      && orientation(upper[upper.length - 2], upper[upper.length - 1], point) <= 0
    ) {
      upper.pop();
    }
    upper.push(point);
  }

  lower.pop();
  upper.pop();
  return lower.concat(upper);
}
