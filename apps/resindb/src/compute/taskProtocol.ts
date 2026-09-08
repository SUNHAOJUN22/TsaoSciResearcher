let taskSequence = 0;

export class ComputeAbortError extends Error {
  constructor(message = 'Compute task aborted') {
    super(message);
    this.name = 'ComputeAbortError';
  }
}

export class ComputeTimeoutError extends ComputeAbortError {
  readonly timeoutMs: number;

  constructor(timeoutMs: number) {
    super(`Compute task timed out after ${timeoutMs} ms`);
    this.name = 'ComputeTimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

export interface ComputeAbortScope {
  signal: AbortSignal;
  dispose(): void;
}

export function createTaskId(): string {
  const randomUuid = globalThis.crypto?.randomUUID?.bind(globalThis.crypto);
  if (randomUuid) return randomUuid();
  taskSequence += 1;
  return `compute-${Date.now().toString(36)}-${taskSequence.toString(36)}`;
}

function getAbortError(signal: AbortSignal): Error {
  const reason: unknown = signal.reason;
  if (reason instanceof Error) return reason;
  if (typeof reason === 'string' && reason.trim()) return new ComputeAbortError(reason);
  return new ComputeAbortError();
}

export function throwIfAborted(signal: AbortSignal): void {
  if (signal.aborted) throw getAbortError(signal);
}

export function raceWithAbort<T>(operation: Promise<T>, signal: AbortSignal): Promise<T> {
  if (signal.aborted) return Promise.reject(getAbortError(signal));

  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(getAbortError(signal));
    signal.addEventListener('abort', onAbort, { once: true });
    operation.then(resolve, reject).finally(() => {
      signal.removeEventListener('abort', onAbort);
    });
  });
}

export function createTaskAbortScope(
  externalSignal?: AbortSignal,
  timeoutMs?: number,
): ComputeAbortScope {
  if (timeoutMs !== undefined && (!Number.isFinite(timeoutMs) || timeoutMs <= 0)) {
    throw new RangeError('timeoutMs must be a positive finite number');
  }

  const controller = new AbortController();
  const abortFromExternal = () => controller.abort(externalSignal?.reason);

  if (externalSignal?.aborted) {
    abortFromExternal();
  } else {
    externalSignal?.addEventListener('abort', abortFromExternal, { once: true });
  }

  const timeoutHandle = timeoutMs === undefined
    ? undefined
    : globalThis.setTimeout(
      () => controller.abort(new ComputeTimeoutError(timeoutMs)),
      timeoutMs,
    );

  return {
    signal: controller.signal,
    dispose() {
      externalSignal?.removeEventListener('abort', abortFromExternal);
      if (timeoutHandle !== undefined) globalThis.clearTimeout(timeoutHandle);
    },
  };
}
