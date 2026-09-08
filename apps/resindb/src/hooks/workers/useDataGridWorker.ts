import { logger } from '@/lib/logger';
import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Product, SortConfig, ColumnConfig, FilterItem } from '@/types/index';
import { useFormulas } from '@/hooks/math/useFormulas';
import { safeStorage } from '@/lib/utils';
import type { WorkerMessage, WorkerResponse } from '@/workers/dataWorker';

interface UseDataGridWorkerProps {
  data: Product[];
  columns: ColumnConfig[];
  activeFilters?: FilterItem[];
  selectedIds?: Set<string>;
  onSelectionChange?: React.Dispatch<React.SetStateAction<Set<string>>>;
}

export function useDataGridWorker({ 
  data, 
  columns, 
  activeFilters = [], 
  selectedIds: controlledSelectedIds, 
  onSelectionChange 
}: UseDataGridWorkerProps) {
  const { formulas } = useFormulas();
  
  const [sortConfig, setSortConfig] = useState<SortConfig[]>(() => {
    const saved = safeStorage.local.getItem('resindb-sort-config-multi');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [];
  });

  const handleSetSortConfig = useCallback((key: string, multi: boolean = false) => {
    setSortConfig((prev) => {
      const existingIndex = prev.findIndex((s) => s.key === key);
      let next: SortConfig[];
      if (existingIndex > -1) {
        const existing = prev[existingIndex];
        if (existing.direction === 'asc') {
          next = [...prev];
          next[existingIndex] = { ...existing, direction: 'desc' };
        } else {
          next = prev.filter((_, i) => i !== existingIndex);
        }
      } else {
        const newSort: SortConfig = { key, direction: 'asc' };
        next = multi ? [...prev, newSort] : [newSort];
      }
      safeStorage.local.setItem('resindb-sort-config-multi', JSON.stringify(next));
      return next;
    });
  }, []);

  const [internalSelectedIds, setInternalSelectedIds] = useState<Set<string>>(new Set());
  const selectedIds = controlledSelectedIds !== undefined ? controlledSelectedIds : internalSelectedIds;
  const [useTopsis, setUseTopsis] = useState(false);
  const [topsisTop3Ids, setTopsisTop3Ids] = useState<string[]>([]);
  const [detectAnomaliesKey, setDetectAnomaliesKey] = useState<string | null>(null);
  const [outliers, setOutliers] = useState<string[]>([]);

  const updateSelection = useCallback((newSet: Set<string> | ((prev: Set<string>) => Set<string>)) => {
    if (onSelectionChange) {
      onSelectionChange(newSet);
    } else {
      setInternalSelectedIds(newSet);
    }
  }, [onSelectionChange]);

  // Worker communication and state
  const workerRef = useRef<Worker | null>(null);
  const [sortedDataIds, setSortedDataIds] = useState<string[]>([]);
  const [isComputing, setIsComputing] = useState(false);
  
  // Data map for O(1) access
  const dataMap = useMemo(() => {
    const map = new Map<string, Product>();
    for (const p of data) {
      map.set(p.id, p);
    }
    return map;
  }, [data]);

  // Derive the actual array of sorted Product objects from the ids
  const sortedData = useMemo(() => {
    const res: Product[] = [];
    for (const id of sortedDataIds) {
      const p = dataMap.get(id);
      if (p) res.push(p);
    }
    return res;
  }, [sortedDataIds, dataMap]);

  // Initialize Worker
  useEffect(() => {
    const worker = new Worker(new URL('../../workers/dataWorker.ts', import.meta.url), { type: 'module' });
    
    worker.onmessage = (e: MessageEvent<WorkerResponse>) => {
      const res = e.data;
      if (res.type === 'INIT_SUCCESS') {
        // Init ready
      } else if (res.type === 'QUERY_RESULT') {
        setSortedDataIds(res.payload.resultIds);
        setTopsisTop3Ids(res.payload.topsisTop3Ids || []);
        setOutliers(res.payload.outliers || []);
        setIsComputing(false); // Done
      } else if (res.type === 'ERROR') {
        logger.error("DataWorker Error:", res.payload.message);
        setIsComputing(false);
      }
    };
    
    workerRef.current = worker;
    return () => {
      worker.terminate();
    };
  }, []);

  // Send INIT_DATA when base data changes
  useEffect(() => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'INIT_DATA',
        payload: { allProducts: data, formulas, columns }
      } as WorkerMessage);
      
      // We should also trigger a re-query immediately to apply current filter/sort to new data
      // That'll be handled by the next useEffect, which watches data reference changes directly?
      // No, we can just trigger it if we want, but the dependency array below includes data/formulas/columns anyway.
    }
  }, [data, formulas, columns]);

  // Send QUERY when filter/sort changes (or after INIT_DATA)
  useEffect(() => {
    if (workerRef.current) {
      setIsComputing(true);
      
      const serializableFilters = activeFilters.map(({ id, label, type }) => ({
        id,
        label,
        type
      }));

      workerRef.current.postMessage({
        type: 'QUERY',
        payload: { activeFilters: serializableFilters, sortConfig, useTopsis, detectAnomaliesKey }
      } as WorkerMessage);
    }
  }, [activeFilters, sortConfig, data, formulas, columns, useTopsis, detectAnomaliesKey]); // include data to re-query after it changes

  const toggleSelection = useCallback((id: string) => {
    updateSelection(prev => {
        const newSet = new Set(prev);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        return newSet;
    });
  }, [updateSelection]);

  const toggleAllSelection = useCallback(() => {
    updateSelection(prev => {
        if (prev.size === sortedDataIds.length && sortedDataIds.length > 0) {
            return new Set();
        } else {
            return new Set(sortedDataIds);
        }
    });
  }, [sortedDataIds, updateSelection]);

  const clearSelection = useCallback(() => {
    updateSelection(new Set());
  }, [updateSelection]);

  return {
    sortedData,
    sortConfig,
    setSortConfig: handleSetSortConfig,
    selectedIds,
    toggleSelection,
    toggleAllSelection,
    clearSelection,
    isComputing,
    useTopsis,
    setUseTopsis,
    topsisTop3Ids,
    detectAnomaliesKey,
    setDetectAnomaliesKey,
    outliers
  };
}
