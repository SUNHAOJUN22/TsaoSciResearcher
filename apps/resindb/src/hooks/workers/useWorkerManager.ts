import { useState, useCallback, useRef, useEffect } from 'react';
import { sharedWorkerPool, type WorkerTaskHandle } from '@/compute/workerPool';
import { ComputeAbortError, ComputeTimeoutError, createTaskId } from '@/compute/taskProtocol';
import type { ComputePriority } from '@/compute/types';
import type { WorkerPostOptions, WorkerProgress } from '@/compute/workerProtocol';

export interface WorkerHookOptions<TResponsePayload> {
  onSuccess?: (payload: TResponsePayload) => void;
  onError?: (error: string) => void;
  onProgress?: (progress: WorkerProgress) => void;
  poolKey?: string;
  priority?: ComputePriority;
  timeoutMs?: number;
}

interface WorkerResponse<TResponsePayload> {
  type: string;
  payload?: TResponsePayload;
  error?: string;
}

function normalizePostOptions(
  options?: readonly Transferable[] | WorkerPostOptions,
): WorkerPostOptions {
  if (options && Array.isArray(options)) return { transfer: [...options] };
  return (options as WorkerPostOptions | undefined) ?? {};
}

export function useWorkerManager<TMessage, TResponsePayload>(
  workerFactory: () => Worker,
  successType: string,
  options?: WorkerHookOptions<TResponsePayload>,
) {
  const [isCalculating, setIsCalculating] = useState(false);
  const [result, setResult] = useState<TResponsePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<WorkerProgress | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const activeHandleRef = useRef<WorkerTaskHandle<WorkerResponse<TResponsePayload>> | null>(null);
  const activeTaskKeyRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  const optionsRef = useRef(options);
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      activeHandleRef.current?.cancel(new ComputeAbortError('Worker task cancelled because its consumer unmounted'));
      activeHandleRef.current = null;
      activeTaskKeyRef.current = null;
      workerRef.current = null;
    };
  }, []);

  const cancel = useCallback((reason = 'Worker task cancelled by the user') => {
    activeHandleRef.current?.cancel(new ComputeAbortError(reason));
  }, []);

  const postMessage = useCallback((
    msg: TMessage,
    postOptions?: readonly Transferable[] | WorkerPostOptions,
  ): string => {
    activeHandleRef.current?.cancel(new ComputeAbortError('Worker task superseded by a newer request'));
    activeHandleRef.current = null;
    const normalized = normalizePostOptions(postOptions);
    const currentOptions = optionsRef.current;
    const taskId = createTaskId();
    activeTaskKeyRef.current = taskId;
    const handle = sharedWorkerPool.submit<TMessage, WorkerResponse<TResponsePayload>>({
      taskId,
      poolKey: currentOptions?.poolKey?.trim() || successType,
      createWorker: workerFactory,
      message: msg,
      successType,
      transfer: normalized.transfer,
      priority: normalized.priority ?? currentOptions?.priority ?? 'scientific',
      signal: normalized.signal,
      timeoutMs: normalized.timeoutMs ?? currentOptions?.timeoutMs,
      onProgress: (nextProgress) => {
        if (!mountedRef.current || activeTaskKeyRef.current !== taskId) return;
        setProgress(nextProgress);
        currentOptions?.onProgress?.(nextProgress);
        normalized.onProgress?.(nextProgress);
      },
      onWorkerAssigned: (worker) => {
        if (activeTaskKeyRef.current === taskId) workerRef.current = worker;
      },
    });

    activeHandleRef.current = handle;
    setActiveTaskId(handle.taskId);
    setIsCalculating(true);
    setError(null);
    setProgress({ ratio: 0 });

    void handle.promise.then((response) => {
      if (!mountedRef.current || activeTaskKeyRef.current !== taskId) return;
      const payload = response.payload ?? null;
      setResult(payload);
      setError(null);
      setProgress({ ratio: 1 });
      setIsCalculating(false);
      setActiveTaskId(null);
      activeHandleRef.current = null;
      activeTaskKeyRef.current = null;
      workerRef.current = null;
      currentOptions?.onSuccess?.(response.payload as TResponsePayload);
    }).catch((reason: unknown) => {
      if (!mountedRef.current || activeTaskKeyRef.current !== taskId) return;
      const isSilentCancellation = reason instanceof ComputeAbortError
        && !(reason instanceof ComputeTimeoutError);
      const message = reason instanceof Error ? reason.message : String(reason);
      setError(isSilentCancellation ? null : message);
      setIsCalculating(false);
      setActiveTaskId(null);
      activeHandleRef.current = null;
      activeTaskKeyRef.current = null;
      workerRef.current = null;
      if (!isSilentCancellation) currentOptions?.onError?.(message);
    });

    return handle.taskId;
  }, [successType, workerFactory]);

  return {
    isCalculating,
    result,
    setResult,
    error,
    setError,
    progress,
    activeTaskId,
    cancel,
    postMessage,
    workerRef,
  };
}
