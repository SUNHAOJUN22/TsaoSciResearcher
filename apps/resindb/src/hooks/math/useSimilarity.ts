import { useCallback, useMemo } from 'react';
import { useWorkerManager } from '@/hooks/workers/useWorkerManager';
import { Product } from '@/types/index';
import type { SimilarityMessage, SimilarityResponse } from '@/workers/similarityWorker';

export function useSimilarityWorker() {
  const {
    isCalculating,
    result,
    setResult,
    postMessage
  } = useWorkerManager<SimilarityMessage, NonNullable<SimilarityResponse['payload']>>(
    useCallback(() => new Worker(new URL('../../workers/similarityWorker.ts', import.meta.url), { type: 'module' }), []),
    'SIMILARITY_CALCULATED'
  );

  const calculateSimilarity = useCallback((products: Product[], features: string[], threshold: number) => {
    if (products.length > 0 && features.length >= 2) {
      postMessage({
        type: 'CALCULATE_SIMILARITY',
        payload: { products, features, threshold }
      });
    } else {
      setResult(null);
    }
  }, [postMessage, setResult]);

  const nodes = useMemo(() => result?.nodes || [], [result]);
  const edges = useMemo(() => result?.edges || [], [result]);

  return {
    nodes,
    edges,
    isCalculating,
    calculateSimilarity
  };
}
