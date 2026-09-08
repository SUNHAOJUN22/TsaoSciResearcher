import { useCallback } from 'react';
import { createRowMajorFloat64Matrix } from '@/compute/numericBuffers';
import { useWorkerManager } from './useWorkerManager';
import type { RSMMessage, RSMResponse } from '@/workers/rsmWorker';

export function useRsmWorker() {
  const {
    isCalculating,
    result: rsmResult,
    error,
    postMessage,
  } = useWorkerManager<RSMMessage, RSMResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/rsmWorker.ts', import.meta.url), { type: 'module' }), []),
    'RSM_CALCULATED',
  );

  const calculateRSM = useCallback((
    data: { x1: number; x2: number; y: number }[],
    gridSize?: number,
  ) => {
    const matrix = createRowMajorFloat64Matrix(data.length, 3, (row, column) => {
      const point = data[row];
      if (column === 0) return Number(point?.x1);
      if (column === 1) return Number(point?.x2);
      return Number(point?.y);
    });
    postMessage({
      type: 'CALCULATE_RSM',
      payload: { matrix, gridSize },
    }, { transfer: [matrix.values.buffer] });
  }, [postMessage]);

  return { isCalculating, rsmResult, error, calculateRSM };
}
