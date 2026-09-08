import type { ComputePriority } from './types';

export const WORKER_PROGRESS_TYPE = 'PROGRESS' as const;

export interface WorkerProgress {
  ratio: number;
  completed?: number;
  total?: number;
  phase?: string;
  message?: string;
}

export interface WorkerProgressMessage {
  type: typeof WORKER_PROGRESS_TYPE;
  payload: WorkerProgress;
}

export interface WorkerPostOptions {
  transfer?: readonly Transferable[];
  priority?: ComputePriority;
  signal?: AbortSignal;
  timeoutMs?: number;
  onProgress?: (progress: WorkerProgress) => void;
}

function finiteNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export function normalizeWorkerProgress(value: unknown): WorkerProgress | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Record<string, unknown>;
  const completed = finiteNumber(candidate.completed);
  const total = finiteNumber(candidate.total);
  const explicitRatio = finiteNumber(candidate.ratio);
  const derivedRatio = completed !== undefined && total !== undefined && total > 0
    ? completed / total
    : undefined;
  const ratio = explicitRatio ?? derivedRatio;
  if (ratio === undefined) return null;

  return {
    ratio: Math.max(0, Math.min(1, ratio)),
    ...(completed === undefined ? {} : { completed }),
    ...(total === undefined ? {} : { total }),
    ...(typeof candidate.phase === 'string' && candidate.phase.trim()
      ? { phase: candidate.phase.trim() }
      : {}),
    ...(typeof candidate.message === 'string' && candidate.message.trim()
      ? { message: candidate.message.trim() }
      : {}),
  };
}

export function isWorkerProgressMessage(value: unknown): value is WorkerProgressMessage {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as { type?: unknown; payload?: unknown };
  return candidate.type === WORKER_PROGRESS_TYPE && normalizeWorkerProgress(candidate.payload) !== null;
}

export function createWorkerProgressMessage(progress: WorkerProgress): WorkerProgressMessage {
  const normalized = normalizeWorkerProgress(progress);
  if (!normalized) throw new TypeError('Worker progress requires a finite ratio or completed/total values');
  return { type: WORKER_PROGRESS_TYPE, payload: normalized };
}

export function getWorkerErrorMessage(value: unknown): string | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as { error?: unknown; payload?: unknown };
  if (typeof candidate.error === 'string' && candidate.error.trim()) return candidate.error.trim();
  if (candidate.payload && typeof candidate.payload === 'object') {
    const message = (candidate.payload as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) return message.trim();
  }
  return null;
}
