import { ComputeBackendRouter } from './backendRouter';
import { probeComputeCapabilities } from './capabilityProbe';
import { createComputeEvidence } from './computeEvidence';
import { ComputeKernelRegistry } from './kernelRegistry';
import { createTaskAbortScope, createTaskId, raceWithAbort, throwIfAborted } from './taskProtocol';
import { TypeScriptComputeBackend } from './backends/typescriptBackend';
import type {
  ComputeBackend,
  ComputeCapabilities,
  ComputeKernelDefinition,
  ComputeTaskRequest,
  ComputeTaskResult,
} from './types';

export interface ComputeEngineDependencies {
  registry?: ComputeKernelRegistry;
  backends?: readonly ComputeBackend[];
  probeCapabilities?: () => ComputeCapabilities;
  now?: () => number;
  createTaskId?: () => string;
}

export class ComputeEngine {
  readonly registry: ComputeKernelRegistry;
  private readonly router: ComputeBackendRouter;
  private readonly probeCapabilities: () => ComputeCapabilities;
  private readonly now: () => number;
  private readonly taskIdFactory: () => string;

  constructor(dependencies: ComputeEngineDependencies = {}) {
    this.registry = dependencies.registry ?? new ComputeKernelRegistry();
    this.router = new ComputeBackendRouter(
      dependencies.backends ?? [new TypeScriptComputeBackend()],
    );
    this.probeCapabilities = dependencies.probeCapabilities ?? probeComputeCapabilities;
    this.now = dependencies.now ?? (() => globalThis.performance?.now() ?? Date.now());
    this.taskIdFactory = dependencies.createTaskId ?? createTaskId;
  }

  register<TInput, TOutput>(definition: ComputeKernelDefinition<TInput, TOutput>): this {
    this.registry.register(definition);
    return this;
  }

  async run<TInput, TOutput>(
    request: ComputeTaskRequest<TInput>,
  ): Promise<ComputeTaskResult<TOutput>> {
    const definition = this.registry.get(request.kernel);
    const requestedBackend = request.backend ?? 'auto';
    const precision = request.precision ?? 'f64';
    const priority = request.priority ?? 'scientific';
    const capabilities = this.probeCapabilities();
    const selection = this.router.select({
      preference: requestedBackend,
      allowFallback: request.allowFallback ?? false,
      definition,
      precision,
      capabilities,
    });
    const abortScope = createTaskAbortScope(request.signal, request.timeoutMs);
    const taskId = request.taskId?.trim() || this.taskIdFactory();
    const startedAt = this.now();

    try {
      throwIfAborted(abortScope.signal);
      const output = await raceWithAbort(
        selection.backend.run(definition, request.input, {
          taskId,
          precision,
          priority,
          signal: abortScope.signal,
          capabilities,
          startedAt,
        }),
        abortScope.signal,
      );
      const finishedAt = this.now();
      return {
        output: output as TOutput,
        evidence: createComputeEvidence({
          taskId,
          definition,
          requestedBackend,
          backend: selection.backend.id,
          precision,
          priority,
          input: request.input,
          startedAt,
          finishedAt,
          fallbackUsed: selection.fallbackUsed,
          capabilities,
          metadata: request.metadata,
        }),
      };
    } finally {
      abortScope.dispose();
    }
  }
}

export function createComputeEngine(
  dependencies: ComputeEngineDependencies = {},
): ComputeEngine {
  return new ComputeEngine(dependencies);
}

export const computeEngine = createComputeEngine();
