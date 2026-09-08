import React, { createContext, useContext, useState, useMemo, useCallback, useEffect, useRef } from "react";
import { Product, ColumnConfig, FilterGroup, ProductUpdates, FormulaConfig, FilterItem, Category, SyncEvent } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";
import { useToasts } from "@/contexts/ToastContext";
import { useUI } from "@/contexts/UIContext";
import { useDatabase } from '@/hooks/app/useDatabase';
import { CATEGORY_TREE } from '@/config/constants';
import api from '@/lib/adapters';
import { safeStorage } from "@/lib/utils";
import { useHistory } from '@/hooks/app/useHistory';
import { HistoryRecord } from "@/lib/adapters/types";

export interface RecentSearch {
  id: string;
  label: string;
  query: string;
  filters: FilterGroup;
  selectedCategoryIds: string[];
  timestamp: number;
}

interface DataContextType {
  allProducts: Product[];
  filteredData: Product[];
  isLoading: boolean;

  isRefreshing: boolean;
  refreshData: () => Promise<void>;
  syncEvents: SyncEvent[];
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  selectedCategoryIds: Set<string>;
  setSelectedCategoryIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  advancedFilterGroup: FilterGroup;
  setAdvancedFilterGroup: React.Dispatch<React.SetStateAction<FilterGroup>>;
  recentSearches: RecentSearch[];
  minCompleteness: number;
  setMinCompleteness: (val: number) => void;
  columns: ColumnConfig[];
  setColumns: React.Dispatch<React.SetStateAction<ColumnConfig[]>>;
  toggleColumn: (key: string) => void;
  toggleAllColumns: (visible: boolean) => void;
  moveColumn: (fromIndex: number, toIndex: number) => void;
  togglePin: (key: string) => void;
  formulas: FormulaConfig[];
  addFormula: (f: Omit<FormulaConfig, "id">) => void;
  updateFormula: (id: string, updates: Partial<FormulaConfig>) => void;
  removeFormula: (id: string) => void;
  categoryNameMap: Map<string, string>;
  categoryCounts: Record<string, number>;
  selectedIds: Set<string>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  setAllProducts: React.Dispatch<React.SetStateAction<Product[]>>;
  handleDelete: (ids: string[]) => Promise<void>;
  handleUpdate: (p: Product) => Promise<void>;
  handleCreate: (p: Partial<Product>) => Promise<void>;
  handleBatchUpdate: (ids: string[], updates: ProductUpdates) => Promise<void>;
  handleBatchTagging: (ids: string[], tags: string[], mode: "append" | "overwrite" | "remove") => Promise<void>;
  handleBatchReorder: (updates: { id: string, priority: number }[]) => Promise<void>;
  handleImportData: (newProducts: Product[]) => void;
  clearFilters: () => void;
  selectSingleCategory: (id: string) => void;
  activeFilters: FilterItem[];
  history: Omit<HistoryRecord, 'snapshot'>[];
  restoreSnapshot: (id: string) => Promise<void>;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { t, tProp, language } = useLanguage();
  const { addToast } = useToasts();
  const { setShowSidebar } = useUI();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>(() => {
    const saved = safeStorage.session.getItem("resindb-recent-searches");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Ignore
      }
    }
    return [];
  });

  const categoryNameMap = useMemo(() => {
    const map = new Map<string, string>();
    const traverse = (cats: Category[]) => {
      cats.forEach((c) => {
        map.set(c.id, language === "en" && c.nameEn ? c.nameEn : c.name);
        if (c.children) traverse(c.children);
      });
    };
    traverse(CATEGORY_TREE);
    return map;
  }, [language]);

  const db = useDatabase(categoryNameMap, tProp, addToast, t);
  const {
    allProducts,
    setAllProducts,
    searchQuery,
    setSearchQuery,
    selectedCategoryIds,
    setSelectedCategoryIds,
    advancedFilterGroup,
    setAdvancedFilterGroup,
    setMinCompleteness,
  } = db;

  const { history, pushToHistory, restoreSnapshot } = useHistory(allProducts, setAllProducts);

  /** Concurrent-mode-safe ref: always holds the latest committed allProducts value. */
  const allProductsRef = useRef<Product[]>(allProducts);
  useEffect(() => { allProductsRef.current = allProducts; }, [allProducts]);

  const categoryCounts = useMemo(() => {
    const products = allProducts;
    const catToProductIds: Record<string, Set<string>> = {};
    
    // 1. Map products to their directly assigned categories
    products.forEach(p => {
      p.categoryIds?.forEach(id => {
        if (!catToProductIds[id]) catToProductIds[id] = new Set();
        catToProductIds[id].add(p.id);
      });
    });

    const finalCounts: Record<string, number> = {};

    // 2. Correct propagation identifying unique products in subtree
    const collectIdsRecursive = (cat: Category): Set<string> => {
      const ids = new Set<string>(catToProductIds[cat.id] || []);
      cat.children?.forEach(child => {
        const childIds = collectIdsRecursive(child);
        childIds.forEach(id => ids.add(id));
      });
      finalCounts[cat.id] = ids.size;
      return ids;
    };
    
    CATEGORY_TREE.forEach(collectIdsRecursive);

    return finalCounts;
  }, [allProducts]);

  const handleCreate = useCallback(async (p: Partial<Product>) => {
    const tempId = `temp-${Date.now()}`;
    const optimisticProduct: Product = {
      id: tempId,
      gradeName: p.gradeName || "New Product",
      manufacturer: p.manufacturer || "Unknown",
      manufacturerId: "m-unknown",
      categoryIds: p.categoryIds || [],
      properties: p.properties || {},
      updatedAt: new Date().toISOString().split('T')[0],
      createdAt: new Date().toISOString().split('T')[0],
    };

    const previousProducts = allProductsRef.current;
    setAllProducts((prev) => [optimisticProduct, ...prev]);

    try {
      const created = await api.create(p);
      setAllProducts((prev) =>
        prev.map((old) => (old.id === tempId ? created : old)),
      );
      pushToHistory(`Create product ${p.gradeName || 'New Product'}`, previousProducts);
      addToast("success", t("createSuccess") || "Product created successfully");
    } catch (error) {
      setAllProducts((prev) => prev.filter((product) => product.id !== tempId));
      addToast(
        "error",
        (t("createFailed") || "Failed to create product: ") +
          (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, addToast, t, pushToHistory]);

  const handleDelete = useCallback(async (ids: string[]) => {
    const previousProducts = allProductsRef.current;
    setAllProducts((prev) => prev.filter((p) => !ids.includes(p.id)));
    setSelectedIds(new Set());

    try {
      await api.delete(ids);
      pushToHistory(`Delete ${ids.length} product(s)`, previousProducts);
      addToast(
        "success",
        t("deleteSuccess").replace("{count}", ids.length.toString()),
      );
      setShowSidebar(true);
    } catch (error) {
      setAllProducts(previousProducts);
      addToast(
        "error",
        t("deleteFailed") +
          (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, setSelectedIds, addToast, t, setShowSidebar, pushToHistory]);

  const handleUpdate = useCallback(async (p: Product) => {
    const previousProducts = allProductsRef.current;
    setAllProducts((prev) => prev.map((old) => (old.id === p.id ? p : old)));

    try {
      const updated = await api.update(p);
      setAllProducts((prev) =>
        prev.map((old) => (old.id === updated.id ? updated : old)),
      );
      pushToHistory(`Update product ${p.gradeName}`, previousProducts);
      addToast("success", t("updateSuccessMsg"));
      setShowSidebar(true);
    } catch (error) {
      setAllProducts(previousProducts);
      addToast(
        "error",
        t("updateFailed") +
          (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, addToast, t, setShowSidebar, pushToHistory]);

  const handleBatchUpdate = useCallback(async (ids: string[], updates: ProductUpdates) => {
    const previousProducts = allProductsRef.current;
    const { _propertyUpdates, ...restUpdates } = updates;

    setAllProducts((prev) => prev.map((p) => {
        if (!ids.includes(p.id)) return p;

        const newProperties = { ...p.properties };
        if (_propertyUpdates) {
          Object.keys(_propertyUpdates).forEach((key) => {
            const updateVal = _propertyUpdates[key];

            if (
              updateVal !== null &&
              typeof updateVal === "object" &&
              "value" in updateVal
            ) {
              newProperties[key] = { ...newProperties[key], ...updateVal };
            } else if (
              updateVal !== null &&
              (typeof updateVal === "string" || typeof updateVal === "number")
            ) {
              if (newProperties[key]) {
                newProperties[key] = {
                  ...newProperties[key],
                  value: updateVal,
                };
              } else {
                newProperties[key] = { value: updateVal, unit: "" };
              }
            }
          });
        }

        return { ...p, ...restUpdates, properties: newProperties };
      }),
    );

    try {
      await api.batchUpdate(ids, updates);
      pushToHistory(`Batch updated ${ids.length} products`, previousProducts);
      addToast("success", t("batchUpdateSuccess"));
      setShowSidebar(true);
    } catch (error) {
      setAllProducts(previousProducts);
      addToast(
        "error",
        t("batchUpdateFailed") +
          (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, addToast, t, setShowSidebar, pushToHistory]);

  const handleBatchTagging = useCallback(async (
    ids: string[],
    tagsToApply: string[],
    mode: "append" | "overwrite" | "remove"
  ) => {
    const previousProducts = allProductsRef.current;

    // Compute the updated list eagerly so we can reference it after the setter
    const applyTags = (list: Product[]): Product[] => list.map((p) => {
      if (!ids.includes(p.id)) return p;

      let newTags = p.tags ? [...p.tags] : [];
      if (mode === "append") {
        tagsToApply.forEach((tag) => {
          if (!newTags.includes(tag)) newTags.push(tag);
        });
      } else if (mode === "overwrite") {
        newTags = [...tagsToApply];
      } else if (mode === "remove") {
        newTags = newTags.filter((tag) => !tagsToApply.includes(tag));
      }

      return {
        ...p,
        tags: newTags,
        updatedAt: new Date().toISOString().split("T")[0],
      };
    });

    const updatedList = applyTags(previousProducts);
    setAllProducts((prev) => applyTags(prev));

    try {
      const affectedProducts = updatedList.filter(p => ids.includes(p.id));
      await Promise.all(affectedProducts.map(p => api.update(p)));

      const modeText = mode === "append" ? t("tagModeAppend", "append") : mode === "overwrite" ? t("tagModeOverwrite", "overwrite") : t("tagModeRemove", "remove");
      pushToHistory(t("batchTagHistory", "Bulk tag {mode} ({count} items)").replace("{mode}", modeText).replace("{count}", String(ids.length)), previousProducts);
      addToast("success", t("batchTagSuccess", "Bulk tagging updated successfully!"));
    } catch (error) {
      setAllProducts(previousProducts);
      addToast(
        "error",
        t("batchTagFailed", "Bulk tagging failed: ") +
          (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, addToast, t, pushToHistory]);

  const handleBatchReorder = useCallback(async (
    updates: { id: string; priority: number }[]
  ) => {
    const previousProducts = allProductsRef.current;

    const updateMap = new Map<string, number>();
    updates.forEach((u) => updateMap.set(u.id, u.priority));

    // Compute eagerly from ref snapshot for API call, but use functional updater for state
    const applyReorder = (list: Product[]): Product[] => list.map((p) => {
      if (!updateMap.has(p.id)) return p;
      return {
        ...p,
        priority: updateMap.get(p.id)!,
        updatedAt: new Date().toISOString().split("T")[0],
      };
    });

    const updatedList = applyReorder(previousProducts);
    setAllProducts((prev) => applyReorder(prev));

    try {
      const affectedProducts = updatedList.filter((p) => updateMap.has(p.id));
      await Promise.all(affectedProducts.map((p) => api.update(p)));

      const titleText = t("batchReorderHistory", "Bulk reorder/prioritize ({count} items)").replace("{count}", String(updates.length));
      pushToHistory(titleText, previousProducts);
      addToast("success", t("batchReorderSuccess", "Bulk reordering & priority updated successfully!"));
    } catch (error) {
      setAllProducts(previousProducts);
      addToast(
        "error",
        t("batchReorderFailed", "Bulk reordering failed: ") +
          (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, addToast, t, pushToHistory]);

  const handleImportData = useCallback(async (newProducts: Product[]) => {
    try {
      const created = await api.batchCreate(newProducts);
      const previousProducts = allProductsRef.current;
      setAllProducts((prev) => [...created, ...prev]);
      pushToHistory(`Imported ${newProducts.length} products`, previousProducts);
      addToast(
        "success",
        t("importSuccess").replace("{count}", created.length.toString()),
      );
      setShowSidebar(true);
    } catch (error) {
      addToast(
        "error",
        t("importFailed", "Import failed: ") + (error instanceof Error ? t(error.message) : t("unknownError")),
      );
    }
  }, [setAllProducts, addToast, t, setShowSidebar, pushToHistory]);

  const clearFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedCategoryIds(new Set());
    setAdvancedFilterGroup({
      id: "root",
      type: "group",
      logic: "AND",
      conditions: [],
    });
    setMinCompleteness(0);
  }, [setSearchQuery, setSelectedCategoryIds, setAdvancedFilterGroup, setMinCompleteness]);

  useEffect(() => {
    const handler = setTimeout(() => {
      const q = searchQuery.trim();
      const hasFilters = advancedFilterGroup.conditions.length > 0;
      const hasCategories = selectedCategoryIds.size > 0;
      
      if (q || hasFilters || hasCategories) {
        setRecentSearches(prev => {
          // Avoid duplicates
          const isDup = prev.some(r => 
            r.query === searchQuery && 
            JSON.stringify(r.filters) === JSON.stringify(advancedFilterGroup) &&
            JSON.stringify([...r.selectedCategoryIds].sort()) === JSON.stringify(Array.from(selectedCategoryIds).sort())
          );
          if (isDup) return prev;

          const labelParts = [];
          if (q) labelParts.push(`"${q}"`);
          if (hasCategories) labelParts.push(`${selectedCategoryIds.size} categories`);
          if (hasFilters) labelParts.push(`${advancedFilterGroup.conditions.length} filters`);
          const label = labelParts.join(" + ");

          const newSearch: RecentSearch = {
            id: Date.now().toString(),
            label,
            query: searchQuery,
            filters: advancedFilterGroup,
            selectedCategoryIds: Array.from(selectedCategoryIds),
            timestamp: Date.now()
          };

          const next = [newSearch, ...prev].slice(0, 10); // Keep last 10
          safeStorage.session.setItem("resindb-recent-searches", JSON.stringify(next));
          return next;
        });
      }
    }, 2000); // 2 second debounce to capture final query states

    return () => clearTimeout(handler);
  }, [searchQuery, advancedFilterGroup, selectedCategoryIds]);

  const selectSingleCategory = useCallback((id: string) => {
    setSelectedCategoryIds(new Set([id]));
  }, [setSelectedCategoryIds]);

  const activeFilters = useMemo(() => {
    const items: FilterItem[] = [];
    if (searchQuery.trim()) {
      items.push({
        id: "search",
        label: `Search: "${searchQuery}"`,
        type: "search",
        onRemove: () => setSearchQuery(""),
      });
    }
    selectedCategoryIds.forEach((id) => {
      items.push({
        id: id,
        label: categoryNameMap.get(id) || id,
        type: "category",
        onRemove: () => {
          setSelectedCategoryIds((prev) => {
            const next = new Set(prev);
            next.delete(id);
            return next;
          });
        },
      });
    });
    if (advancedFilterGroup.conditions.length > 0) {
      items.push({
        id: "advanced-filters",
        label: `${t("advancedFilters")} (${advancedFilterGroup.conditions.length})`,
        type: "advanced",
        onRemove: () =>
          setAdvancedFilterGroup({
            id: "root",
            type: "group",
            logic: "AND",
            conditions: [],
          }),
      });
    }
    return items;
  }, [searchQuery, setSearchQuery, selectedCategoryIds, setSelectedCategoryIds, advancedFilterGroup, setAdvancedFilterGroup, categoryNameMap, t]);

  const value = useMemo(() => ({
    ...db,
    categoryNameMap,
    categoryCounts,
    recentSearches,
    selectedIds,
    setSelectedIds,
    handleDelete,
    handleUpdate,
    handleCreate,
    handleBatchUpdate,
    handleBatchTagging,
    handleBatchReorder,
    handleImportData,
    clearFilters,
    selectSingleCategory,
    activeFilters,
    history,
    restoreSnapshot,
  }), [
    db,
    categoryNameMap,
    categoryCounts,
    recentSearches,
    selectedIds,
    handleDelete,
    handleUpdate,
    handleCreate,
    handleBatchUpdate,
    handleBatchTagging,
    handleBatchReorder,
    handleImportData,
    clearFilters,
    selectSingleCategory,
    activeFilters,
    history,
    restoreSnapshot,
  ]);

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
};

 
export const useData = () => {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error("useData must be used within a DataProvider");
  }
  return context;
};
