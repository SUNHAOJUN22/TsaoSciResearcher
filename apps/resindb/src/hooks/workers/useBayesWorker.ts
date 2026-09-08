import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { BayesMessage, BayesResponse } from '@/workers/bayesWorker';

export function useBayesWorker() {
  const {
    isCalculating,
    result: bayesResult,
    setResult: setBayesResult,
    error,
    postMessage
  } = useWorkerManager<BayesMessage, BayesResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/bayesWorker.ts', import.meta.url), { type: 'module' }), []),
    'BAYES_RESULT'
  );

  const runBayesOpt = useCallback((
    data: Record<string, number>[], 
    features: string[], 
    target: string, 
    maximize: boolean,
    iterations: number = 10000
  ) => {
    setBayesResult(null);
    postMessage({
      type: 'RUN_BAYES',
      payload: { data, features, target, maximize, iterations }
    });
  }, [postMessage, setBayesResult]);

  return { isCalculating, bayesResult, error, runBayesOpt };
}
