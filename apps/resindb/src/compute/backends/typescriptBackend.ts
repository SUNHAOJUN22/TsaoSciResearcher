import { throwIfAborted } from '../taskProtocol';
import type {
  ComputeBackend,
  ComputeCapabilities,
  ComputeExecutionContext,
  ComputeKernelDefinition,
  ComputePrecision,
} from '../types';

export class TypeScriptComputeBackend implements ComputeBackend {
  readonly id = 'typescript' as const;

  isAvailable(_capabilities: ComputeCapabilities): boolean {
    return true;
  }

  supports(
    definition: ComputeKernelDefinition<unknown, unknown>,
    precision: ComputePrecision,
  ): boolean {
    const backendSupported = definition.supportedBackends?.includes(this.id) ?? true;
    const precisionSupported = definition.supportedPrecisions?.includes(precision) ?? true;
    return backendSupported && precisionSupported;
  }

  async run(
    definition: ComputeKernelDefinition<unknown, unknown>,
    input: unknown,
    context: ComputeExecutionContext,
  ): Promise<unknown> {
    throwIfAborted(context.signal);
    const output = await definition.execute(input, context);
    throwIfAborted(context.signal);
    return output;
  }
}
