/**
 * Fill average ranks (1-based, ties receive their arithmetic mean rank) into a
 * caller-owned Float64Array. The reusable index workspace avoids allocating one
 * `{ value, index }` object per observation for every ranked feature.
 */
export function fillAverageRanks(
  values: ArrayLike<number>,
  output: Float64Array,
  orderWorkspace: number[],
): void {
  const length = values.length;
  if (output.length !== length || orderWorkspace.length !== length) {
    throw new RangeError('Average-rank buffers must match the input length');
  }

  for (let index = 0; index < length; index++) {
    if (!Number.isFinite(values[index])) {
      throw new TypeError('Average-rank input values must be finite');
    }
    orderWorkspace[index] = index;
  }
  orderWorkspace.sort((left, right) => {
    const difference = values[left] - values[right];
    return difference || left - right;
  });

  let cursor = 0;
  while (cursor < length) {
    const value = values[orderWorkspace[cursor]];
    let end = cursor + 1;
    while (end < length && values[orderWorkspace[end]] === value) end += 1;
    const averageRank = ((cursor + 1) + end) / 2;
    for (let index = cursor; index < end; index++) {
      output[orderWorkspace[index]] = averageRank;
    }
    cursor = end;
  }
}
