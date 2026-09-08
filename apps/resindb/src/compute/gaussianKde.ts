const SQRT_TWO_PI = Math.sqrt(2 * Math.PI);

export interface GaussianKdePoint {
  x: number;
  y: number;
}

/**
 * Exact direct one-dimensional Gaussian KDE on an evenly spaced output grid.
 * Fixed bandwidth and normalization terms are hoisted outside the O(nm)
 * kernel loop; the estimator and output grid are unchanged.
 */
export function calculateGaussianKde(
  data: ArrayLike<number>,
  bandwidth: number,
  steps = 100,
): GaussianKdePoint[] {
  if (data.length === 0) return [];
  const safeSteps = Number.isInteger(steps) && steps > 0 ? steps : 100;
  let min = data[0];
  let max = data[0];
  for (let index = 1; index < data.length; index++) {
    const value = data[index];
    if (value < min) min = value;
    if (value > max) max = value;
  }

  const fallbackScale = Math.max(Math.abs(min), Math.abs(max), 1) * 1e-6;
  const safeBandwidth = Math.abs(bandwidth) > 1e-15 ? Math.abs(bandwidth) : fallbackScale;
  const margin = (max - min) * 0.1 || safeBandwidth * 3;
  min -= margin;
  max += margin;
  const span = max - min;
  const kernelExponentScale = -0.5 / (safeBandwidth * safeBandwidth);
  const densityScale = 1 / (data.length * safeBandwidth * SQRT_TWO_PI);
  const kde = new Array<GaussianKdePoint>(safeSteps + 1);

  for (let step = 0; step <= safeSteps; step++) {
    const x = min + (step / safeSteps) * span;
    let kernelSum = 0;
    for (let index = 0; index < data.length; index++) {
      const difference = x - data[index];
      kernelSum += Math.exp(difference * difference * kernelExponentScale);
    }
    kde[step] = { x, y: kernelSum * densityScale };
  }
  return kde;
}
