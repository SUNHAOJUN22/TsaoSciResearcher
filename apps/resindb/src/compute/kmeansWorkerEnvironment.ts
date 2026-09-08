import {
  createKMeansBenchmarkEnvironment,
  type KMeansBenchmarkEnvironment,
} from './kmeansBackendPolicy';
import type { ComputeProbeEnvironment } from './capabilityProbe';

function fnv1a(value: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index++) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

/**
 * Profiles are generated inside a browser Worker. The main thread must
 * reconstruct that target compute identity instead of validating the profile
 * against the browser-window runtime label.
 */
export function createKMeansWorkerBenchmarkEnvironment(
  probeEnvironment?: ComputeProbeEnvironment,
): KMeansBenchmarkEnvironment {
  const detected = createKMeansBenchmarkEnvironment(probeEnvironment);
  if (detected.runtime === 'browser-worker') return detected;
  const identity = {
    runtime: 'browser-worker' as const,
    runtimeVersion: detected.runtimeVersion,
    platform: detected.platform,
    architecture: detected.architecture,
    logicalCores: detected.logicalCores,
    wasm: detected.wasm,
    wasmSimd: detected.wasmSimd,
    wasmThreads: detected.wasmThreads,
  };
  return {
    ...identity,
    fingerprint: `kmeans-env-${fnv1a(JSON.stringify(identity))}`,
  };
}
