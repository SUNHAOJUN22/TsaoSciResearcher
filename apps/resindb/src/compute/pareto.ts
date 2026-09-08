export type ParetoDirection = 'minimize' | 'maximize';

function validatePoints(
  points: readonly (readonly number[])[],
  directions: readonly ParetoDirection[],
): void {
  if (directions.length === 0) throw new RangeError('Pareto analysis requires objectives');
  for (const point of points) {
    if (point.length !== directions.length) throw new RangeError('Pareto point dimensions must match objectives');
    for (const value of point) {
      if (!Number.isFinite(value)) throw new TypeError('Pareto points must contain finite numbers');
    }
  }
}

function transformedValue(value: number, direction: ParetoDirection): number {
  return direction === 'minimize' ? value : -value;
}

export function paretoDominates(
  left: readonly number[],
  right: readonly number[],
  directions: readonly ParetoDirection[],
): boolean {
  let strictlyBetter = false;
  for (let objective = 0; objective < directions.length; objective++) {
    const leftValue = transformedValue(left[objective], directions[objective]);
    const rightValue = transformedValue(right[objective], directions[objective]);
    if (leftValue > rightValue) return false;
    if (leftValue < rightValue) strictlyBetter = true;
  }
  return strictlyBetter;
}

function twoObjectiveFront(
  points: readonly (readonly number[])[],
  directions: readonly ParetoDirection[],
): number[] {
  const order = Array.from({ length: points.length }, (_, index) => index);
  order.sort((leftIndex, rightIndex) => {
    const leftX = transformedValue(points[leftIndex][0], directions[0]);
    const rightX = transformedValue(points[rightIndex][0], directions[0]);
    if (leftX !== rightX) return leftX - rightX;
    const leftY = transformedValue(points[leftIndex][1], directions[1]);
    const rightY = transformedValue(points[rightIndex][1], directions[1]);
    return leftY - rightY;
  });

  const front: number[] = [];
  let bestPreviousY = Infinity;
  let cursor = 0;
  while (cursor < order.length) {
    const groupX = transformedValue(points[order[cursor]][0], directions[0]);
    let groupEnd = cursor + 1;
    let groupBestY = transformedValue(points[order[cursor]][1], directions[1]);
    while (
      groupEnd < order.length
      && transformedValue(points[order[groupEnd]][0], directions[0]) === groupX
    ) {
      groupBestY = Math.min(
        groupBestY,
        transformedValue(points[order[groupEnd]][1], directions[1]),
      );
      groupEnd += 1;
    }
    if (groupBestY < bestPreviousY) {
      for (let index = cursor; index < groupEnd; index++) {
        const pointIndex = order[index];
        if (transformedValue(points[pointIndex][1], directions[1]) === groupBestY) {
          front.push(pointIndex);
        }
      }
      bestPreviousY = groupBestY;
    }
    cursor = groupEnd;
  }
  return front;
}

function incrementalFront(
  points: readonly (readonly number[])[],
  directions: readonly ParetoDirection[],
): number[] {
  const front: number[] = [];
  for (let candidate = 0; candidate < points.length; candidate++) {
    let dominated = false;
    for (const current of front) {
      if (paretoDominates(points[current], points[candidate], directions)) {
        dominated = true;
        break;
      }
    }
    if (dominated) continue;
    for (let index = front.length - 1; index >= 0; index--) {
      if (paretoDominates(points[candidate], points[front[index]], directions)) {
        front.splice(index, 1);
      }
    }
    front.push(candidate);
  }
  return front;
}

export function paretoFrontIndices(
  points: readonly (readonly number[])[],
  directions: readonly ParetoDirection[],
): number[] {
  validatePoints(points, directions);
  if (points.length === 0) return [];
  return directions.length === 2
    ? twoObjectiveFront(points, directions)
    : incrementalFront(points, directions);
}
