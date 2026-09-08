import { afterEach, describe, expect, it, vi } from 'vitest';
import { LazyWorkerPool } from '@/compute/workerPool';
import { ComputeAbortError, ComputeTimeoutError } from '@/compute/taskProtocol';
import { collectTransferables } from '@/compute/transferables';

type PostedMessage = { message: unknown; transfer: Transferable[] };

class FakeWorker {
  readonly posts: PostedMessage[] = [];
  terminated = false;
  private readonly listeners = new Map<string, Set<EventListenerOrEventListenerObject>>();

  addEventListener(type: string, listener: EventListenerOrEventListenerObject | null): void {
    if (!listener) return;
    const listeners = this.listeners.get(type) ?? new Set<EventListenerOrEventListenerObject>();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: EventListenerOrEventListenerObject | null): void {
    if (!listener) return;
    this.listeners.get(type)?.delete(listener);
  }

  postMessage(message: unknown, transfer: Transferable[] = []): void {
    this.posts.push({ message, transfer });
  }

  terminate(): void {
    this.terminated = true;
  }

  emitMessage(data: unknown): void {
    this.dispatch('message', new MessageEvent('message', { data }));
  }

  private dispatch(type: string, event: Event): void {
    for (const listener of [...(this.listeners.get(type) ?? [])]) {
      if (typeof listener === 'function') listener.call(this, event);
      else listener.handleEvent(event);
    }
  }
}

function workerFactory(workers: FakeWorker[]): () => Worker {
  return () => {
    const worker = new FakeWorker();
    workers.push(worker);
    return worker as unknown as Worker;
  };
}

afterEach(() => {
  vi.useRealTimers();
});

