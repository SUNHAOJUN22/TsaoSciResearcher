import type { ComputeKernelDefinition } from './types';

export class ComputeKernelNotFoundError extends Error {
  constructor(kernelId: string) {
    super(`Compute kernel is not registered: ${kernelId}`);
    this.name = 'ComputeKernelNotFoundError';
  }
}

export class ComputeKernelRegistry {
  private readonly definitions = new Map<string, ComputeKernelDefinition<unknown, unknown>>();

  register<TInput, TOutput>(definition: ComputeKernelDefinition<TInput, TOutput>): this {
    const id = definition.id.trim();
    const version = definition.version.trim();
    if (!id) throw new TypeError('Compute kernel id must not be empty');
    if (!version) throw new TypeError(`Compute kernel version must not be empty: ${id}`);
    if (this.definitions.has(id)) throw new Error(`Compute kernel is already registered: ${id}`);

    this.definitions.set(id, {
      ...definition,
      id,
      version,
    } as ComputeKernelDefinition<unknown, unknown>);
    return this;
  }

  has(kernelId: string): boolean {
    return this.definitions.has(kernelId);
  }

  get(kernelId: string): ComputeKernelDefinition<unknown, unknown> {
    const definition = this.definitions.get(kernelId);
    if (!definition) throw new ComputeKernelNotFoundError(kernelId);
    return definition;
  }

  list(): readonly ComputeKernelDefinition<unknown, unknown>[] {
    return [...this.definitions.values()];
  }
}
