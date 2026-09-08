import { useCallback, useEffect, useRef, useState } from 'react';
import {
  kmeansBackendProfileStore,
  type KMeansBackendProfileLoadResult,
} from '@/compute/kmeansBackendProfileStore';
import type {
  KMeansBrowserBenchmarkMode,
  KMeansBrowserBenchmarkResult,
} from '@/compute/kmeansBrowserBenchmark';
import { kmeansDecisionHistoryStore } from '@/compute/kmeansDecisionHistoryStore';
import type {
  KMeansBenchmarkWorkerMessage,
  KMeansBenchmarkWorkerResponse,
} from '@/workers/kmeansBenchmarkWorker';
import { useWorkerManager } from './useWorkerManager';

const EMPTY_PROFILE_STATE: KMeansBackendProfileLoadResult = {
  status: 'missing',
  profile: null,
  environment: null,
  reason: 'Profile has not been loaded yet',
  savedAt: null,
  migration: null,
  migrationHistory: [],
};

export function useKMeansBackendCalibration() {
  const [profileState, setProfileState] = useState<KMeansBackendProfileLoadResult>(
    EMPTY_PROFILE_STATE,
  );
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isPersistingProfile, setIsPersistingProfile] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);
  const persistedDigestRef = useRef<string | null>(null);

  const {
    isCalculating: isCalibrating,
    result: benchmarkResult,
    error: benchmarkError,
    progress: benchmarkProgress,
    postMessage,
    cancel,
  } = useWorkerManager<
    KMeansBenchmarkWorkerMessage,
    Extract<KMeansBenchmarkWorkerResponse, { type: 'KMEANS_BENCHMARK_COMPLETE' }>['payload']
  >(
    useCallback(
      () => new Worker(
        new URL('../../workers/kmeansBenchmarkWorker.ts', import.meta.url),
        { type: 'module' },
      ),
      [],
    ),
    'KMEANS_BENCHMARK_COMPLETE',
    {
      poolKey: 'kmeans-browser-benchmark',
      priority: 'background',
      timeoutMs: 120_000,
    },
  );

  const refreshProfile = useCallback(async () => {
    setIsLoadingProfile(true);
    try {
      const loaded = await kmeansBackendProfileStore.load();
      setProfileState(loaded);
      setStorageError(loaded.status === 'error' || loaded.status === 'unavailable'
        ? loaded.reason
        : null);
      return loaded;
    } finally {
      setIsLoadingProfile(false);
    }
  }, []);

  useEffect(() => {
    void refreshProfile();
  }, [refreshProfile]);

  useEffect(() => {
    if (!benchmarkResult) return;
    const digest = benchmarkResult.report.digest;
    if (persistedDigestRef.current === digest) return;
    persistedDigestRef.current = digest;
    setIsPersistingProfile(true);
    setStorageError(null);
    void kmeansBackendProfileStore
      .save(benchmarkResult.profile, benchmarkResult.environment)
      .then(() => refreshProfile())
      .catch((error: unknown) => {
        persistedDigestRef.current = null;
        setStorageError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => setIsPersistingProfile(false));
  }, [benchmarkResult, refreshProfile]);

  const runCalibration = useCallback((mode: KMeansBrowserBenchmarkMode = 'full') => {
    persistedDigestRef.current = null;
    setStorageError(null);
    postMessage({
      type: 'RUN_KMEANS_BROWSER_BENCHMARK',
      payload: { mode },
    });
  }, [postMessage]);

  const clearProfile = useCallback(async () => {
    setIsPersistingProfile(true);
    setStorageError(null);
    try {
      await Promise.all([
        kmeansBackendProfileStore.clear(),
        kmeansDecisionHistoryStore.clear(),
      ]);
      persistedDigestRef.current = null;
      await refreshProfile();
    } catch (error) {
      setStorageError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsPersistingProfile(false);
    }
  }, [refreshProfile]);

  return {
    profileState,
    isLoadingProfile,
    isPersistingProfile,
    isCalibrating,
    benchmarkResult: benchmarkResult as KMeansBrowserBenchmarkResult | null,
    benchmarkError,
    benchmarkProgress,
    storageError,
    runCalibration,
    cancelCalibration: cancel,
    clearProfile,
    refreshProfile,
  };
}
