import type {
  ComputeBackendId,
  ComputeBackendPreference,
  ComputeCapabilities,
  ComputeEvidence,
  ComputeKernelDefinition,
  ComputeMetadataValue,
  ComputePrecision,
  ComputePriority,
  NumericMatrix,
} from './types';

function isNumericMatrix(value: unknown): value is NumericMatrix {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<NumericMatrix>;
  return (
    (candidate.values instanceof Float32Array || candidate.values instanceof Float64Array)
    && Number.isInteger(candidate.rows)
    && Number.isInteger(candidate.columns)
    && (candidate.rows ?? 0) >= 0
    && (candidate.columns ?? 0) >= 0
  );
}

function inferArrayShape(value: readonly unknown[]): number[] {
  if (value.length === 0) return [0];
  const child = value[0];
  return Array.isArray(child) ? [value.length, ...inferArrayShape(child)] : [value.length];
}

export function inferInputShape(input: unknown): number[] {
  if (isNumericMatrix(input)) return [input.rows, input.columns];
  if (ArrayBuffer.isView(input)) {
    const length = 'length' in input && typeof input.length === 'number'
      ? input.length
      : input.byteLength;
    return [length];
  }
  if (Array.isArray(input)) return inferArrayShape(input);
  return [];
}

export interface ComputeEvidenceInput {
  taskId: string;
  definition: ComputeKernelDefinition<unknown, unknown>;
  requestedBackend: ComputeBackendPreference;
  backend: ComputeBackendId;
  precision: ComputePrecision;
  priority: ComputePriority;
  input: unknown;
  startedAt: number;
  finishedAt: number;
  fallbackUsed: boolean;
  capabilities: ComputeCapabilities;
  metadata?: Readonly<Record<string, ComputeMetadataValue>>;
}

export function createComputeEvidence(input: ComputeEvidenceInput): ComputeEvidence {
  return {
    taskId: input.taskId,
    kernel: input.definition.id,
    algorithmVersion: input.definition.version,
    requestedBackend: input.requestedBackend,
    backend: input.backend,
    precision: input.precision,
    priority: input.priority,
    inputShape: inferInputShape(input.input),
    durationMs: Math.max(0, input.finishedAt - input.startedAt),
    fallbackUsed: input.fallbackUsed,
    capabilities: input.capabilities,
    metadata: input.metadata,
  };
}