describe('LazyWorkerPool', () => {
  it('creates workers only on demand, reuses them, and disposes them after idle timeout', async () => {
    vi.useFakeTimers();
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 2, idleTimeoutMs: 50 });
    const createWorker = workerFactory(workers);

    expect(workers).toHaveLength(0);
    const first = pool.submit({
      poolKey: 'analysis',
      createWorker,
      message: { id: 1 },
      successType: 'DONE',
    });
    expect(workers).toHaveLength(1);

    workers[0].emitMessage({ type: 'DONE', payload: 1 });
    await expect(first.promise).resolves.toMatchObject({ payload: 1 });

    const second = pool.submit({
      poolKey: 'analysis',
      createWorker,
      message: { id: 2 },
      successType: 'DONE',
    });
    expect(workers).toHaveLength(1);
    workers[0].emitMessage({ type: 'DONE', payload: 2 });
    await second.promise;

    vi.advanceTimersByTime(50);
    expect(workers[0].terminated).toBe(true);
    expect(pool.getStats().workers).toBe(0);
    pool.dispose();
  });

  it('keeps the total worker inventory within the configured cap by evicting the oldest idle worker', async () => {
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 2, idleTimeoutMs: 10_000 });
    const createWorker = workerFactory(workers);

    for (const key of ['one', 'two']) {
      const handle = pool.submit({ poolKey: key, createWorker, message: key, successType: 'DONE' });
      workers.at(-1)?.emitMessage({ type: 'DONE', payload: key });
      await handle.promise;
    }
    expect(pool.getStats().workers).toBe(2);

    const third = pool.submit({ poolKey: 'three', createWorker, message: 'three', successType: 'DONE' });
    expect(workers[0].terminated).toBe(true);
    expect(pool.getStats().workers).toBe(2);
    workers.at(-1)?.emitMessage({ type: 'DONE', payload: 'three' });
    await third.promise;
    pool.dispose();
  });

  it('orders queued tasks by priority while preserving FIFO within each priority', async () => {
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 1, idleTimeoutMs: 1_000 });
    const createWorker = workerFactory(workers);

    const first = pool.submit({
      poolKey: 'shared', createWorker, message: { id: 'first' }, successType: 'DONE', priority: 'background',
    });
    const second = pool.submit({
      poolKey: 'shared', createWorker, message: { id: 'second' }, successType: 'DONE', priority: 'background',
    });
    const third = pool.submit({
      poolKey: 'shared', createWorker, message: { id: 'third' }, successType: 'DONE', priority: 'interactive',
    });

    expect(workers[0].posts.map((entry) => entry.message)).toEqual([{ id: 'first' }]);
    workers[0].emitMessage({ type: 'DONE', payload: 'first' });
    await first.promise;
    expect(workers[0].posts.map((entry) => entry.message)).toEqual([{ id: 'first' }, { id: 'third' }]);

    workers[0].emitMessage({ type: 'DONE', payload: 'third' });
    await third.promise;
    expect(workers[0].posts.map((entry) => entry.message)).toEqual([
      { id: 'first' }, { id: 'third' }, { id: 'second' },
    ]);

    workers[0].emitMessage({ type: 'DONE', payload: 'second' });
    await second.promise;
    pool.dispose();
  });

  it('forwards deduplicated transferables and normalized progress', async () => {
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 1, idleTimeoutMs: 1_000 });
    const createWorker = workerFactory(workers);
    const matrix = new Float64Array([1, 2, 3, 4]);
    const transfer = collectTransferables({ values: matrix, duplicate: matrix.subarray(0, 2) });
    const onProgress = vi.fn();

    expect(transfer).toEqual([matrix.buffer]);
    const handle = pool.submit({
      poolKey: 'transfer',
      createWorker,
      message: { values: matrix },
      successType: 'DONE',
      transfer: [...transfer, matrix.buffer],
      onProgress,
    });

    expect(workers[0].posts[0].transfer).toEqual([matrix.buffer]);
    workers[0].emitMessage({
      type: 'PROGRESS',
      payload: { completed: 5, total: 10, phase: 'sampling' },
    });
    expect(onProgress).toHaveBeenCalledWith({
      ratio: 0.5,
      completed: 5,
      total: 10,
      phase: 'sampling',
    });

    workers[0].emitMessage({ type: 'DONE', payload: true });
    await handle.promise;
    pool.dispose();
  });

  it('terminates an active worker when the task is cancelled', async () => {
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 1, idleTimeoutMs: 1_000 });
    const handle = pool.submit({
      poolKey: 'cancel',
      createWorker: workerFactory(workers),
      message: { id: 1 },
      successType: 'DONE',
    });

    handle.cancel('stop now');
    await expect(handle.promise).rejects.toEqual(expect.objectContaining({
      name: 'ComputeAbortError',
      message: 'stop now',
    }));
    expect(workers[0].terminated).toBe(true);
    expect(pool.getStats().running).toBe(0);
    pool.dispose();
  });

  it('enforces task timeout even when the worker never responds', async () => {
    vi.useFakeTimers();
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 1, idleTimeoutMs: 1_000 });
    const handle = pool.submit({
      poolKey: 'timeout',
      createWorker: workerFactory(workers),
      message: { id: 1 },
      successType: 'DONE',
      timeoutMs: 25,
    });

    vi.advanceTimersByTime(25);
    await expect(handle.promise).rejects.toBeInstanceOf(ComputeTimeoutError);
    expect(workers[0].terminated).toBe(true);
    pool.dispose();
  });

  it('rejects queued work when the pool key is disposed', async () => {
    const workers: FakeWorker[] = [];
    const pool = new LazyWorkerPool({ maxWorkers: 1, idleTimeoutMs: 1_000 });
    const createWorker = workerFactory(workers);
    const active = pool.submit({ poolKey: 'dispose', createWorker, message: 1, successType: 'DONE' });
    const queued = pool.submit({ poolKey: 'dispose', createWorker, message: 2, successType: 'DONE' });

    pool.disposeKey('dispose');
    await expect(active.promise).rejects.toBeInstanceOf(ComputeAbortError);
    await expect(queued.promise).rejects.toBeInstanceOf(ComputeAbortError);
    expect(workers[0].terminated).toBe(true);
    pool.dispose();
  });
});

describe('collectTransferables', () => {
  it('walks nested cyclic structures without duplicating buffers', () => {
    const data = new Uint8Array([1, 2, 3]);
    const root: { data: Uint8Array; child?: unknown; self?: unknown } = { data };
    root.child = { view: data.subarray(1) };
    root.self = root;

    expect(collectTransferables(root)).toEqual([data.buffer]);
    expect(() => collectTransferables(root, { maxDepth: -1 })).toThrow(RangeError);
  });
});
