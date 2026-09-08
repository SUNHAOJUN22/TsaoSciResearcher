import { useCallback } from 'react';
import { useWorkerManager } from './useWorkerManager';
import { PronyMessage, PronyResponse } from '@/workers/pronyWorker';

export function usePronyWorker() {
    const {
        isCalculating,
        result,
        setResult,
        error,
        postMessage
    } = useWorkerManager<PronyMessage, PronyResponse['payload']>(
        useCallback(() => new Worker(new URL('../../workers/pronyWorker.ts', import.meta.url), { type: 'module' }), []),
        'PRONY_RESULT'
    );

    const runProny = useCallback((data: { omega: number; storage: number; loss: number }[], numTerms: number) => {
        setResult(null);
        postMessage({
            type: 'RUN_PRONY',
            payload: { data, numTerms }
        });
    }, [postMessage, setResult]);

    return {
        isCalculating,
        result,
        error,
        runProny
    };
}
