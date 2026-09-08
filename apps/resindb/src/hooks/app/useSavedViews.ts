import { logger } from '@/lib/logger';
import { useState, useCallback } from "react";
import { FilterGroup, ColumnConfig, Toast } from '@/types/index';
import { safeStorage } from '@/lib/utils';

export interface SavedView {
  id: string;
  name: string;
  query: string;
  filters: FilterGroup | null;
  columns: ColumnConfig[];
}

export function useSavedViews(
  deferredSearchQuery: string,
  advancedFilterGroup: FilterGroup,
  columns: ColumnConfig[],
  setSearchQuery: (query: string) => void,
  setAdvancedFilterGroup: (group: FilterGroup) => void,
  setColumns: React.Dispatch<React.SetStateAction<ColumnConfig[]>>,
  addToast: (type: Toast["type"], message: string) => void,
  t: (key: string, fallback?: string) => string
) {
  const [savedViews, setSavedViews] = useState<SavedView[]>(() => {
    try {
      const saved = safeStorage.local.getItem("resindb-saved-views");
      if (!saved) return [];
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      logger.error("Failed to load saved views:", e);
      return [];
    }
  });

  const saveView = useCallback(
    (name: string) => {
      try {
        const newView = {
          id: Math.random().toString(36).substr(2, 9),
          name,
          query: deferredSearchQuery,
          filters: advancedFilterGroup,
          columns: columns,
        };
        const updated = [...savedViews, newView];
        setSavedViews(updated);
        safeStorage.local.setItem("resindb-saved-views", JSON.stringify(updated));
        addToast("success", t("viewSaved").replace("{name}", name));
      } catch (e) {
        logger.error("Failed to save view:", e);
        addToast("error", t("saveFailed", "Failed to save view"));
      }
    },
    [deferredSearchQuery, advancedFilterGroup, columns, savedViews, addToast, t]
  );

  const applyView = useCallback(
    (view: SavedView) => {
      setSearchQuery(view.query);
      if (view.filters && view.filters.type === "group") {
        setAdvancedFilterGroup(view.filters);
      } else {
        setAdvancedFilterGroup({
          id: "root",
          type: "group",
          logic: "AND",
          conditions: [],
        });
      }
      setColumns((cols) =>
        cols.map((c) => {
          const savedCol = view.columns.find((sc) => sc.key === c.key);
          return savedCol ? { ...c, visible: savedCol.visible } : c;
        })
      );
      addToast("info", t("viewApplied").replace("{name}", view.name));
    },
    [addToast, t, setSearchQuery, setAdvancedFilterGroup, setColumns]
  );

  const deleteView = useCallback(
    (id: string) => {
      const updated = savedViews.filter((v) => v.id !== id);
      setSavedViews(updated);
      try {
        safeStorage.local.setItem("resindb-saved-views", JSON.stringify(updated));
      } catch {
        // Ignore
      }
    },
    [savedViews]
  );

  return {
    savedViews,
    setSavedViews, // Optional, depending on if you modify it directly elsewhere
    saveView,
    applyView,
    deleteView,
  };
}
