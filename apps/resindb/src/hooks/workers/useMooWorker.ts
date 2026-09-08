import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { MooMessage, MooResponse, MooTarget } from '@/workers/mooWorker';

export function useMooWorker() {
  const {
    isCalculating,
    result: mooResult,
    setResult: setMooResult,
    error,
    postMessage
  } = useWorkerManager<MooMessage, MooResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/mooWorker.ts', import.meta.url), { type: 'module' }), []),
    'MOO_RESULT'
  );

  const runMooOpt = useCallback((
    data: Record<string, number>[], 
    features: string[], 
    targets: MooTarget[], 
    iterations: number = 10000
  ) => {
    setMooResult(null);
    postMessage({
      type: 'RUN_MOO',
      payload: { data, features, targets, iterations }
    });
  }, [postMessage, setMooResult]);

  return { isCalculating, mooResult, error, runMooOpt };
}
