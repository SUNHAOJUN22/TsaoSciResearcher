import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { ArrheniusMessage, ArrheniusResponse } from '@/workers/arrheniusWorker';

export function useArrheniusWorker() {
  const {
    isCalculating,
    result: arrheniusResult,
    error,
    postMessage
  } = useWorkerManager<ArrheniusMessage, ArrheniusResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/arrheniusWorker.ts', import.meta.url), { type: 'module' }), []),
    'ARRHENIUS_RESULT'
  );

  const calculateArrhenius = useCallback((points: { tempC: number; time: number }[]) => {
    postMessage({
      type: 'CALCULATE_ARRHENIUS',
      payload: { points }
    });
  }, [postMessage]);

  const getPredictedLife = useCallback((tempC: number) => {
     if (!arrheniusResult) return null;
     const { m, b } = arrheniusResult.equation;
     const tk = tempC + 273.15;
     if (Math.abs(tk) < 1e-6) return null;
     const lnTime = m * (1 / tk) + b;
     return Math.exp(lnTime);
  }, [arrheniusResult]);

  return { isCalculating, arrheniusResult, error, calculateArrhenius, getPredictedLife };
}
