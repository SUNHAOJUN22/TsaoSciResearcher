import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import { Product } from '@/types/index';
import { QualityWorkerMessage, QualityMonitorResultPayload } from '@/workers/dataQualityWorker';

export function useDataQualityWorker() {
  const {
    isCalculating: isAnomalizing,
    result,
    setResult,
    error,
    postMessage
  } = useWorkerManager<QualityWorkerMessage, QualityMonitorResultPayload>(
    useCallback(() => new Worker(new URL('../../workers/dataQualityWorker.ts', import.meta.url), { type: 'module' }), []),
    'QUALITY_MONITOR_RESULT'
  );

  const runQualityCheck = useCallback((allProducts: Product[], options?: QualityWorkerMessage['payload']['options']) => {
    setResult(null);
    postMessage({
      type: 'RUN_MONITOR',
      payload: { allProducts, options }
    });
  }, [postMessage, setResult]);

  return {
    isAnomalizing,
    result,
    error,
    runQualityCheck
  };
}
