export const COMPUTE_BACKENDS = ['typescript', 'wasm', 'webgpu', 'edge'] as const;

export type ComputeBackendId = (typeof COMPUTE_BACKENDS)[number];
export type ComputeBackendPreference = 'auto' | ComputeBackendId;
export type ComputePrecision = 'f32' | 'f64';
export type ComputePriority = 'interactive' | 'scientific' | 'background';
export type ComputeMetadataValue = string | number | boolean | null;

export interface NumericMatrix {
  values: Float32Array | Float64Array;
  rows: number;
  columns: number;
  columnNames?: readonly string[];
}

export interface ComputeCapabilities {
  hardwareConcurrency: number;
  deviceMemoryGiB?: number;
  wasm: boolean;
  wasmSimd: boolean;
  wasmThreads: boolean;
  sharedArrayBuffer: boolean;
  crossOriginIsolated: boolean;
  webgpu: boolean;
  edgeService: boolean;
}

export interface ComputeTaskOptions {
  backend?: ComputeBackendPreference;
  precision?: ComputePrecision;
  priority?: ComputePriority;
  allowFallback?: boolean;
  signal?: AbortSignal;
  timeoutMs?: number;
  taskId?: string;
  metadata?: Readonly<Record<string, ComputeMetadataValue>>;
}

export interface ComputeTaskRequest<TInput = unknown> extends ComputeTaskOptions {
  kernel: string;
  input: TInput;
}

export interface ComputeEvidence {
  taskId: string;
  kernel: string;
  algorithmVersion: string;
  requestedBackend: ComputeBackendPreference;
  backend: ComputeBackendId;
  precision: ComputePrecision;
  priority: ComputePriority;
  inputShape: number[];
  durationMs: number;
  fallbackUsed: boolean;
  capabilities: ComputeCapabilities;
  metadata?: Readonly<Record<string, ComputeMetadataValue>>;
}

export interface ComputeTaskResult<TOutput = unknown> {
  output: TOutput;
  evidence: ComputeEvidence;
}

export interface ComputeExecutionContext {
  taskId: string;
  precision: ComputePrecision;
  priority: ComputePriority;
  signal: AbortSignal;
  capabilities: ComputeCapabilities;
  startedAt: number;
}

export type ComputeKernelHandler<TInput, TOutput> = (
  input: TInput,
  context: ComputeExecutionContext,
) => TOutput | Promise<TOutput>;

export interface ComputeKernelDefinition<TInput = unknown, TOutput = unknown> {
  id: string;
  version: string;
  supportedBackends?: readonly ComputeBackendId[];
  supportedPrecisions?: readonly ComputePrecision[];
  execute: ComputeKernelHandler<TInput, TOutput>;
}

export interface ComputeBackend {
  readonly id: ComputeBackendId;
  isAvailable(capabilities: ComputeCapabilities): boolean;
  supports(
    definition: ComputeKernelDefinition<unknown, unknown>,
    precision: ComputePrecision,
  ): boolean;
  run(
    definition: ComputeKernelDefinition<unknown, unknown>,
    input: unknown,
    context: ComputeExecutionContext,
  ): Promise<unknown>;
}
