import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { WeibullMessage, WeibullResponse } from '@/workers/weibullWorker';

export function useWeibullWorker() {
  const {
    isCalculating,
    result: weibullResult,
    error,
    postMessage
  } = useWorkerManager<WeibullMessage, WeibullResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/weibullWorker.ts', import.meta.url), { type: 'module' }), []),
    'WEIBULL_RESULT'
  );

  const calculateWeibull = useCallback((data: number[]) => {
    postMessage({
      type: 'CALCULATE_WEIBULL',
      payload: { data }
    });
  }, [postMessage]);

  return { isCalculating, weibullResult, error, calculateWeibull };
}
