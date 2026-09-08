import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import { Product } from '@/types/index';
import { ForecastingWorkerMessage, ForecastingWorkerResponse } from '@/workers/forecastingWorker';

export function useForecastingWorker() {
  const {
    isCalculating: isProjecting,
    result: forecastResult,
    error: forecastError,
    postMessage
  } = useWorkerManager<ForecastingWorkerMessage, Required<ForecastingWorkerResponse>['payload']>(
    useCallback(() => new Worker(new URL('../../workers/forecastingWorker.ts', import.meta.url), { type: 'module' }), []),
    'FORECAST_RESULT'
  );

  const runCalculatedForecast = useCallback((
    products: Product[],
    propertyKey: string,
    algorithm: ForecastingWorkerMessage['payload']['algorithm'],
    condition: ForecastingWorkerMessage['payload']['condition'],
    stressFactor: number,
    alpha?: number,
    beta?: number
  ) => {
    postMessage({
      type: 'RUN_FORECAST',
      payload: {
        products,
        propertyKey,
        algorithm,
        condition,
        stressFactor,
        alpha,
        beta
      }
    });
  }, [postMessage]);

  return {
    isProjecting,
    forecastResult,
    forecastError,
    runCalculatedForecast
  };
}
