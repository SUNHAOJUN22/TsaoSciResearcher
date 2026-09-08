import { useCallback, useEffect, useRef, useState } from 'react';
import type { KMeansAssignmentBackendPreference } from '@/compute/kmeansAssignment';
import {
  kmeansBackendProfileStore,
  type KMeansBackendProfileLoadStatus,
} from '@/compute/kmeansBackendProfileStore';
import {
  createKMeansDecisionHistoryEntry,
  kmeansDecisionHistoryStore,
} from '@/compute/kmeansDecisionHistoryStore';
import { createRowMajorFloat64Matrix } from '@/compute/numericBuffers';
import type { RandomSeed } from '@/compute/random';
import {
  clearKMeansWorkloadSnapshot,
  updateKMeansWorkloadSnapshot,
} from '@/compute/kmeansWorkloadStore';
import type { KMeansResponse } from '@/workers/kmeansWorker';
import type { KMeansProfileAwareMessage } from '@/workers/kmeansProfileAwareWorker';
import { useWorkerManager } from './useWorkerManager';

export interface KMeansExecutionOptions {
  backend?: KMeansAssignmentBackendPreference;
  allowFallback?: boolean;
}

export function useKMeansWorker() {
  const [profileLoadStatus, setProfileLoadStatus] = useState<KMeansBackendProfileLoadStatus>('missing');
  const {
    isCalculating: isComputing,
    result,
    setResult,
    postMessage,
  } = useWorkerManager<
    KMeansProfileAwareMessage,
    Extract<KMeansResponse, { type: 'KMEANS_RESULT' }>['payload']
  >(
    useCallback(
      () => new Worker(
        new URL('../../workers/kmeansProfileAwareWorker.ts', import.meta.url),
        { type: 'module' },
      ),
      [],
    ),
    'KMEANS_RESULT',
  );
  const lastAuditedResult = useRef<typeof result>(null);

  useEffect(() => {
    if (!result || lastAuditedResult.current === result) return;
    lastAuditedResult.current = result;
    const evidence = result.performance.assignmentKernel;
    if (!evidence) return;
    void kmeansDecisionHistoryStore
      .append(createKMeansDecisionHistoryEntry(evidence))
      .catch(() => undefined);
  }, [result]);

  const computeKMeans = useCallback(async (
    data: { id: string; values: Record<string, number> }[],
    keys: string[],
    maxK = 10,
    seed?: RandomSeed,
    options: KMeansExecutionOptions = {},
  ) => {
    if (keys.length === 0 || data.length === 0) {
      clearKMeansWorkloadSnapshot();
      setResult(null);
      return;
    }
    const requestedBackend = options.backend ?? 'auto';
    const loadedProfile = requestedBackend === 'auto'
      ? await kmeansBackendProfileStore.load()
      : null;
    setProfileLoadStatus(loadedProfile?.status ?? 'missing');
    const matrix = createRowMajorFloat64Matrix(
      data.length,
      keys.length,
      (row, column) => Number(data[row]?.values?.[keys[column]]),
    );
    const maxClusters = Math.max(1, Math.min(maxK, Math.floor(data.length / 2), 10));
    updateKMeansWorkloadSnapshot(data.length, keys.length, maxClusters);
    postMessage({
      type: 'COMPUTE_KMEANS',
      payload: {
        ids: data.map((item) => String(item.id)),
        matrix,
        keys,
        maxK,
        seed,
        backend: options.backend,
        allowFallback: options.allowFallback,
        benchmarkProfile: loadedProfile?.status === 'valid'
          ? loadedProfile.profile ?? undefined
          : undefined,
      },
    }, { transfer: [matrix.values.buffer] });
  }, [postMessage, setResult]);

  return {
    clusters: result?.clusters ?? {},
    bestK: result?.k ?? 0,
    silhouetteScore: result?.silhouetteScore ?? null,
    reproducibility: result?.reproducibility ?? null,
    modelSelection: result?.modelSelection ?? null,
    performance: result?.performance ?? null,
    profileLoadStatus,
    computeKMeans,
    isComputingKMeans: isComputing,
  };
}
