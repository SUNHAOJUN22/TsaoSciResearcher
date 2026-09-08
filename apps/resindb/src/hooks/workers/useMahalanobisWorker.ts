import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import { MahalanobisMessage, MahalanobisResponse } from '@/workers/mahalanobisWorker';

export function useMahalanobisWorker() {
    const {
        isCalculating,
        result,
        setResult,
        error,
        postMessage
    } = useWorkerManager<MahalanobisMessage, MahalanobisResponse['payload']>(
        useCallback(() => new Worker(new URL('../../workers/mahalanobisWorker.ts', import.meta.url), { type: 'module' }), []),
        'MAHALANOBIS_RESULT'
    );

    const runAnalysis = useCallback((data: (Record<string, number> & { _id: string, name: string })[], features: string[], alpha: number = 0.05) => {
        setResult(null);
        postMessage({
            type: 'CALCULATE_MAHALANOBIS',
            payload: { data, features, alpha }
        });
    }, [postMessage, setResult]);

    return {
        isCalculating,
        result,
        error,
        runAnalysis
    };
}
