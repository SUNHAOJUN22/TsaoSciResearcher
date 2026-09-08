import { describe, expect, it } from 'vitest';
import {
  ComputeAbortError,
  ComputeBackendUnavailableError,
  ComputeKernelRegistry,
  ComputeTimeoutError,
  createComputeEngine,
  inferInputShape,
  probeComputeCapabilities,
  type ComputeCapabilities,
} from '@/compute';

const capabilities: ComputeCapabilities = {
  hardwareConcurrency: 8,
  deviceMemoryGiB: 16,
  wasm: true,
  wasmSimd: true,
  wasmThreads: true,
  sharedArrayBuffer: true,
  crossOriginIsolated: true,
  webgpu: true,
  edgeService: false,
};

function createTestEngine() {
  let clock = 100;
  return createComputeEngine({
    probeCapabilities: () => capabilities,
    now: () => {
      clock += 5;
      return clock;
    },
    createTaskId: () => 'task-test',
  });
}

describe('compute engine foundation', () => {
  it('executes a registered TypeScript kernel and records evidence', async () => {
    const engine = createTestEngine().register<number[], number>({
      id: 'sum',
      version: '1.0.0',
      supportedBackends: ['typescript'],
      supportedPrecisions: ['f64'],
      execute: (values) => values.reduce((sum, value) => sum + value, 0),
    });

    const result = await engine.run<number[], number>({
      kernel: 'sum',
      input: [1, 2, 3],
      metadata: { dataset: 'fixture' },
    });

    expect(result.output).toBe(6);
    expect(result.evidence).toMatchObject({
      taskId: 'task-test',
      kernel: 'sum',
      algorithmVersion: '1.0.0',
      requestedBackend: 'auto',
      backend: 'typescript',
      precision: 'f64',
      priority: 'scientific',
      inputShape: [3],
      durationMs: 5,
      fallbackUsed: false,
      capabilities,
      metadata: { dataset: 'fixture' },
    });
  });

  it('infers TypedArray and matrix shapes for evidence receipts', () => {
    expect(inferInputShape(new Float64Array(6))).toEqual([6]);
    expect(inferInputShape({
      values: new Float64Array(6),
      rows: 2,
      columns: 3,
    })).toEqual([2, 3]);
    expect(inferInputShape([[1, 2], [3, 4]])).toEqual([2, 2]);
  });

  it('uses the reference backend only when explicit fallback is allowed', async () => {
    const engine = createTestEngine().register<number, number>({
      id: 'identity',
      version: '1.0.0',
      execute: (value) => value,
    });

    const result = await engine.run<number, number>({
      kernel: 'identity',
      input: 7,
      backend: 'webgpu',
      allowFallback: true,
    });

    expect(result.output).toBe(7);
    expect(result.evidence.backend).toBe('typescript');
    expect(result.evidence.requestedBackend).toBe('webgpu');
    expect(result.evidence.fallbackUsed).toBe(true);
  });

  it('rejects an unavailable explicit backend without permission to fall back', async () => {
    const engine = createTestEngine().register<number, number>({
      id: 'identity',
      version: '1.0.0',
      execute: (value) => value,
    });

    await expect(engine.run({
      kernel: 'identity',
      input: 7,
      backend: 'webgpu',
    })).rejects.toBeInstanceOf(ComputeBackendUnavailableError);
  });

  it('propagates an external abort before kernel execution', async () => {
    const controller = new AbortController();
    controller.abort('cancelled by test');
    const engine = createTestEngine().register<number, number>({
      id: 'identity',
      version: '1.0.0',
      execute: (value) => value,
    });

    await expect(engine.run({
      kernel: 'identity',
      input: 7,
      signal: controller.signal,
    })).rejects.toBeInstanceOf(ComputeAbortError);
  });

  it('enforces timeout even when a kernel does not observe the signal', async () => {
    const engine = createTestEngine().register<void, number>({
      id: 'slow',
      version: '1.0.0',
      execute: async () => {
        await new Promise((resolve) => globalThis.setTimeout(resolve, 25));
        return 1;
      },
    });

    await expect(engine.run({
      kernel: 'slow',
      input: undefined,
      timeoutMs: 1,
    })).rejects.toBeInstanceOf(ComputeTimeoutError);
  });

  it('probes injected browser and edge capabilities deterministically', () => {
    const webAssembly = {
      validate: () => true,
    } as Pick<typeof WebAssembly, 'validate'>;

    expect(probeComputeCapabilities({
      navigator: { hardwareConcurrency: 12, deviceMemory: 32, gpu: {} },
      webAssembly,
      sharedArrayBuffer: true,
      crossOriginIsolated: true,
      edgeService: true,
    })).toEqual({
      hardwareConcurrency: 12,
      deviceMemoryGiB: 32,
      wasm: true,
      wasmSimd: true,
      wasmThreads: true,
      sharedArrayBuffer: true,
      crossOriginIsolated: true,
      webgpu: true,
      edgeService: true,
    });
  });

  it('rejects duplicate kernel registration', () => {
    const registry = new ComputeKernelRegistry();
    registry.register({ id: 'sum', version: '1.0.0', execute: () => 1 });
    expect(() => registry.register({
      id: 'sum',
      version: '1.0.1',
      execute: () => 2,
    })).toThrow('Compute kernel is already registered: sum');
  });
});
