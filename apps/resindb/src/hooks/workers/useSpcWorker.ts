import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { SpcMessage, SpcResponse } from '@/workers/spcWorker';

export function useSpcWorker() {
  const {
    isCalculating,
    result: spcResult,
    setResult: setSpcResult,
    error,
    postMessage
  } = useWorkerManager<SpcMessage, SpcResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/spcWorker.ts', import.meta.url), { type: 'module' }), []),
    'SPC_RESULT'
  );

  const calculateSpc = useCallback((data: number[], usl: number, lsl: number) => {
    setSpcResult(null);
    postMessage({
      type: 'CALCULATE_SPC',
      payload: { data, usl, lsl }
    });
  }, [postMessage, setSpcResult]);

  return { isCalculating, spcResult, error, calculateSpc };
}
