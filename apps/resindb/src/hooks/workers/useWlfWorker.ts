import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { WlfMessage, WlfResponse } from '@/workers/wlfWorker';

export function useWlfWorker() {
  const {
    isCalculating,
    result: wlfResult,
    setResult: setWlfResult,
    error,
    postMessage
  } = useWorkerManager<WlfMessage, WlfResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/wlfWorker.ts', import.meta.url), { type: 'module' }), []),
    'WLF_RESULT'
  );

  const calculateWLF = useCallback((curves: { temp: number; points: { rate: number; visc: number }[] }[], refTemp: number) => {
    setWlfResult(null);
    postMessage({
      type: 'CALCULATE_WLF',
      payload: { curves, refTemp }
    });
  }, [postMessage, setWlfResult]);

  return { isCalculating, wlfResult, error, calculateWLF };
}
