import { summarizeFinite } from '@/lib/numericAggregation';

const KINETICS_MODEL_VERSION = 'kissinger-first-order-extrapolation-2.0.0';

export interface KineticsMessage {
  type: 'RUN_KINETICS';
  payload: {
    data: { beta: number; tp: number }[];
    isoTemp: number;
  };
}

export interface KineticsResponse {
  type: 'KINETICS_RESULT' | 'ERROR';
  payload?: {
    E: number;
    A: number;
    r2: number;
    points: { x: number; y: number }[];
    line: { x: number; y: number }[];
    isoCurve: { time: number; alpha: number }[];
    equation: string;
    modelVersion: typeof KINETICS_MODEL_VERSION;
    method: 'kissinger-peak-temperature-linearization';
    isothermalPrediction: {
      model: 'first-order-conversion-assumption';
      derivedFromPeakFit: true;
      outputAlphaUnit: 'percent';
      timeUnit: 'minutes';
    };
    observations: number;
  };
  error?: string;
}

self.onmessage = (event: MessageEvent<KineticsMessage>) => {
  try {
    const { data, isoTemp } = event.data.payload;
    const isoTemperatureKelvin = isoTemp + 273.15;
    if (!Number.isFinite(isoTemp) || !(isoTemperatureKelvin > 0)) {
      throw new Error('Isothermal prediction temperature must exceed absolute zero.');
    }
    const validData = (data ?? []).filter((row) => (
      row
      && Number.isFinite(row.beta)
      && Number.isFinite(row.tp)
      && row.beta > 0
      && row.tp + 273.15 > 0
    ));
    if (validData.length < 3) throw new Error('Kissinger fitting requires at least three valid heating rates.');

    const points = validData.map((row) => {
      const temperatureKelvin = row.tp + 273.15;
      return {
        x: 1 / temperatureKelvin,
        y: Math.log(row.beta / (temperatureKelvin * temperatureKelvin)),
      };
    });
    const observations = points.length;
    const meanX = points.reduce((sum, point) => sum + point.x, 0) / observations;
    const meanY = points.reduce((sum, point) => sum + point.y, 0) / observations;
    let centeredXX = 0;
    let centeredXY = 0;
    let totalSquares = 0;
    for (const point of points) {
      centeredXX += (point.x - meanX) ** 2;
      centeredXY += (point.x - meanX) * (point.y - meanY);
      totalSquares += (point.y - meanY) ** 2;
    }
    if (!(centeredXX > Number.EPSILON)) throw new Error('Peak temperatures do not provide enough inverse-temperature variation.');
    const slope = centeredXY / centeredXX;
    const intercept = meanY - slope * meanX;
    let residualSquares = 0;
    for (const point of points) residualSquares += (point.y - (slope * point.x + intercept)) ** 2;
    const r2 = totalSquares > 0
      ? Math.max(0, Math.min(1, 1 - residualSquares / totalSquares))
      : 0;

    const gasConstant = 8.31446261815324;
    const activationEnergyJoules = -slope * gasConstant;
    const E = activationEnergyJoules / 1000;
    if (!(E > 0) || !Number.isFinite(E)) {
      throw new Error('Kissinger fit does not yield a positive finite apparent activation energy.');
    }
    const A = (activationEnergyJoules / gasConstant) * Math.exp(intercept);
    if (!(A > 0) || !Number.isFinite(A)) throw new Error('Kissinger pre-exponential estimate is invalid.');

    const xBounds = summarizeFinite(points, (point) => point.x);
    if (!xBounds) throw new Error('Kissinger fitting produced no finite inverse temperatures.');
    const minimumX = xBounds.minimum;
    const maximumX = xBounds.maximum;
    const padding = (maximumX - minimumX) * 0.1;
    const line = [
      { x: minimumX - padding, y: slope * (minimumX - padding) + intercept },
      { x: maximumX + padding, y: slope * (maximumX + padding) + intercept },
    ];
    const rateConstant = A * Math.exp(-activationEnergyJoules / (gasConstant * isoTemperatureKelvin));
    if (!(rateConstant > 0) || !Number.isFinite(rateConstant)) {
      throw new Error('Isothermal first-order rate constant is invalid at the requested temperature.');
    }
    const timeToNinetyNinePercent = -Math.log(0.01) / rateConstant;
    const isoCurve = Array.from({ length: 101 }, (_, index) => {
      const time = timeToNinetyNinePercent * index / 100;
      return { time, alpha: (1 - Math.exp(-rateConstant * time)) * 100 };
    });

    self.postMessage({
      type: 'KINETICS_RESULT',
      payload: {
        E,
        A,
        r2,
        points,
        line,
        isoCurve,
        equation: `y = ${slope.toExponential(6)}x + ${intercept.toFixed(6)}`,
        modelVersion: KINETICS_MODEL_VERSION,
        method: 'kissinger-peak-temperature-linearization',
        isothermalPrediction: {
          model: 'first-order-conversion-assumption',
          derivedFromPeakFit: true,
          outputAlphaUnit: 'percent',
          timeUnit: 'minutes',
        },
        observations,
      },
    } satisfies KineticsResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies KineticsResponse);
  }
};
