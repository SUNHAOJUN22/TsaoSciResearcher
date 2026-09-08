import { describe, expect, it, vi } from 'vitest';
import {
  assignAndAccumulateTypeScript,
  createKMeansAssignmentSession,
} from '@/compute/kmeansAssignment';
import { createKMeansAssignmentWasmSession } from '@/compute/wasm/kmeansAssignmentWasm';

const matrix = new Float64Array([
  -1, -1,
  1, 1,
  -0.75, -1.25,
  1.25, 0.75,
  8, 8,
  9, 9,
]);
const centroids = new Float64Array([
  0, 0,
  8.5, 8.5,
]);

function createBuffers() {
  const assignments = new Int32Array(matrix.length / 2);
  assignments.fill(-1);
  return {
    assignments,
    sums: new Float64Array(centroids.length),
    counts: new Uint32Array(2),
  };
}

describe('FP64 K-Means assignment backends', () => {
  it('matches the TypeScript reference backend exactly', () => {
    const typescriptBuffers = createBuffers();
    const wasmBuffers = createBuffers();
    const typescriptChanged = assignAndAccumulateTypeScript(
      matrix,
      6,
      2,
      centroids,
      2,
      typescriptBuffers.assignments,
      typescriptBuffers.sums,
      typescriptBuffers.counts,
    );
    const wasm = createKMeansAssignmentWasmSession(matrix, 6, 2, 2);
    const wasmChanged = wasm.assignAndAccumulate(
      centroids,
      2,
      wasmBuffers.assignments,
      wasmBuffers.sums,
      wasmBuffers.counts,
    );

    expect(wasmChanged).toBe(typescriptChanged);
    expect([...wasmBuffers.assignments]).toEqual([...typescriptBuffers.assignments]);
    expect([...wasmBuffers.sums]).toEqual([...typescriptBuffers.sums]);
    expect([...wasmBuffers.counts]).toEqual([...typescriptBuffers.counts]);
    expect(wasm.memoryBytes).toBeGreaterThanOrEqual(131_072);
  });

  it('uses WebAssembly when explicitly requested', () => {
    const session = createKMeansAssignmentSession({
      matrix,
      sampleCount: 6,
      dimensions: 2,
      maxClusters: 2,
      preference: 'wasm',
      allowFallback: false,
    });
    const buffers = createBuffers();
    session.assignAndAccumulate(
      centroids,
      2,
      buffers.assignments,
      buffers.sums,
      buffers.counts,
    );
    expect(session.getEvidence()).toMatchObject({
      kernel: 'kmeans-assignment-update',
      kernelVersion: '1.0.0',
      precision: 'f64',
      requestedBackend: 'wasm',
      backend: 'wasm',
      fallbackUsed: false,
      calls: 1,
      wasmSimdUsed: false,
      wasmThreadsUsed: false,
    });
  });

  it('falls back to TypeScript when WebAssembly initialization fails', () => {
    const session = createKMeansAssignmentSession({
      matrix,
      sampleCount: 6,
      dimensions: 2,
      maxClusters: 2,
      preference: 'wasm',
      allowFallback: true,
      createWasmSession: () => {
        throw new Error('synthetic wasm initialization failure');
      },
    });
    const buffers = createBuffers();
    session.assignAndAccumulate(
      centroids,
      2,
      buffers.assignments,
      buffers.sums,
      buffers.counts,
    );
    expect(session.getEvidence()).toMatchObject({
      backend: 'typescript',
      fallbackUsed: true,
      fallbackReason: 'synthetic wasm initialization failure',
      calls: 1,
    });
  });

  it('falls back after a WebAssembly runtime failure without exposing partial output', () => {
    const session = createKMeansAssignmentSession({
      matrix,
      sampleCount: 6,
      dimensions: 2,
      maxClusters: 2,
      preference: 'wasm',
      allowFallback: true,
      createWasmSession: () => ({
        memoryBytes: 131_072,
        assignAndAccumulate(_centroids, _clusters, assignments, sums, counts) {
          assignments.fill(99);
          sums.fill(Number.NaN);
          counts.fill(99);
          throw new Error('synthetic wasm runtime failure');
        },
      }),
    });
    const buffers = createBuffers();
    session.assignAndAccumulate(
      centroids,
      2,
      buffers.assignments,
      buffers.sums,
      buffers.counts,
    );
    expect([...buffers.assignments]).toEqual([0, 0, 0, 0, 1, 1]);
    expect([...buffers.sums]).toEqual([0.5, -0.5, 17, 17]);
    expect([...buffers.counts]).toEqual([4, 2]);
    expect(session.getEvidence()).toMatchObject({
      backend: 'typescript',
      fallbackUsed: true,
      fallbackReason: 'synthetic wasm runtime failure',
    });
  });

  it('rejects a strict WebAssembly request when initialization fails', () => {
    expect(() => createKMeansAssignmentSession({
      matrix,
      sampleCount: 6,
      dimensions: 2,
      maxClusters: 2,
      preference: 'wasm',
      allowFallback: false,
      createWasmSession: () => {
        throw new Error('strict wasm failure');
      },
    })).toThrow('strict wasm failure');
  });

  it('rejects a strict WebAssembly request when the capability is absent', () => {
    vi.stubGlobal('WebAssembly', undefined);
    try {
      expect(() => createKMeansAssignmentSession({
        matrix,
        sampleCount: 6,
        dimensions: 2,
        maxClusters: 2,
        preference: 'wasm',
        allowFallback: false,
      })).toThrow('WebAssembly was requested but is unavailable');
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
