import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { KdeMessage, KdeResponse } from '@/workers/kdeWorker';

export function useKdeWorker() {
  const {
    isCalculating,
    result: kdeResult,
    postMessage
  } = useWorkerManager<KdeMessage, KdeResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/kdeWorker.ts', import.meta.url), { type: 'module' }), []),
    'KDE_CALCULATED'
  );

  const calculateKde = useCallback((points: {x: number, y: number}[]) => {
    if (points.length === 0) return;
    postMessage({
      type: 'CALCULATE_KDE',
      payload: { points }
    });
  }, [postMessage]);

  return { isCalculating, kdeResult, calculateKde };
}
