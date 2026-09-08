const SPC_MODEL_VERSION = 'normal-capability-sample-sigma-2.0.0';

export interface SpcMessage {
  type: 'CALCULATE_SPC';
  payload: {
    data: number[];
    usl: number;
    lsl: number;
  };
}

export interface SpcResponse {
  type: 'SPC_RESULT' | 'ERROR';
  payload?: {
    mean: number;
    sigma: number;
    cp: number;
    cpk: number;
    ppm: number;
    histogram: { x: number; y: number }[];
    normalCurve: { x: number; y: number }[];
    histogramBins: number[];
    status: 'success' | 'warning' | 'danger';
    modelVersion: typeof SPC_MODEL_VERSION;
    diagnostics: {
      observations: number;
      sigmaEstimator: 'sample-standard-deviation-n-minus-one';
      ppmAssumption: 'fitted-normal-distribution';
    };
  };
  error?: string;
}

function errorFunction(value: number): number {
  const sign = value >= 0 ? 1 : -1;
  const x = Math.abs(value);
  const t = 1 / (1 + 0.3275911 * x);
  const approximation = 1 - (
    (((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t
      + 0.254829592) * t) * Math.exp(-x * x)
  );
  return sign * approximation;
}

function normalCdf(value: number, mean: number, standardDeviation: number): number {
  return 0.5 * (1 + errorFunction(
    (value - mean) / (Math.SQRT2 * standardDeviation),
  ));
}

self.onmessage = (event: MessageEvent<SpcMessage>) => {
  try {
    const { data, usl, lsl } = event.data.payload;
    if (!Number.isFinite(usl) || !Number.isFinite(lsl) || usl <= lsl) {
      throw new Error('USL and LSL must be finite, with USL strictly greater than LSL.');
    }
    const validData = (data ?? []).filter(Number.isFinite);
    if (validData.length < 2) {
      throw new Error('Sample standard deviation requires at least two finite observations.');
    }
    const observations = validData.length;
    const mean = validData.reduce((sum, value) => sum + value, 0) / observations;
    let squaredDeviation = 0;
    let minimum = validData[0];
    let maximum = validData[0];
    for (const value of validData) {
      squaredDeviation += (value - mean) ** 2;
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }
    const sigma = Math.sqrt(squaredDeviation / (observations - 1));
    if (!(sigma > 0) || !Number.isFinite(sigma)) {
      throw new Error('Sample standard deviation is zero or invalid.');
    }

    const cp = (usl - lsl) / (6 * sigma);
    const cpk = Math.min((usl - mean) / (3 * sigma), (mean - lsl) / (3 * sigma));
    const lowerTail = normalCdf(lsl, mean, sigma);
    const upperTail = 1 - normalCdf(usl, mean, sigma);
    const ppm = Math.max(0, Math.min(1_000_000, (lowerTail + upperTail) * 1_000_000));
    const status: 'success' | 'warning' | 'danger' = cpk >= 1.33
      ? 'success'
      : cpk >= 1
        ? 'warning'
        : 'danger';

    const minData = Math.min(minimum, lsl - 1.5 * sigma);
    const maxData = Math.max(maximum, usl + 1.5 * sigma);
    const binCount = Math.max(7, Math.ceil(1 + 3.322 * Math.log10(observations)));
    const binWidth = (maxData - minData) / binCount;
    const histogramCounts = new Array<number>(binCount).fill(0);
    for (const value of validData) {
      const rawIndex = Math.floor((value - minData) / binWidth);
      const binIndex = Math.max(0, Math.min(binCount - 1, rawIndex));
      histogramCounts[binIndex] += 1;
    }
    const histogram: { x: number; y: number }[] = [];
    const histogramBins: number[] = [];
    for (let index = 0; index < binCount; index++) {
      const x = minData + (index + 0.5) * binWidth;
      histogram.push({ x, y: histogramCounts[index] });
      histogramBins.push(x);
    }

    const normalCurve: { x: number; y: number }[] = [];
    const curvePoints = 150;
    const scale = observations * binWidth;
    for (let index = 0; index <= curvePoints; index++) {
      const x = minData + (index / curvePoints) * (maxData - minData);
      const standardized = (x - mean) / sigma;
      const density = Math.exp(-0.5 * standardized * standardized) / (sigma * Math.sqrt(2 * Math.PI));
      normalCurve.push({ x, y: density * scale });
    }

    self.postMessage({
      type: 'SPC_RESULT',
      payload: {
        mean,
        sigma,
        cp,
        cpk,
        ppm,
        histogram,
        normalCurve,
        histogramBins,
        status,
        modelVersion: SPC_MODEL_VERSION,
        diagnostics: {
          observations,
          sigmaEstimator: 'sample-standard-deviation-n-minus-one',
          ppmAssumption: 'fitted-normal-distribution',
        },
      },
    } satisfies SpcResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies SpcResponse);
  }
};
