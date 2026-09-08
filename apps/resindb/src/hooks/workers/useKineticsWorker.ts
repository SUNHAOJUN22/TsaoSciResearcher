import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import { KineticsMessage, KineticsResponse } from '@/workers/kineticsWorker';

export function useKineticsWorker() {
    const {
        isCalculating,
        result,
        setResult,
        error,
        postMessage
    } = useWorkerManager<KineticsMessage, KineticsResponse['payload']>(
        useCallback(() => new Worker(new URL('../../workers/kineticsWorker.ts', import.meta.url), { type: 'module' }), []),
        'KINETICS_RESULT'
    );

    const runAnalysis = useCallback((data: { beta: number; tp: number }[], isoTemp: number) => {
        setResult(null);
        postMessage({
            type: 'RUN_KINETICS',
            payload: { data, isoTemp }
        });
    }, [postMessage, setResult]);

    return {
        isCalculating,
        result,
        error,
        runAnalysis
    };
}
