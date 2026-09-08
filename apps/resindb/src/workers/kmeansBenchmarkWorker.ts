import {
  runKMeansBrowserBenchmark,
  type KMeansBrowserBenchmarkMode,
  type KMeansBrowserBenchmarkResult,
} from '@/compute/kmeansBrowserBenchmark';
import { createWorkerProgressMessage } from '@/compute/workerProtocol';

export interface KMeansBenchmarkWorkerMessage {
  type: 'RUN_KMEANS_BROWSER_BENCHMARK';
  payload?: {
    mode?: KMeansBrowserBenchmarkMode;
  };
}

export type KMeansBenchmarkWorkerResponse = {
  type: 'KMEANS_BENCHMARK_COMPLETE';
  payload: KMeansBrowserBenchmarkResult;
} | {
  type: 'ERROR';
  error: string;
};

self.onmessage = async (event: MessageEvent<KMeansBenchmarkWorkerMessage>) => {
  try {
    if (event.data.type !== 'RUN_KMEANS_BROWSER_BENCHMARK') {
      throw new Error('Unsupported K-Means benchmark worker message');
    }
    const result = await runKMeansBrowserBenchmark({
      mode: event.data.payload?.mode ?? 'full',
      onProgress(completed, total, phase) {
        self.postMessage(createWorkerProgressMessage({
          ratio: total > 0 ? completed / total : 0,
          completed,
          total,
          phase,
        }));
      },
    });
    self.postMessage(createWorkerProgressMessage({ ratio: 1, phase: 'complete' }));
    self.postMessage({
      type: 'KMEANS_BENCHMARK_COMPLETE',
      payload: result,
    } satisfies KMeansBenchmarkWorkerResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      error: error instanceof Error ? error.message : String(error),
    } satisfies KMeansBenchmarkWorkerResponse);
  }
};
