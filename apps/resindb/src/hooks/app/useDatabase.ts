import { useState, useMemo, useDeferredValue, useEffect, useCallback, useRef } from 'react';
import { Product, FilterGroup, Category, Toast, SyncEvent } from '@/types/index';
import { compileFilterGroup } from '@/lib/filterUtils';
import { calculateCompleteness, getLower } from '@/utils/productUtils';
import { CATEGORY_TREE } from '@/config/constants';
import { debounce } from 'lodash';
import api from '@/lib/adapters';
import { useColumns } from '@/hooks/datagrid/useColumns';
import { propertyMap } from '@/config/i18n';
import { generateId, safeStorage } from '@/lib/utils';

const __globalProductTextIndex = new WeakMap<Product, string>();

export function useDatabase(
  categoryNameMap: Map<string, string>,
  tProp: (key: string) => string,
  addToast: (type: Toast['type'], message: string) => void,
  t: (key: string, fallback?: string) => string
) {
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [syncEvents, setSyncEvents] = useState<SyncEvent[]>(() => {
    const saved = safeStorage.local.getItem('resindb-sync-events');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Ignore malformed local history.
      }
    }
    return [];
  });

  const addSyncEvent = useCallback((event: Omit<SyncEvent, 'id' | 'timestamp'>) => {
    setSyncEvents(prev => {
      const newEvents = [
        { ...event, id: generateId(), timestamp: Date.now() },
        ...prev
      ].slice(0, 50);
      safeStorage.local.setItem('resindb-sync-events', JSON.stringify(newEvents));
      return newEvents;
    });
  }, []);

  const columnManagement = useColumns(allProducts);
  const { columns } = columnManagement;
  const propertyKeyLookup = useMemo(() => {
    const lookup = new Map<string, string>();
    for (const column of columns) {
      lookup.set(column.key.toLowerCase(), column.key);
      lookup.set(tProp(column.label).toLowerCase(), column.key);
    }
    for (const [key, translatedLabel] of Object.entries(propertyMap)) {
      lookup.set(key.toLowerCase(), key);
      lookup.set(translatedLabel.toLowerCase(), key);
    }
    return lookup;
  }, [columns, tProp]);

  const resolvePropKey = useCallback(
    (label: string): string | null => propertyKeyLookup.get(label.toLowerCase()) ?? null,
    [propertyKeyLookup],
  );

  const fetchRequestId = useRef(0);
  const fetchProducts = useCallback(async (
    query = '',
    categoryId: string | null = null,
    silent = false,
  ): Promise<boolean> => {
    const requestId = ++fetchRequestId.current;
    if (!silent) setIsLoading(true);
    try {
      const data = await api.search(query, categoryId);
      if (requestId === fetchRequestId.current) setAllProducts(data);
      return true;
    } catch (error) {
      if (requestId === fetchRequestId.current) {
        addToast('error', t('fetchDataError') + (error instanceof Error ? error.message : t('unknownError')));
      }
      return false;
    } finally {
      if (requestId === fetchRequestId.current && !silent) setIsLoading(false);
    }
  }, [addToast, t]);

  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const refreshed = await fetchProducts('', null, true);
      if (refreshed) {
        addToast('success', t('dataRefreshed'));
        addSyncEvent({ status: 'success', message: t('dataRefreshed', 'Data refreshed successfully') });
      } else {
        addSyncEvent({ status: 'error', message: t('fetchDataError', 'Data refresh failed') });
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchProducts, addToast, t, addSyncEvent]);

  useEffect(() => {
    void fetchProducts();
  }, [fetchProducts]);

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const debouncedSetQuery = useMemo(() => debounce((query: string) => setDebouncedSearchQuery(query), 300), []);
  useEffect(() => {
    debouncedSetQuery(searchQuery);
    return () => debouncedSetQuery.cancel();
  }, [searchQuery, debouncedSetQuery]);

  const deferredSearchQuery = useDeferredValue(debouncedSearchQuery);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<Set<string>>(new Set());
  const [advancedFilterGroup, setAdvancedFilterGroup] = useState<FilterGroup>({
    id: 'root',
    type: 'group',
    logic: 'AND',
    conditions: []
  });
  const [minCompleteness, setMinCompleteness] = useState(0);

  const allExpandedSelectedCategoryIds = useMemo(() => {
    if (selectedCategoryIds.size === 0) return new Set<string>();
    const ids = new Set<string>();
    const traverse = (categories: Category[], forceAdd = false) => {
      categories.forEach((category) => {
        const shouldAdd = forceAdd || selectedCategoryIds.has(category.id);
        if (shouldAdd) ids.add(category.id);
        if (category.children) traverse(category.children, shouldAdd);
      });
    };
    traverse(CATEGORY_TREE);
    return ids;
  }, [selectedCategoryIds]);

  const buildProductTextIndex = useCallback((product: Product): string => {
    const chunks: string[] = [getLower(product.gradeName), getLower(product.manufacturer)];
    product.categoryIds.forEach((id) => {
      const category = categoryNameMap.get(id);
      if (category) chunks.push(getLower(category));
    });
    for (const [key, property] of Object.entries(product.properties)) {
      chunks.push(getLower(key));
      const translatedKey = getLower(tProp(key));
      if (translatedKey && translatedKey !== getLower(key)) chunks.push(translatedKey);
      chunks.push(getLower(String(property.value)));
      if (property.unit) chunks.push(getLower(property.unit));
    }
    return chunks.join(' | ');
  }, [categoryNameMap, tProp]);

  useEffect(() => {
    if (!allProducts.length) return;

    let cancelled = false;
    let currentIndex = 0;
    let idleHandle: number | null = null;
    let intervalHandle: ReturnType<typeof setInterval> | null = null;
    const batchSize = 250;

    const processBatch = () => {
      const end = Math.min(currentIndex + batchSize, allProducts.length);
      for (let index = currentIndex; index < end; index += 1) {
        const product = allProducts[index];
        if (!__globalProductTextIndex.has(product)) {
          __globalProductTextIndex.set(product, buildProductTextIndex(product));
        }
      }
      currentIndex = end;
    };

    const idleWindow = window as Window & {
      requestIdleCallback?: (callback: (deadline: IdleDeadline) => void) => number;
      cancelIdleCallback?: (handle: number) => void;
    };

    if (idleWindow.requestIdleCallback) {
      const run = (deadline: IdleDeadline) => {
        if (cancelled) return;
        while (deadline.timeRemaining() > 0 && currentIndex < allProducts.length) processBatch();
        if (currentIndex < allProducts.length) idleHandle = idleWindow.requestIdleCallback?.(run) ?? null;
      };
      idleHandle = idleWindow.requestIdleCallback(run);
    } else {
      intervalHandle = setInterval(() => {
        if (cancelled) return;
        processBatch();
        if (currentIndex >= allProducts.length && intervalHandle) {
          clearInterval(intervalHandle);
          intervalHandle = null;
        }
      }, 50);
    }

    return () => {
      cancelled = true;
      if (intervalHandle) clearInterval(intervalHandle);
      if (idleHandle !== null) idleWindow.cancelIdleCallback?.(idleHandle);
    };
  }, [allProducts, buildProductTextIndex]);

  const filteredData = useMemo(() => {
    const syntaxRegex = /([^:\s]+(?:\s+[^:\s]+)*):([<>]=?|[^:\s]+)/g;
    const syntaxFilters: { key: string, operator: string, value: string | number, max?: number }[] = [];
    const filterMatches: { start: number, end: number }[] = [];
    let match;
    while ((match = syntaxRegex.exec(deferredSearchQuery)) !== null) {
      const [full, label, condition] = match;
      let key = resolvePropKey(label.trim());
      let matchedLabel = label.trim();
      if (!key) {
        const parts = label.trim().split(/\s+/);
        for (let index = 1; index < parts.length; index += 1) {
          const subLabel = parts.slice(index).join(' ');
          key = resolvePropKey(subLabel);
          if (key) {
            matchedLabel = subLabel;
            break;
          }
        }
      }
      if (key) {
        const filterPart = `${matchedLabel}:${condition}`;
        const filterStart = match.index + full.lastIndexOf(filterPart);
        filterMatches.push({ start: filterStart, end: filterStart + filterPart.length });
        if (condition.includes('-') && !condition.startsWith('-')) {
          const parts = condition.split('-');
          syntaxFilters.push({ key, operator: 'range', value: parseFloat(parts[0]), max: parseFloat(parts[1]) });
        } else if (condition.match(/^[<>]=?/)) {
          const operator = condition.match(/^[<>]=?/)?.[0] || '';
          syntaxFilters.push({ key, operator, value: parseFloat(condition.replace(operator, '')) });
        } else {
          const numeric = parseFloat(condition);
          syntaxFilters.push({ key, operator: '=', value: Number.isNaN(numeric) ? getLower(condition) : numeric });
        }
      }
    }

    let processedQuery = '';
    let lastIndex = 0;
    filterMatches.sort((a, b) => a.start - b.start).forEach((item) => {
      processedQuery += deferredSearchQuery.substring(lastIndex, item.start);
      lastIndex = item.end;
    });
    processedQuery += deferredSearchQuery.substring(lastIndex);

    const textKeywords = processedQuery.toLowerCase().split(' ').filter((keyword) => keyword.trim());
    const advancedPredicate = compileFilterGroup(advancedFilterGroup);
    const hasAdvancedFilters = advancedFilterGroup.conditions.length > 0;

    return allProducts.filter((product) => {
      if (minCompleteness > 0 && calculateCompleteness(product) < minCompleteness) return false;

      if (allExpandedSelectedCategoryIds.size > 0) {
        const categories = Array.isArray(product.categoryIds) ? product.categoryIds : [];
        if (!categories.some((category) => allExpandedSelectedCategoryIds.has(category))) return false;
      }

      if (textKeywords.length > 0) {
        let searchTokens = __globalProductTextIndex.get(product);
        if (searchTokens === undefined) {
          searchTokens = buildProductTextIndex(product);
          __globalProductTextIndex.set(product, searchTokens);
        }
        if (textKeywords.some((keyword) => !searchTokens.includes(keyword))) return false;
      }

      for (const filter of syntaxFilters) {
        const propertyValue = product.properties[filter.key]?.value;
        const numericValue = typeof propertyValue === 'number' ? propertyValue : parseFloat(String(propertyValue));
        let matches: boolean;
        if (Number.isNaN(numericValue) || typeof filter.value === 'string') {
          matches = getLower(String(propertyValue)).includes(filter.value as string);
        } else {
          switch (filter.operator) {
            case '>': matches = numericValue > (filter.value as number); break;
            case '<': matches = numericValue < (filter.value as number); break;
            case '>=': matches = numericValue >= (filter.value as number); break;
            case '<=': matches = numericValue <= (filter.value as number); break;
            case 'range': matches = numericValue >= (filter.value as number) && numericValue <= (filter.max ?? Infinity); break;
            case '=': matches = numericValue === (filter.value as number); break;
            default: matches = true;
          }
        }
        if (!matches) return false;
      }

      return !hasAdvancedFilters || advancedPredicate(product);
    });
  }, [allProducts, deferredSearchQuery, allExpandedSelectedCategoryIds, resolvePropKey, advancedFilterGroup, minCompleteness, buildProductTextIndex]);

  return useMemo(() => ({
    searchQuery,
    setSearchQuery,
    deferredSearchQuery,
    selectedCategoryIds,
    setSelectedCategoryIds,
    advancedFilterGroup,
    setAdvancedFilterGroup,
    minCompleteness,
    setMinCompleteness,
    filteredData,
    allProducts,
    setAllProducts,
    isLoading,
    isRefreshing,
    refreshData,
    syncEvents,
    addSyncEvent,
    resolvePropKey,
    ...columnManagement
  }), [
    searchQuery,
    deferredSearchQuery,
    selectedCategoryIds,
    advancedFilterGroup,
    minCompleteness,
    filteredData,
    allProducts,
    isLoading,
    isRefreshing,
    refreshData,
    syncEvents,
    addSyncEvent,
    resolvePropKey,
    columnManagement
  ]);
}
