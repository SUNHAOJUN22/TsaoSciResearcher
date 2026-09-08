const ARRHENIUS_MODEL_VERSION = 'log-lifetime-arrhenius-2.0.0';

export interface ArrheniusMessage {
  type: 'CALCULATE_ARRHENIUS';
  payload: {
    points: { tempC: number; time: number }[];
  };
}

export interface ArrheniusResponse {
  type: 'ARRHENIUS_RESULT' | 'ERROR';
  payload?: {
    ea: number;
    lnA: number;
    rSquared: number;
    points: { tempC: number; time: number; x: number; y: number }[];
    equation: { m: number; b: number };
    modelVersion: typeof ARRHENIUS_MODEL_VERSION;
    method: 'ordinary-least-squares-log-lifetime-arrhenius';
    interceptMeaning: 'log-time-intercept-not-direct-rate-prefactor';
    observations: number;
  };
  error?: string;
}

self.onmessage = (event: MessageEvent<ArrheniusMessage>) => {
  try {
    const validPoints = (event.data.payload.points ?? []).filter((point) => (
      point
      && Number.isFinite(point.tempC)
      && Number.isFinite(point.time)
      && point.tempC + 273.15 > 0
      && point.time > 0
    ));
    if (validPoints.length < 2) {
      throw new Error('Arrhenius log-lifetime analysis requires at least two finite positive-time observations.');
    }
    const mappedPoints = validPoints.map((point) => ({
      tempC: point.tempC,
      time: point.time,
      x: 1 / (point.tempC + 273.15),
      y: Math.log(point.time),
    }));
    const observations = mappedPoints.length;
    const meanX = mappedPoints.reduce((sum, point) => sum + point.x, 0) / observations;
    const meanY = mappedPoints.reduce((sum, point) => sum + point.y, 0) / observations;
    let centeredXX = 0;
    let centeredXY = 0;
    for (const point of mappedPoints) {
      centeredXX += (point.x - meanX) ** 2;
      centeredXY += (point.x - meanX) * (point.y - meanY);
    }
    if (!(centeredXX > Number.EPSILON)) throw new Error('Temperature values do not provide enough inverse-temperature variation.');
    const m = centeredXY / centeredXX;
    const b = meanY - m * meanX;
    let totalSquares = 0;
    let residualSquares = 0;
    for (const point of mappedPoints) {
      totalSquares += (point.y - meanY) ** 2;
      residualSquares += (point.y - (m * point.x + b)) ** 2;
    }
    const rSquared = totalSquares > 0
      ? Math.max(0, Math.min(1, 1 - residualSquares / totalSquares))
      : 0;
    const ea = m * 8.31446261815324 / 1000;
    if (!(ea > 0) || !Number.isFinite(ea)) {
      throw new Error('The fitted trend does not yield a positive finite apparent activation energy.');
    }
    self.postMessage({
      type: 'ARRHENIUS_RESULT',
      payload: {
        ea,
        lnA: b,
        rSquared,
        points: mappedPoints,
        equation: { m, b },
        modelVersion: ARRHENIUS_MODEL_VERSION,
        method: 'ordinary-least-squares-log-lifetime-arrhenius',
        interceptMeaning: 'log-time-intercept-not-direct-rate-prefactor',
        observations,
      },
    } satisfies ArrheniusResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies ArrheniusResponse);
  }
};
