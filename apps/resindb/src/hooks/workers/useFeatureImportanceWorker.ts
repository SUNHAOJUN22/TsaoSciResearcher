import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { FeatureImportanceMessage, FeatureImportanceResponse } from '@/workers/featureImportanceWorker';

export function useFeatureImportanceWorker() {
  const {
    isCalculating,
    result: importanceResult,
    error,
    postMessage
  } = useWorkerManager<FeatureImportanceMessage, FeatureImportanceResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/featureImportanceWorker.ts', import.meta.url), { type: 'module' }), []),
    'IMPORTANCE_RESULT'
  );

  const calculateImportance = useCallback((data: number[][], featureNames: string[]) => {
    postMessage({
      type: 'CALCULATE_IMPORTANCE',
      payload: { data, featureNames }
    });
  }, [postMessage]);

  return { isCalculating, importanceResult, error, calculateImportance };
}
