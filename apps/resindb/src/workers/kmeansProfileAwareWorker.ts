import {
  createKMeansBenchmarkEnvironment,
  decideKMeansAssignmentBackend,
  type KMeansBackendBenchmarkProfile,
  type KMeansBackendDecisionEvidence,
} from '@/compute/kmeansBackendPolicy';
import type { KMeansMessage, KMeansResponse } from './kmeansWorker';
import './kmeansWorker';

export type KMeansProfileAwareMessage = {
  type: 'COMPUTE_KMEANS';
  payload: KMeansMessage['payload'] & {
    benchmarkProfile?: KMeansBackendBenchmarkProfile;
  };
};

type WorkerScope = {
  onmessage: ((event: MessageEvent<KMeansMessage>) => void) | null;
  postMessage(message: unknown, transfer?: Transferable[]): void;
};

const scope = self as unknown as WorkerScope;
const baseHandler = scope.onmessage;
if (!baseHandler) throw new Error('K-Means worker handler was not initialized');

const nativePostMessage = scope.postMessage.bind(scope);
let activeDecision: KMeansBackendDecisionEvidence | null = null;
let activeRequestedBackend: 'auto' | 'typescript' | 'wasm' = 'auto';

scope.postMessage = (message: unknown, transfer: Transferable[] = []) => {
  if (
    activeDecision
    && message
    && typeof message === 'object'
    && (message as { type?: unknown }).type === 'KMEANS_RESULT'
  ) {
    const response = message as Extract<KMeansResponse, { type: 'KMEANS_RESULT' }>;
    const assignmentKernel = response.payload.performance.assignmentKernel;
    if (assignmentKernel) {
      assignmentKernel.requestedBackend = activeRequestedBackend;
      assignmentKernel.backendDecision = activeDecision;
    }
    activeDecision = null;
  } else if (
    message
    && typeof message === 'object'
    && (message as { type?: unknown }).type === 'ERROR'
  ) {
    activeDecision = null;
  }
  nativePostMessage(message, transfer);
};

scope.onmessage = (event: MessageEvent<KMeansMessage>) => {
  const message = event.data as KMeansProfileAwareMessage;
  const payload = message.payload;
  const sampleCount = 'matrix' in payload ? payload.matrix.rows : payload.data.length;
  const dimensions = payload.keys.length;
  const requestedMaxK = payload.maxK ?? 10;
  const maxClusters = Math.max(1, Math.min(
    requestedMaxK,
    Math.floor(sampleCount / 2),
    10,
  ));
  activeRequestedBackend = payload.backend ?? 'auto';
  activeDecision = decideKMeansAssignmentBackend({
    requestedBackend: activeRequestedBackend,
    sampleCount,
    dimensions,
    maxClusters,
    profile: payload.benchmarkProfile,
    environment: createKMeansBenchmarkEnvironment(),
  });
  payload.backend = activeDecision.selectedBackend;
  delete payload.benchmarkProfile;
  baseHandler(event);
};
