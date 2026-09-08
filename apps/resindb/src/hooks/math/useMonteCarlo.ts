import { useCallback, useMemo } from 'react';
import { useWorkerManager } from '@/hooks/workers/useWorkerManager';
import type { RandomSeed } from '@/compute/random';
import type { Product, FormulaConfig } from '@/types/index';
import type { MonteCarloMessage, MonteCarloResponse } from '@/workers/monteCarloWorker';

export function useMonteCarlo() {
  const {
    isCalculating: isSimulating,
    result,
    setResult,
    error,
    setError,
    postMessage,
  } = useWorkerManager<MonteCarloMessage, NonNullable<MonteCarloResponse['payload']>>(
    useCallback(() => new Worker(new URL('../../workers/monteCarloWorker.ts', import.meta.url), { type: 'module' }), []),
    'SIMULATION_COMPLETE',
  );

  const runSimulation = useCallback((
    targetFormulaId: string,
    formulas: FormulaConfig[],
    product: Product,
    variances: Record<string, number>,
    iterations: number = 5000,
    seed?: RandomSeed,
  ) => {
    postMessage({
      type: 'RUN_SIMULATION',
      payload: { targetFormulaId, formulas, product, variances, iterations, seed },
    });
  }, [postMessage]);

  const resetSimulation = useCallback(() => {
    setResult(null);
    setError(null);
  }, [setResult, setError]);

  const simulationStats = useMemo(() => result?.stats ?? null, [result]);
  const reproducibility = useMemo(() => result?.reproducibility ?? null, [result]);

  return {
    simulationStats,
    reproducibility,
    isSimulating,
    error,
    runSimulation,
    resetSimulation,
  };
}
