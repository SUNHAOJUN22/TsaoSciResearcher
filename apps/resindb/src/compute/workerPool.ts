import { ComputeAbortError, createTaskAbortScope, createTaskId } from './taskProtocol';
import type { ComputePriority } from './types';
import {
  getWorkerErrorMessage,
  isWorkerProgressMessage,
  normalizeWorkerProgress,
  type WorkerProgress,
} from './workerProtocol';

const PRIORITY_RANK: Readonly<Record<ComputePriority, number>> = {
  interactive: 0,
  scientific: 1,
  background: 2,
};

export interface WorkerPoolOptions {
  maxWorkers?: number;
  idleTimeoutMs?: number;
}

export interface WorkerPoolTaskRequest<TMessage> {
  poolKey: string;
  createWorker: () => Worker;
  message: TMessage;
  successType: string | readonly string[];
  errorType?: string;
  transfer?: readonly Transferable[];
  priority?: ComputePriority;
  signal?: AbortSignal;
  timeoutMs?: number;
  taskId?: string;
  onProgress?: (progress: WorkerProgress) => void;
  onWorkerAssigned?: (worker: Worker | null) => void;
}

export interface WorkerTaskHandle<TResponse> {
  taskId: string;
  promise: Promise<TResponse>;
  cancel(reason?: unknown): void;
}

export interface WorkerPoolStats {
  queued: number;
  running: number;
  workers: number;
  idleWorkers: number;
  maxWorkers: number;
  effectiveMaxWorkers: number;
}

interface WorkerSlot {
  key: string;
  worker: Worker;
  busy: boolean;
  lastUsedAt: number;
  idleTimer?: ReturnType<typeof setTimeout>;
}

type TaskState = 'queued' | 'running' | 'settled';

interface QueuedTask {
  sequence: number;
  taskId: string;
  poolKey: string;
  createWorker: () => Worker;
  message: unknown;
  successTypes: ReadonlySet<string>;
  errorType: string;
  transfer: readonly Transferable[];
  priority: ComputePriority;
  abortScope: ReturnType<typeof createTaskAbortScope>;
  onProgress?: (progress: WorkerProgress) => void;
  onWorkerAssigned?: (worker: Worker | null) => void;
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
  state: TaskState;
  slot?: WorkerSlot;
  abortListener?: () => void;
  messageListener?: (event: MessageEvent<unknown>) => void;
  errorListener?: (event: ErrorEvent) => void;
  messageErrorListener?: () => void;
}

function defaultMaxWorkers(): number {
  const cores = typeof navigator === 'undefined' ? 2 : navigator.hardwareConcurrency || 2;
  return Math.max(1, Math.min(4, cores - 1));
}

function abortReason(signal: AbortSignal): Error {
  if (signal.reason instanceof Error) return signal.reason;
  if (typeof signal.reason === 'string' && signal.reason.trim()) {
    return new ComputeAbortError(signal.reason.trim());
  }
  return new ComputeAbortError();
}

function normalizeSuccessTypes(value: string | readonly string[]): ReadonlySet<string> {
  const values = (Array.isArray(value) ? value : [value]).map((item) => item.trim()).filter(Boolean);
  if (values.length === 0) throw new TypeError('successType must contain at least one non-empty value');
  return new Set(values);
}

export class LazyWorkerPool {
  private readonly idleTimeoutMs: number;
  private readonly queue: QueuedTask[] = [];
  private readonly slots = new Map<string, WorkerSlot[]>();
  private readonly activeTasks = new Set<QueuedTask>();
  private maxWorkers: number;
  private running = 0;
  private sequence = 0;
  private disposed = false;
  private readonly visibilityListener = () => this.pump();

