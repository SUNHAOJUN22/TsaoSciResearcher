import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import type { CopulaMessage, CopulaResponse } from '@/workers/copulaWorker';

export function useCopulaWorker() {
  const {
    isCalculating,
    result: copulaResult,
    error,
    postMessage
  } = useWorkerManager<CopulaMessage, CopulaResponse['payload']>(
    useCallback(() => new Worker(new URL('../../workers/copulaWorker.ts', import.meta.url), { type: 'module' }), []),
    'COPULA_RESULT'
  );

  const calculateCopula = useCallback((data: { x: number; y: number }[]) => {
    postMessage({
      type: 'CALCULATE_COPULA',
      payload: { data }
    });
  }, [postMessage]);

  const getJointFailureProb = useCallback((thresholdX: number, thresholdY: number) => {
    if (!copulaResult) return null;
    const { sortedX, sortedY, grid } = copulaResult;
    
    // Find u and v for thresholds
    let uIdx = 0;
    while(uIdx < sortedX.length && sortedX[uIdx] <= thresholdX) uIdx++;
    const u = sortedX.length > 0 ? uIdx / sortedX.length : 0;
    
    let vIdx = 0;
    while(vIdx < sortedY.length && sortedY[vIdx] <= thresholdY) vIdx++;
    const v = sortedY.length > 0 ? vIdx / sortedY.length : 0;
    
    // Integrate copula PDF numerically from grid (Riemann sum approximation)
    // grid is 50x50, step is 1/50 = 0.02
    // We sum up C_uv * du * dv where u_grid <= u and v_grid <= v
    let sum = 0;
    const du = 1/50;
    const dv = 1/50;
    
    for (const point of grid) {
        if (point.u <= u && point.v <= v) {
            sum += point.z * du * dv;
        }
    }
    
    return sum; // Joint probability
  }, [copulaResult]);

  return { isCalculating, copulaResult, error, calculateCopula, getJointFailureProb };
}
