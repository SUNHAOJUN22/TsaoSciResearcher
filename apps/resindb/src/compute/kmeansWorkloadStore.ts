export const KMEANS_WORKLOAD_SNAPSHOT_VERSION = 'kmeans-workload-snapshot-1.0.0';

export interface KMeansWorkloadSnapshot {
  version: typeof KMEANS_WORKLOAD_SNAPSHOT_VERSION;
  sampleCount: number;
  dimensions: number;
  maxClusters: number;
  workloadOperations: number;
  updatedAt: string;
}

type Listener = () => void;

let snapshot: KMeansWorkloadSnapshot | null = null;
const listeners = new Set<Listener>();

function validateDimension(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative integer`);
  }
  return value;
}

export function updateKMeansWorkloadSnapshot(
  sampleCount: number,
  dimensions: number,
  maxClusters: number,
  now = new Date(),
): KMeansWorkloadSnapshot {
  const samples = validateDimension(sampleCount, 'sampleCount');
  const dimensionCount = validateDimension(dimensions, 'dimensions');
  const clusters = validateDimension(maxClusters, 'maxClusters');
  const workloadOperations = samples * dimensionCount * clusters;
  if (!Number.isSafeInteger(workloadOperations)) {
    throw new RangeError('K-Means workload exceeds the safe integer range');
  }
  snapshot = {
    version: KMEANS_WORKLOAD_SNAPSHOT_VERSION,
    sampleCount: samples,
    dimensions: dimensionCount,
    maxClusters: clusters,
    workloadOperations,
    updatedAt: now.toISOString(),
  };
  for (const listener of listeners) listener();
  return snapshot;
}

export function getKMeansWorkloadSnapshot(): KMeansWorkloadSnapshot | null {
  return snapshot;
}

export function subscribeKMeansWorkloadSnapshot(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function clearKMeansWorkloadSnapshot(): void {
  snapshot = null;
  for (const listener of listeners) listener();
}