  constructor(options: WorkerPoolOptions = {}) {
    const maxWorkers = options.maxWorkers ?? defaultMaxWorkers();
    const idleTimeoutMs = options.idleTimeoutMs ?? 30_000;
    if (!Number.isInteger(maxWorkers) || maxWorkers < 1) {
      throw new RangeError('maxWorkers must be a positive integer');
    }
    if (!Number.isFinite(idleTimeoutMs) || idleTimeoutMs < 0) {
      throw new RangeError('idleTimeoutMs must be a non-negative finite number');
    }
    this.maxWorkers = maxWorkers;
    this.idleTimeoutMs = idleTimeoutMs;
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.visibilityListener);
    }
  }

  submit<TMessage, TResponse = unknown>(
    request: WorkerPoolTaskRequest<TMessage>,
  ): WorkerTaskHandle<TResponse> {
    if (this.disposed) throw new Error('Worker pool has been disposed');
    const poolKey = request.poolKey.trim();
    if (!poolKey) throw new TypeError('poolKey must be a non-empty string');
    const abortScope = createTaskAbortScope(request.signal, request.timeoutMs);
    const taskId = request.taskId?.trim() || createTaskId();
    let task!: QueuedTask;
    const promise = new Promise<TResponse>((resolve, reject) => {
      task = {
        sequence: this.sequence += 1,
        taskId,
        poolKey,
        createWorker: request.createWorker,
        message: request.message,
        successTypes: normalizeSuccessTypes(request.successType),
        errorType: request.errorType?.trim() || 'ERROR',
        transfer: [...new Set(request.transfer ?? [])],
        priority: request.priority ?? 'scientific',
        abortScope,
        onProgress: request.onProgress,
        onWorkerAssigned: request.onWorkerAssigned,
        resolve: (value) => resolve(value as TResponse),
        reject,
        state: 'queued',
      };
    });

    const cancel = (reason?: unknown) => {
      this.cancelTask(task, reason);
    };

    task.abortListener = () => this.cancelTask(task, abortReason(task.abortScope.signal));
    task.abortScope.signal.addEventListener('abort', task.abortListener, { once: true });
    if (task.abortScope.signal.aborted) {
      this.cancelTask(task, abortReason(task.abortScope.signal));
    } else {
      this.queue.push(task);
      this.sortQueue();
      this.pump();
    }

    return { taskId, promise, cancel };
  }

  setMaxWorkers(maxWorkers: number): void {
    if (!Number.isInteger(maxWorkers) || maxWorkers < 1) {
      throw new RangeError('maxWorkers must be a positive integer');
    }
    this.maxWorkers = maxWorkers;
    this.trimIdleWorkers();
    this.pump();
  }

  getStats(): WorkerPoolStats {
    const allSlots = [...this.slots.values()].flat();
    return {
      queued: this.queue.length,
      running: this.running,
      workers: allSlots.length,
      idleWorkers: allSlots.filter((slot) => !slot.busy).length,
      maxWorkers: this.maxWorkers,
      effectiveMaxWorkers: this.effectiveMaxWorkers(),
    };
  }

  disposeKey(poolKey: string): void {
    const key = poolKey.trim();
    for (const task of [...this.queue]) {
      if (task.poolKey === key) this.cancelTask(task, new ComputeAbortError(`Worker pool ${key} disposed`));
    }
    for (const task of this.runningTasks()) {
      if (task.poolKey === key) this.cancelTask(task, new ComputeAbortError(`Worker pool ${key} disposed`));
    }
    for (const slot of [...(this.slots.get(key) ?? [])]) this.terminateSlot(slot);
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.visibilityListener);
    }
    for (const task of [...this.queue, ...this.runningTasks()]) {
      this.cancelTask(task, new ComputeAbortError('Worker pool disposed'));
    }
    for (const slot of [...this.slots.values()].flat()) this.terminateSlot(slot);
  }

  private runningTasks(): QueuedTask[] {
    return [...this.activeTasks];
  }

  private effectiveMaxWorkers(): number {
    return typeof document !== 'undefined' && document.hidden ? 1 : this.maxWorkers;
  }

  private sortQueue(): void {
    this.queue.sort((left, right) => (
      PRIORITY_RANK[left.priority] - PRIORITY_RANK[right.priority]
      || left.sequence - right.sequence
    ));
  }

  private pump(): void {
    if (this.disposed) return;
    while (this.running < this.effectiveMaxWorkers() && this.queue.length > 0) {
      const task = this.queue.shift();
      if (!task || task.state !== 'queued') continue;
      if (task.abortScope.signal.aborted) {
        this.cancelTask(task, abortReason(task.abortScope.signal));
        continue;
      }
      let slot: WorkerSlot;
      try {
        slot = this.acquireSlot(task.poolKey, task.createWorker);
      } catch (error) {
        this.settle(task, undefined, error, true);
        continue;
      }
      this.startTask(task, slot);
    }
  }

  private acquireSlot(poolKey: string, factory: () => Worker): WorkerSlot {
    const existing = this.slots.get(poolKey) ?? [];
    const idle = existing.find((slot) => !slot.busy);
    if (idle) {
      if (idle.idleTimer !== undefined) clearTimeout(idle.idleTimer);
      idle.idleTimer = undefined;
      idle.lastUsedAt = Date.now();
      return idle;
    }

    const allSlots = [...this.slots.values()].flat();
    if (allSlots.length >= this.maxWorkers) {
      const eviction = allSlots
        .filter((slot) => !slot.busy)
        .sort((left, right) => left.lastUsedAt - right.lastUsedAt)[0];
      if (!eviction) throw new Error('Worker pool capacity is exhausted');
      this.terminateSlot(eviction);
    }

    const slot: WorkerSlot = {
      key: poolKey,
      worker: factory(),
      busy: false,
      lastUsedAt: Date.now(),
    };
    existing.push(slot);
    this.slots.set(poolKey, existing);
    return slot;
  }

  private startTask(task: QueuedTask, slot: WorkerSlot): void {
    task.state = 'running';
    task.slot = slot;
    slot.busy = true;
    this.running += 1;
    this.activeTasks.add(task);
    task.onWorkerAssigned?.(slot.worker);

    task.messageListener = (event) => {
      if (isWorkerProgressMessage(event.data)) {
        const progress = normalizeWorkerProgress(event.data.payload);
        if (progress) task.onProgress?.(progress);
        return;
      }
      const responseType = event.data && typeof event.data === 'object'
        ? (event.data as { type?: unknown }).type
        : undefined;
      if (responseType === task.errorType) {
        this.settle(task, undefined, new Error(getWorkerErrorMessage(event.data) ?? 'Worker execution failed'));
        return;
      }
      if (typeof responseType === 'string' && task.successTypes.has(responseType)) {
        this.settle(task, event.data, undefined);
      }
    };
    task.errorListener = (event) => {
      this.settle(task, undefined, new Error(event.message || 'Worker execution failed'), true);
    };
    task.messageErrorListener = () => {
      this.settle(task, undefined, new Error('Worker response could not be deserialized'), true);
    };

    slot.worker.addEventListener('message', task.messageListener);
    slot.worker.addEventListener('error', task.errorListener);
    slot.worker.addEventListener('messageerror', task.messageErrorListener);

    try {
      slot.worker.postMessage(task.message, [...task.transfer]);
    } catch (error) {
      this.settle(task, undefined, error, true);
    }
  }

  private cancelTask(task: QueuedTask, reason?: unknown): void {
    if (task.state === 'settled') return;
    const error = reason instanceof Error
      ? reason
      : new ComputeAbortError(typeof reason === 'string' ? reason : undefined);
    if (task.state === 'queued') {
      const index = this.queue.indexOf(task);
      if (index >= 0) this.queue.splice(index, 1);
      this.settle(task, undefined, error);
      return;
    }
    this.settle(task, undefined, error, true);
  }

  private settle(
    task: QueuedTask,
    response?: unknown,
    error?: unknown,
    terminateWorker = false,
  ): void {
    if (task.state === 'settled') return;
    const wasRunning = task.state === 'running';
    task.state = 'settled';
    if (task.abortListener) {
      task.abortScope.signal.removeEventListener('abort', task.abortListener);
    }
    task.abortScope.dispose();

    if (wasRunning && task.slot) {
      const { slot } = task;
      if (task.messageListener) slot.worker.removeEventListener('message', task.messageListener);
      if (task.errorListener) slot.worker.removeEventListener('error', task.errorListener);
      if (task.messageErrorListener) slot.worker.removeEventListener('messageerror', task.messageErrorListener);
      this.running = Math.max(0, this.running - 1);
      this.activeTasks.delete(task);
      task.onWorkerAssigned?.(null);
      if (terminateWorker) {
        this.terminateSlot(slot);
      } else {
        slot.busy = false;
        slot.lastUsedAt = Date.now();
        this.scheduleIdleDisposal(slot);
      }
    }

    if (error !== undefined) task.reject(error);
    else task.resolve(response);
    this.pump();
  }

  private trimIdleWorkers(): void {
    const idle = [...this.slots.values()]
      .flat()
      .filter((slot) => !slot.busy)
      .sort((left, right) => left.lastUsedAt - right.lastUsedAt);
    while ([...this.slots.values()].flat().length > this.maxWorkers && idle.length > 0) {
      const slot = idle.shift();
      if (slot) this.terminateSlot(slot);
    }
  }

  private scheduleIdleDisposal(slot: WorkerSlot): void {
    if (slot.idleTimer !== undefined) clearTimeout(slot.idleTimer);
    slot.idleTimer = setTimeout(() => {
      if (!slot.busy) this.terminateSlot(slot);
    }, this.idleTimeoutMs);
  }

  private terminateSlot(slot: WorkerSlot): void {
    if (slot.idleTimer !== undefined) clearTimeout(slot.idleTimer);
    slot.worker.terminate();
    const existing = this.slots.get(slot.key) ?? [];
    const remaining = existing.filter((candidate) => candidate !== slot);
    if (remaining.length === 0) this.slots.delete(slot.key);
    else this.slots.set(slot.key, remaining);
  }
}

export const sharedWorkerPool = new LazyWorkerPool();
