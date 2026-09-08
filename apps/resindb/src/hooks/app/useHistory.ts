import { logger } from '@/lib/logger';
import { useState, useCallback, useEffect, useRef } from 'react';
import { Product } from '@/types/index';
import { HistoryRecord } from '@/lib/adapters/types';
import api from '@/lib/adapters';
import { useToasts } from '@/contexts/ToastContext';
import type { HistoryWorkerMessage, HistoryWorkerResponse } from '@/workers/historyWorker';

export function useHistory(
  allProducts: Product[],
  setAllProducts: React.Dispatch<React.SetStateAction<Product[]>>
) {
  const [history, setHistory] = useState<Omit<HistoryRecord, 'snapshot'>[]>([]);
  const { addToast } = useToasts();
  const workerRef = useRef<Worker | null>(null);

  // Update a ref to always point to the latest products array without re-triggering effects
  const allProductsRef = useRef(allProducts);
  useEffect(() => {
    allProductsRef.current = allProducts;
  }, [allProducts]);

  useEffect(() => {
    const worker = new Worker(new URL('../../workers/historyWorker.ts', import.meta.url), { type: 'module' });
    
    worker.onmessage = async (e: MessageEvent<HistoryWorkerResponse>) => {
      const res = e.data;
      if (res.type === 'HISTORY_UPDATED') {
        setHistory(res.payload.history);
      } else if (res.type === 'SNAPSHOT_DATA') {
        try {
          const snapshotToRestore = res.payload.snapshot;
          
          // Before applying, push a "Undo to current" snapshot just in case it's not the recent actual state
          worker.postMessage({
            type: 'PUSH_SNAPSHOT',
            payload: {
               description: `Undo to: previous state`,
               // using the current array directly (will be structurally cloned in worker)
               snapshot: [...allProductsRef.current]
            }
          } as HistoryWorkerMessage);

          await api.restoreSnapshot(snapshotToRestore);
          setAllProducts(snapshotToRestore);
          addToast('success', `Restored successful!`);
        } catch (e) {
          logger.error(e);
          addToast('error', `Failed to restore: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
      } else if (res.type === 'ERROR') {
        logger.error("HistoryWorker Error:", res.payload.message);
      }
    };
    
    workerRef.current = worker;
    
    worker.postMessage({ type: 'GET_HISTORY' } as HistoryWorkerMessage);

    return () => {
      worker.terminate();
    };
  }, [addToast, setAllProducts]);

  const pushToHistory = useCallback((description: string, currentSnapshot: Product[]) => {
    if (workerRef.current) {
        // Structured clone automatically deep copies the snapshot array in the background
        workerRef.current.postMessage({
            type: 'PUSH_SNAPSHOT',
            payload: { description, snapshot: currentSnapshot }
        } as HistoryWorkerMessage);
    }
  }, []);

  const restoreSnapshot = useCallback(async (recordId: string) => {
    if (workerRef.current) {
         workerRef.current.postMessage({
            type: 'GET_SNAPSHOT',
            payload: { id: recordId }
         } as HistoryWorkerMessage);
    }
  }, []);

  return {
    history,
    pushToHistory,
    restoreSnapshot
  };
}
