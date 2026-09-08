import type {
  ComputeBackend,
  ComputeBackendId,
  ComputeBackendPreference,
  ComputeCapabilities,
  ComputeKernelDefinition,
  ComputePrecision,
} from './types';

const DEFAULT_AUTO_ORDER: readonly ComputeBackendId[] = [
  'edge',
  'webgpu',
  'wasm',
  'typescript',
];

export class ComputeBackendUnavailableError extends Error {
  constructor(backend: ComputeBackendPreference, kernel: string) {
    super(`Compute backend ${backend} is unavailable for kernel ${kernel}`);
    this.name = 'ComputeBackendUnavailableError';
  }
}

export interface BackendSelection {
  backend: ComputeBackend;
  fallbackUsed: boolean;
}

export interface BackendSelectionRequest {
  preference: ComputeBackendPreference;
  allowFallback: boolean;
  definition: ComputeKernelDefinition<unknown, unknown>;
  precision: ComputePrecision;
  capabilities: ComputeCapabilities;
}

export class ComputeBackendRouter {
  private readonly backends: ReadonlyMap<ComputeBackendId, ComputeBackend>;
  private readonly autoOrder: readonly ComputeBackendId[];

  constructor(
    backends: readonly ComputeBackend[],
    autoOrder: readonly ComputeBackendId[] = DEFAULT_AUTO_ORDER,
  ) {
    const map = new Map<ComputeBackendId, ComputeBackend>();
    for (const backend of backends) {
      if (map.has(backend.id)) throw new Error(`Duplicate compute backend: ${backend.id}`);
      map.set(backend.id, backend);
    }
    this.backends = map;
    this.autoOrder = [...autoOrder];
  }

  private isEligible(
    backend: ComputeBackend | undefined,
    request: BackendSelectionRequest,
  ): backend is ComputeBackend {
    return Boolean(
      backend
      && backend.isAvailable(request.capabilities)
      && backend.supports(request.definition, request.precision),
    );
  }

  private selectAuto(request: BackendSelectionRequest): ComputeBackend {
    for (const id of this.autoOrder) {
      const backend = this.backends.get(id);
      if (this.isEligible(backend, request)) return backend;
    }
    throw new ComputeBackendUnavailableError('auto', request.definition.id);
  }

  select(request: BackendSelectionRequest): BackendSelection {
    if (request.preference === 'auto') {
      return { backend: this.selectAuto(request), fallbackUsed: false };
    }

    const preferred = this.backends.get(request.preference);
    if (this.isEligible(preferred, request)) {
      return { backend: preferred, fallbackUsed: false };
    }

    if (request.allowFallback) {
      return { backend: this.selectAuto(request), fallbackUsed: true };
    }

    throw new ComputeBackendUnavailableError(request.preference, request.definition.id);
  }
}
