import { logger } from '@/lib/logger';
import React, {
  useState,
  useMemo,
  useRef,
  useEffect,
  useCallback,
} from "react";
import { createPortal } from "react-dom";
import { Product, ColumnConfig } from '@/types/index';
import { calculateCompleteness, isLowBest } from '@/utils/productUtils';
import {
  CheckSquare,
  Square,
  ArrowUp,
  ArrowDown,
  Trash2,
  Eye,
  Copy,
  Edit,
  Tag,
  Search,
  X,
  LayoutList,
  LayoutGrid,
  Filter,
  RefreshCw,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Pin,
  PinOff,
  Sparkles,
  Radar,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useToasts } from "@/contexts/ToastContext";
import { useData } from "@/contexts/DataContext";
import { useModals } from "@/contexts/ModalContext";
import { EditProductModal } from "@/components/modals/EditProductModal";
import { DeleteConfirmationModal } from "@/components/modals/DeleteConfirmationModal";
import { motion, AnimatePresence } from "motion/react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useDataGridWorker } from '@/hooks/workers/useDataGridWorker';
import { useColumnResizing } from '@/hooks/datagrid/useColumnResizing';
import { useParetoWorker } from '@/hooks/workers/useParetoWorker';
import { useMahalanobisWorker } from '@/hooks/math/useMahalanobis';
import { ColumnResizer } from '@/components/features/DataGrid/ColumnResizer';
import { FilterItem } from '@/types/index';
import { DataGridRow } from '@/components/features/DataGrid/DataGridRow';
import { SkeletonRow, EmptyState, QuickRadarPopup } from '@/components/features/DataGrid/DataGridComponents';
import { formulaEngine } from "@/lib/formulaParser";
import { safeStorage } from '@/lib/utils';

interface DataGridProps {
  data: Product[];
  columns: ColumnConfig[];
  isLoading: boolean;
  onDelete: (ids: string[]) => void;
  onUpdate: (product: Product) => void;
  onBatchUpdate: (ids: string[], updates: Partial<Product>) => void;
  onCategorySelect: (id: string) => void;
  onViewDetails: (product: Product) => void;
  selectedIds: Set<string>;
  onSelectionChange: React.Dispatch<React.SetStateAction<Set<string>>>;
  onClearFilters?: () => void;
  onSearchChange?: (query: string) => void;
  activeFilters?: FilterItem[];
  onMoveColumn?: (fromIndex: number, toIndex: number) => void;
}

export const DataGrid: React.FC<DataGridProps> = React.memo(
  ({
    data = [],
    columns = [],
    isLoading,
    onDelete,
    onUpdate,
    onBatchUpdate,
    onCategorySelect,
    onSearchChange,
    onViewDetails,
    selectedIds = new Set<string>(),
    onSelectionChange,
    onClearFilters,
    activeFilters = [],
    onMoveColumn,
  }) => {
    const { formulas, togglePin } = useData();

    const formulaExecutor = useMemo(() => {
      return formulaEngine.compileGraph(formulas);
    }, [formulas]);

    const { setAnalyzingProduct, openModal: openModalGlobal } = useModals();
    const {
      sortedData,
      sortConfig,
      setSortConfig,
      toggleSelection,
      isComputing,
      useTopsis,
      setUseTopsis,
      topsisTop3Ids
    } = useDataGridWorker({
      data,
      columns,
      activeFilters,
      selectedIds,
      onSelectionChange,
    });
    
    const { paretoFrontIds, computePareto, isComputingPareto } = useParetoWorker();
    
    const { outlierResults, isDetecting: isDetectingOutliers, detectOutliers, clearOutliers } = useMahalanobisWorker();

    const [hoveredProduct, setHoveredProduct] = useState<{
      product: Product;
      x: number;
      y: number;
    } | null>(null);
    const [isCompact, setIsCompact] = useState(() => {
      const saved = safeStorage.local.getItem("resindb-compact");
      return saved !== null ? saved === "true" : true;
    });
    const [isRefreshing, setIsRefreshing] = useState(false);

    const [focusedIndex, setFocusedIndex] = useState(-1);
    const [contextMenu, setContextMenu] = useState<{
      x: number;
      y: number;
      product: Product;
      columnKey?: string;
      cellValue?: unknown;
    } | null>(null);
    const { t, tProp, language } = useLanguage();
    const { addToast } = useToasts();
    const [highlightedRowId, setHighlightedRowId] = useState<string | null>(null);

    const handleHighlightRow = useCallback((id: string) => {
      setHighlightedRowId(id);
      addToast("success", t("highlightedRow", "已定位并高亮对应行"));
      setTimeout(() => {
        setHighlightedRowId((prev) => (prev === id ? null : prev));
      }, 5000);
    }, [addToast, t]);

    const parentRef = useRef<HTMLDivElement>(null);

    const currentViewData = useMemo(() => {
        if (paretoFrontIds.size > 0) {
            return sortedData.filter(d => paretoFrontIds.has(d.id));
        }
        return sortedData;
    }, [sortedData, paretoFrontIds]);

    const handleToggleAllSelection = useCallback(() => {
        if (selectedIds.size === currentViewData.length) {
            onSelectionChange(new Set());
        } else {
            onSelectionChange(new Set(currentViewData.map(d => d.id)));
        }
    }, [selectedIds.size, currentViewData, onSelectionChange]);
    
    const handleCopy = async (e: React.MouseEvent | null, text: string) => {
      e?.stopPropagation();
      try {
        await navigator.clipboard.writeText(text);
        addToast("success", t("copied"));
      } catch {
        addToast("error", "Failed to copy");
      }
    };

    const rowVirtualizer = useVirtualizer({
      count: currentViewData.length,
      getScrollElement: () => parentRef.current,
      estimateSize: () => (isCompact ? 35 : 55),
      overscan: 10,
    });

    const [editingProduct, setEditingProduct] = useState<Product | null>(null);
    const [deletingIds, setDeletingIds] = useState<string[]>([]);

    const handleRefresh = () => {
      setIsRefreshing(true);
      setTimeout(() => setIsRefreshing(false), 1000);
    };

    useEffect(() => {
      safeStorage.local.setItem("resindb-compact", String(isCompact));
    }, [isCompact]);

    const visibleCols = useMemo(() => {
      return columns.filter((c) => c.visible || c.isSystem);
    }, [columns]);

    const defaultWidths = useMemo(() => {
      const widths: Record<string, number> = {
        _checkbox: 48,
        _score: 80,
        _actions: 96,
      };
      columns.forEach((c) => {
        if (c.key === "gradeName") widths[c.key] = 160;
        else if (c.key === "manufacturer") widths[c.key] = 128;
        else widths[c.key] = 192;
      });
      return widths;
    }, [columns]);

    const { columnWidths, handleResize } = useColumnResizing(defaultWidths);

    const stickyOffsets = useMemo(() => {
      const offsets: Record<string, number> = {
        _checkbox: 0,
        _score: columnWidths["_checkbox"] || 48,
      };
      let currentOffset =
        (columnWidths["_checkbox"] || 48) + (columnWidths["_score"] || 80);

      visibleCols.forEach((col) => {
        if (col.key === "gradeName" || col.isPinned) {
          offsets[col.key] = currentOffset;
          currentOffset += columnWidths[col.key] || 192;
        }
      });
      return offsets;
    }, [visibleCols, columnWidths]);

    const columnExtremes = useMemo(() => {
      const extremes: Record<string, number> = {};
      const activeCols = visibleCols.filter((c) => !c.isSystem);

      const numCols = activeCols.length;
      const numData = currentViewData.length;
      if (numCols === 0 || numData === 0) return extremes;

      const colKeys = new Array(numCols);
      const colIsLowBest = new Array(numCols);
      for (let c = 0; c < numCols; c++) {
        colKeys[c] = activeCols[c].key;
        colIsLowBest[c] = isLowBest(colKeys[c]);
      }

      const minArr = new Float32Array(numCols).fill(Infinity);
      const maxArr = new Float32Array(numCols).fill(-Infinity);
      const hasDataArr = new Uint8Array(numCols);

      for (let i = 0; i < numData; i++) {
        const props = currentViewData[i].properties;
        for (let c = 0; c < numCols; c++) {
          const rawVal = props[colKeys[c]]?.value;
          const val =
            typeof rawVal === "number" ? rawVal : parseFloat(String(rawVal));
          if (!isNaN(val)) {
            hasDataArr[c] = 1;
            if (val < minArr[c]) minArr[c] = val;
            if (val > maxArr[c]) maxArr[c] = val;
          }
        }
      }

      for (let c = 0; c < numCols; c++) {
        if (hasDataArr[c] === 1) {
          extremes[colKeys[c]] = colIsLowBest[c] ? minArr[c] : maxArr[c];
        }
      }

      return extremes;
    }, [currentViewData, visibleCols]);

    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (contextMenu) return;

        if (e.key === "ArrowDown") {
          e.preventDefault();
          setFocusedIndex((prev) => {
            const next = Math.min(prev + 1, currentViewData.length - 1);
            rowVirtualizer.scrollToIndex(next, { align: "auto" });
            return next;
          });
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setFocusedIndex((prev) => {
            const next = Math.max(prev - 1, 0);
            rowVirtualizer.scrollToIndex(next, { align: "auto" });
            return next;
          });
        } else if (e.key === "Enter" && focusedIndex >= 0) {
          onViewDetails(currentViewData[focusedIndex]);
        } else if (e.key === " " && focusedIndex >= 0) {
          e.preventDefault();
          toggleSelection(currentViewData[focusedIndex].id);
        } else if ((e.metaKey || e.ctrlKey) && e.key === "a") {
          // Only select all if grid is likely the focus target or active element is body/grid
          if (
            document.activeElement?.tagName === "BODY" ||
            document.activeElement?.closest(".group\\/grid")
          ) {
            e.preventDefault();
            handleToggleAllSelection();
          }
        } else if (e.key === "Delete" || e.key === "Backspace") {
          // Delete focused item if not in input
          const target = e.target as HTMLElement;
          if (
            target.tagName !== "INPUT" &&
            target.tagName !== "TEXTAREA" &&
            focusedIndex >= 0
          ) {
            setDeletingIds([currentViewData[focusedIndex].id]);
          }
        }
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }, [
      currentViewData,
      focusedIndex,
      contextMenu,
      onViewDetails,
      toggleSelection,
      handleToggleAllSelection,
      rowVirtualizer,
    ]);

    useEffect(() => {
      const handleWindowClick = () => {
        if (contextMenu) setContextMenu(null);
      };
      window.addEventListener("click", handleWindowClick);
      return () => window.removeEventListener("click", handleWindowClick);
    }, [contextMenu]);

    const handleContextMenu = React.useCallback(
      (
        e: React.MouseEvent,
        product: Product,
        columnKey?: string,
        cellValue?: unknown,
      ) => {
        e.preventDefault();
        setContextMenu({
          x: e.clientX,
          y: e.clientY,
          product,
          columnKey,
          cellValue,
        });
      },
      [],
    );

    const handleAnalyze = React.useCallback(
      (p: Product) => {
        setAnalyzingProduct(p);
        openModalGlobal("smartAnalysis");
      },
      [openModalGlobal, setAnalyzingProduct]
    );

    const handleCellEdit = React.useCallback((p: Product, colKey: string, newValue: string | number) => {
      let newProduct: Product;
      if (colKey === "gradeName") {
        newProduct = { ...p, gradeName: String(newValue) };
      } else if (colKey === "manufacturer") {
        newProduct = { ...p, manufacturer: String(newValue) };
      } else {
        newProduct = {
          ...p,
          properties: {
            ...p.properties,
            [colKey]: {
              ...p.properties?.[colKey],
              value: typeof newValue === 'number' || !isNaN(Number(newValue)) && newValue !== '' ? Number(newValue) : newValue,
              unit: p.properties?.[colKey]?.unit || ""
            }
          }
        };
      }
      onUpdate(newProduct);
    }, [onUpdate]);

    return (
      <div className="h-full flex flex-col relative overflow-hidden group/grid">
        {/* Context Menu */}
        {contextMenu && createPortal(
          <div
            className="fixed z-[9999] bg-white/70 dark:bg-slate-950/70 backdrop-blur-3xl border border-white/20 dark:border-white/10 rounded-2xl shadow-2xl py-2 w-48 animate-in fade-in zoom-in-95 duration-200 ring-1 ring-slate-200/50 dark:ring-slate-700/50 drop-shadow-2xl"
            style={{
              top: Math.min(contextMenu.y, window.innerHeight - 300),
              left: Math.min(contextMenu.x, window.innerWidth - 200),
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-2 border-b border-slate-100/50 dark:border-slate-800/50 mb-1">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">
                {contextMenu.product.gradeName}
              </p>
            </div>
            {contextMenu.cellValue !== undefined && (
              <motion.button
                whileHover={{
                  scale: 0.99,
                  backgroundColor: "var(--color-primary-50)",
                }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  handleCopy(
                    null,
                    String(contextMenu.cellValue)
                  );
                  setContextMenu(null);
                }}
                className="w-[calc(100%-1rem)] mx-2 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 flex items-center gap-2 transition-all group"
              >
                <Copy
                  size={14}
                  className="text-slate-400 group-hover:text-primary-500"
                />{" "}
                {t("copyCell")}
              </motion.button>
            )}
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-primary-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                handleCopy(
                  null,
                  contextMenu.product.gradeName
                );
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 flex items-center gap-2 transition-all group"
            >
              <Copy
                size={14}
                className="text-slate-400 group-hover:text-primary-500"
              />{" "}
              {t("copyGrade")}
            </motion.button>
            {contextMenu.cellValue !== undefined && onSearchChange && (
              <motion.button
                whileHover={{
                  scale: 0.99,
                  backgroundColor: "var(--color-primary-50)",
                }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  onSearchChange(String(contextMenu.cellValue));
                  setContextMenu(null);
                }}
                className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 flex items-center gap-2 transition-all group"
              >
                <Filter
                  size={14}
                  className="text-slate-400 group-hover:text-primary-500"
                />{" "}
                {t("filterThis", "筛选此项数值")}
              </motion.button>
            )}
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-primary-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                handleHighlightRow(contextMenu.product.id);
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 flex items-center gap-2 transition-all group"
            >
              <Search
                size={14}
                className="text-slate-400 group-hover:text-primary-500"
              />{" "}
              {t("locateRow", "定位并高亮对应行")}
            </motion.button>
            <div className="my-1 border-t border-slate-100/50 dark:border-slate-800/50 mx-2" />
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "rgba(79, 70, 229, 0.1)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                setAnalyzingProduct(contextMenu.product);
                openModalGlobal("smartAnalysis");
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 flex items-center gap-2 transition-all group"
            >
              <Sparkles
                size={14}
                className="text-indigo-400 group-hover:text-indigo-500"
              />{" "}
              {t("smartAnalysis", "Smart Analysis")}
            </motion.button>
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-primary-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                onUpdate(contextMenu.product);
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 flex items-center gap-2 transition-all group"
            >
              <Edit
                size={14}
                className="text-slate-400 group-hover:text-primary-500"
              />{" "}
              {t("edit", "Edit Record")}
            </motion.button>
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "rgba(225, 29, 72, 0.1)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                onDelete([contextMenu.product.id]);
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 mt-0.5 mb-1 px-3 py-2 rounded-xl text-left text-xs font-bold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/30 flex items-center gap-2 transition-all group"
            >
              <Trash2
                size={14}
                className="text-rose-400 group-hover:text-rose-500"
              />{" "}
              {t("delete", "Delete")}
            </motion.button>
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-emerald-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                onViewDetails(contextMenu.product);
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 hover:text-emerald-600 flex items-center gap-2 transition-all group"
            >
              <Eye
                size={14}
                className="text-slate-400 group-hover:text-emerald-500"
              />{" "}
              {t("viewDetails")}
            </motion.button>
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-indigo-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                // Note: window.open might be restricted in some iframe environments
                try {
                  window.open(`/?product=${contextMenu.product.id}`, "_blank");
                } catch (e) {
                  logger.error("Popup blocked", e);
                }
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 hover:text-indigo-600 flex items-center gap-2 transition-all group"
            >
              <ExternalLink
                size={14}
                className="text-slate-400 group-hover:text-indigo-500"
              />{" "}
              {t("openNewTab")}
            </motion.button>
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-amber-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                toggleSelection(contextMenu.product.id);
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-amber-50 dark:hover:bg-amber-900/30 hover:text-amber-600 flex items-center gap-2 transition-all group"
            >
              <CheckSquare
                size={14}
                className="text-slate-400 group-hover:text-amber-500"
              />{" "}
              {selectedIds.has(contextMenu.product.id)
                ? t("deselect")
                : t("addToCompare")}
            </motion.button>
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "rgba(241, 245, 249, 1)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                onBatchUpdate?.([contextMenu.product.id], {
                  updatedAt: new Date().toISOString().split("T")[0],
                });
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-primary-600 flex items-center gap-2 transition-all group"
            >
              <RefreshCw
                size={14}
                className="text-slate-400 group-hover:text-primary-500"
              />{" "}
              {t("updateTimestamp")}
            </motion.button>
            <div className="my-1 border-t border-slate-100/50 dark:border-slate-800/50 mx-2" />
            <motion.button
              whileHover={{
                scale: 0.99,
                backgroundColor: "var(--color-rose-50)",
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                onDelete([contextMenu.product.id]);
                setContextMenu(null);
              }}
              className="w-[calc(100%-1rem)] mx-2 my-0.5 px-3 py-2 rounded-xl text-left text-xs font-bold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center gap-2 transition-all group"
            >
              <Trash2
                size={14}
                className="text-rose-400 group-hover:text-rose-600"
              />{" "}
              {t("deleteRecord")}
            </motion.button>
          </div>,
          document.body
        )}

        {/* Toolbar */}
        <div className="px-3 md:px-4 py-2 border-b border-slate-200/50 dark:border-slate-800/50 flex items-center justify-between bg-white/40 dark:bg-slate-950/40 backdrop-blur-md shrink-0 z-20">
          <div className="flex items-center gap-2 md:gap-4">
            <div className="flex items-center gap-1 bg-slate-100/50 dark:bg-slate-800/50 backdrop-blur-sm shadow-inner p-1 rounded-xl">
              <motion.button
                whileHover={{
                  scale: 1.1,
                  backgroundColor: "rgba(99, 102, 241, 0.1)",
                }}
                whileTap={{ scale: 0.9, rotate: 180 }}
                onClick={handleRefresh}
                className={`p-1.5 rounded-lg transition-all ${isRefreshing ? "bg-white dark:bg-slate-700 shadow-sm text-primary-500" : "text-slate-400 hover:text-slate-600"}`}
                title="Refresh Data"
              >
                <RefreshCw
                  size={14}
                  className={isRefreshing ? "animate-spin" : ""}
                />
              </motion.button>
              <div className="w-px h-3 bg-slate-200 dark:bg-slate-800 mx-0.5" />
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsCompact(false)}
                className={`p-1.5 rounded-lg transition-all ${!isCompact ? "bg-white dark:bg-slate-700 shadow-sm text-primary-600" : "text-slate-400 hover:text-slate-600"}`}
                title="Relaxed View"
              >
                <LayoutList size={14} />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsCompact(true)}
                className={`p-1.5 rounded-lg transition-all ${isCompact ? "bg-white dark:bg-slate-700 shadow-sm text-primary-600" : "text-slate-400 hover:text-slate-600"}`}
                title="Compact View"
              >
                <LayoutGrid size={14} />
              </motion.button>
            </div>
            
            <motion.button
               whileHover={{ scale: 1.02 }}
               whileTap={{ scale: 0.98 }}
               onClick={() => setUseTopsis(!useTopsis)}
               className={`hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${
                 useTopsis 
                   ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border border-amber-200 dark:border-amber-800/50 relative overflow-hidden"
                   : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
               }`}
             >
               {useTopsis && (
                  <motion.div 
                     initial={{ x: '-100%' }}
                     animate={{ x: '200%' }}
                     transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                     className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent skew-x-12"
                  />
               )}
               <Sparkles size={14} className={useTopsis ? "text-amber-500" : ""} />
               Smart Rank (TOPSIS)
            </motion.button>
            <motion.button
               whileHover={{ scale: 1.02 }}
               whileTap={{ scale: 0.98 }}
               onClick={() => {
                   if (paretoFrontIds.size > 0) {
                      // Turn off Pareto filter
                      computePareto([], []);
                   } else {
                      // Turn on Pareto filter
                      const activeSorts = sortConfig.filter(s => s.key !== "gradeName" && s.key !== "completeness");
                      if (activeSorts.length === 0) {
                         addToast("error", "Please sort by at least two numeric columns first to set your objectives.");
                         return;
                      }
                      
                      const objectives = activeSorts.map(s => ({
                         key: s.key,
                         // To get Pareto front, 'minimize' objective means lower is better. 
                         // Sort direction 'asc' means we WANT lower values.
                         minimize: s.direction === "asc"
                      }));
                      
                      const dataPayload = sortedData.map(d => {
                          const v: Record<string, number> = {};
                          for (const o of objectives) {
                             v[o.key] = parseFloat(String(d.properties[o.key]?.value)) || 0;
                          }
                          return { id: d.id, values: v };
                      });
                      
                      computePareto(dataPayload, objectives);
                   }
               }}
               className={`hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${
                 paretoFrontIds.size > 0
                   ? "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400 border border-purple-200 dark:border-purple-800/50"
                   : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
               }`}
            >
               {isComputingPareto ? <RefreshCw size={14} className="animate-spin" /> : <Radar size={14} className={paretoFrontIds.size > 0 ? "text-purple-500" : ""} />}
               {paretoFrontIds.size > 0 ? "💎 Pareto Front: ON" : "💎 Pareto Front"}
            </motion.button>

            <motion.button
               whileHover={{ scale: 1.02 }}
               whileTap={{ scale: 0.98 }}
               onClick={() => {
                   if (Object.keys(outlierResults).length > 0) {
                      clearOutliers();
                   } else {
                      const numericFeatures = visibleCols.filter(c => c.type === 'number' && !c.isSystem && !c.isComputed).map(c => c.key);
                      detectOutliers(sortedData, numericFeatures);
                   }
               }}
               className={`hidden lg:flex items-center gap-1.5 px-3 py-1.5 ml-2 border rounded-lg text-xs font-bold transition-all shadow-sm ${
                 Object.keys(outlierResults).length > 0
                   ? "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-400 border-rose-200 dark:border-rose-800/50"
                   : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
               }`}
             >
               {isDetectingOutliers ? <RefreshCw size={14} className="animate-spin text-rose-500" /> : <Sparkles size={14} className={Object.keys(outlierResults).length > 0 ? "text-rose-500" : ""} />}
               {Object.keys(outlierResults).length > 0 ? "🧼 Clear Anomalies" : "🧼 Mahalanobis Check"}
            </motion.button>
          </div>
          <div className="flex items-center gap-2">
            <p className="hidden sm:block text-xs font-mono text-slate-400 uppercase tracking-widest">
              {sortedData.length} records
            </p>
          </div>
        </div>

        {/* Active Filters Bar */}
        <AnimatePresence mode="popLayout">
          {activeFilters.length > 0 && (
            <motion.div
              key="active-filters-container"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="px-3 md:px-4 py-2 md:py-3 bg-white/50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2 md:gap-3 shrink-0 overflow-x-auto no-scrollbar backdrop-blur-sm"
            >
              <div className="flex items-center gap-1 text-[10px] md:text-xs font-black text-slate-400 uppercase tracking-widest shrink-0">
                <Filter size={12} /> {activeFilters.length}{" "}
                <span className="hidden sm:inline">{language === "en" ? "Active Filters" : "已激活过滤器"}</span>
              </div>
              <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 shrink-0 mx-0.5 md:mx-1"></div>

              <div className="flex items-center gap-2">
                {activeFilters.map((f) => (
                  <motion.div
                    key={f.id}
                    layout
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.8, opacity: 0 }}
                    className={`flex items-center gap-1.5 px-2.5 md:px-3 py-1 md:py-1.5 rounded-lg text-[10px] md:text-xs font-bold border shadow-sm transition-all shrink-0 ${
                      f.type === "search"
                        ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-100 dark:border-blue-800"
                        : "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border-primary-100 dark:border-primary-800"
                    }`}
                  >
                    {f.type === "search" ? (
                      <Search size={10} />
                    ) : (
                      <Tag size={10} />
                    )}
                    <span className="truncate max-w-[100px] md:max-w-[150px]">
                      {f.label}
                    </span>
                    <motion.button
                      whileHover={{
                        scale: 1.1,
                        backgroundColor: "rgba(244, 63, 94, 0.1)",
                        color: "#f43f5e",
                      }}
                      whileTap={{ scale: 0.9, rotate: 90 }}
                      onClick={f.onRemove}
                      className="p-1 rounded-full hover:bg-white/50 dark:hover:bg-black/20 transition-all ml-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
                    >
                      <X size={12} />
                    </motion.button>
                  </motion.div>
                ))}
              </div>

              {onClearFilters && activeFilters.length > 1 && (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={onClearFilters}
                  className="ml-auto text-[9px] md:text-[10px] font-bold text-slate-400 hover:text-rose-500 hover:underline transition-colors whitespace-nowrap px-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/50 rounded-md shrink-0"
                >
                  {language === "en" ? "Clear All" : "清除所有"}
                </motion.button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Computing Indicator */}
        <AnimatePresence>
          {isComputing && !isLoading && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 2, opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="w-full bg-slate-100 dark:bg-slate-800 overflow-hidden"
            >
              <div className="h-full bg-primary-500 animate-[indeterminate_1.5s_infinite_linear] origin-left" style={{ width: '50%' }} />
            </motion.div>
          )}
        </AnimatePresence>

        <div
          ref={parentRef}
          className="flex-1 overflow-x-auto overflow-y-auto custom-scrollbar relative w-full h-full"
        >
          <table className="w-max min-w-full text-sm text-left border-collapse table-fixed">
            <thead className="sticky top-0 z-30 bg-white/50 dark:bg-slate-950/50 backdrop-blur-3xl shadow-[0_4px_20px_-10px_rgba(0,0,0,0.1)] dark:shadow-[0_4px_20px_-10px_rgba(255,255,255,0.05)] after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-full after:h-px after:bg-gradient-to-r after:from-transparent after:via-slate-300 dark:after:via-slate-700 after:to-transparent">
              <tr>
                <th
                  style={{ width: columnWidths["_checkbox"] || 48 }}
                  className={`px-4 border-b border-transparent bg-white/80 dark:bg-slate-950/80 backdrop-blur-md ${isCompact ? "py-2" : "py-4"} sticky left-0 z-40 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]`}
                >
                  <motion.button
                    whileHover={{
                      scale: 1.15,
                      backgroundColor: "rgba(99, 102, 241, 0.1)",
                    }}
                    whileTap={{ scale: 0.85, rotate: -15 }}
                    onClick={handleToggleAllSelection}
                    className="p-2 text-slate-400 hover:text-primary-500 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-xl"
                  >
                    {selectedIds.size > 0 &&
                    selectedIds.size === currentViewData.length ? (
                      <CheckSquare size={18} className="text-primary-500" />
                    ) : (
                      <Square size={18} />
                    )}
                  </motion.button>
                </th>
                <motion.th
                  whileHover={{ backgroundColor: "rgba(99, 102, 241, 0.05)" }}
                  whileTap={{ scale: 0.98 }}
                  style={{ 
                    width: columnWidths["_score"] || 80,
                    left: stickyOffsets["_score"],
                  }}
                  className={`px-4 border-b border-transparent bg-white/80 dark:bg-slate-950/80 backdrop-blur-md sticky z-40 font-display italic text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest cursor-pointer hover:text-primary-600 transition-all group/head ${isCompact ? "py-2" : "py-4"} shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]`}
                  onClick={(e) => setSortConfig("completeness", e.shiftKey)}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="truncate">{language === "en" ? "Score" : "完整性得分"}</span>
                    {sortConfig.find((s) => s.key === "completeness") && (
                      <div className="flex items-center gap-0.5">
                        <span className="text-primary-500">
                          {sortConfig.find((s) => s.key === "completeness")
                            ?.direction === "desc" ? (
                            <ArrowDown size={12} />
                          ) : (
                            <ArrowUp size={12} />
                          )}
                        </span>
                        {sortConfig.length > 1 && (
                          <span className="text-[9px] bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 w-3 h-3 flex items-center justify-center rounded-full font-bold">
                            {sortConfig.findIndex(
                              (s) => s.key === "completeness",
                            ) + 1}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <ColumnResizer
                    columnKey="_score"
                    width={columnWidths["_score"] || 80}
                    onResize={handleResize}
                  />
                </motion.th>
                {visibleCols.map((col, index) => {
                    const isSticky = col.key === "gradeName" || col.isPinned;
                    const stickyLeft = stickyOffsets[col.key];

                    return (
                      <motion.th
                        key={col.key}
                        whileHover={{
                          backgroundColor: "rgba(99, 102, 241, 0.05)",
                        }}
                        whileTap={{ scale: 0.98 }}
                        style={{
                          width: columnWidths[col.key],
                          left: isSticky ? stickyLeft : undefined,
                        }}
                        className={`px-4 font-display italic text-xs text-slate-500 dark:text-slate-400 uppercase tracking-[0.15em] border-b border-transparent cursor-pointer hover:text-primary-600 transition-all group/head bg-white/80 dark:bg-slate-950/80 backdrop-blur-md ${isCompact ? "py-2" : "py-4"} relative ${isSticky ? "sticky z-40 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)] border-r border-slate-100 dark:border-slate-800/50" : ""}`}
                        onClick={(e) =>
                        setSortConfig(
                          col.key,
                          e.shiftKey
                        )
                      }
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        {onMoveColumn && !col.isSystem && index > 2 && (
                          <motion.button
                            whileHover={{
                              scale: 1.2,
                              color: "var(--color-primary-500)",
                            }}
                            whileTap={{ scale: 0.8 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              onMoveColumn(
                                columns.findIndex((c) => c.key === col.key),
                                columns.findIndex((c) => c.key === col.key) - 1,
                              );
                            }}
                            className="p-1 text-slate-300 opacity-0 group-hover/head:opacity-100 transition-opacity"
                          >
                            <ChevronLeft size={10} />
                          </motion.button>
                        )}
                        <span className="truncate" title={tProp(col.label)}>
                          {tProp(col.label)}
                        </span>
                        
                        {!col.isSystem && (
                          <motion.button
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              togglePin(col.key);
                            }}
                            className={`p-1 rounded-md transition-all ${col.isPinned ? "text-primary-500 bg-primary-50 dark:bg-primary-900/40 opacity-100" : "text-slate-300 opacity-0 group-hover/head:opacity-100 hover:text-slate-500"}`}
                          >
                            {col.isPinned ? <PinOff size={10} /> : <Pin size={10} />}
                          </motion.button>
                        )}

                        {sortConfig.find((s) => s.key === col.key) && (
                          <div className="flex items-center gap-0.5 shrink-0">
                            <span className="text-primary-500">
                              {sortConfig.find((s) => s.key === col.key)
                                ?.direction === "desc" ? (
                                <ArrowDown size={12} />
                              ) : (
                                <ArrowUp size={12} />
                              )}
                            </span>
                            {sortConfig.length > 1 && (
                              <span className="text-[9px] bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 w-3 h-3 flex items-center justify-center rounded-full font-bold">
                                {sortConfig.findIndex(
                                  (s) => s.key === col.key,
                                ) + 1}
                              </span>
                            )}
                          </div>
                        )}

                        {onMoveColumn &&
                          !col.isSystem &&
                          index < visibleCols.length - 1 && (
                            <motion.button
                              whileHover={{
                                scale: 1.2,
                                color: "var(--color-primary-500)",
                              }}
                              whileTap={{ scale: 0.8 }}
                              onClick={(e) => {
                                e.stopPropagation();
                                onMoveColumn(
                                  columns.findIndex((c) => c.key === col.key),
                                  columns.findIndex((c) => c.key === col.key) +
                                    1,
                                );
                              }}
                              className="p-1 text-slate-300 opacity-0 group-hover/head:opacity-100 transition-opacity"
                            >
                              <ChevronRight size={10} />
                            </motion.button>
                          )}
                      </div>
                      <ColumnResizer
                        columnKey={col.key}
                        width={columnWidths[col.key] || 192}
                        onResize={handleResize}
                      />
                    </motion.th>
                  );
                })}
                <th
                  style={{ width: columnWidths["_actions"] || 96 }}
                  className={`px-4 border-b border-transparent text-right font-display italic text-[11px] text-slate-500 dark:text-slate-400 uppercase tracking-widest bg-white/80 dark:bg-slate-950/80 backdrop-blur-md ${isCompact ? "py-2" : "py-4"} sticky right-0 z-40 shadow-[-2px_0_5px_-2px_rgba(0,0,0,0.05)]`}
                >
                  {t("actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <SkeletonRow key={i} columns={visibleCols} />
                ))
              ) : currentViewData.length === 0 ? (
                <tr>
                  <td
                    colSpan={visibleCols.length + 3}
                    className="p-0 border border-slate-200 dark:border-slate-800"
                  >
                    <EmptyState onClearFilters={onClearFilters} />
                  </td>
                </tr>
              ) : (
                <>
                  {rowVirtualizer.getVirtualItems().length > 0 && (
                    <tr
                      style={{
                        height: `${rowVirtualizer.getVirtualItems()[0]?.start}px`,
                      }}
                    />
                  )}
                  {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                    const actualIndex = virtualRow.index;
                    const p = currentViewData[actualIndex];
                    const score = calculateCompleteness(p);
                    const isFocused = actualIndex === focusedIndex;
                    const isSelected = selectedIds.has(p.id);
                    const isHighlighted = highlightedRowId === p.id;
                    return (
                      <DataGridRow
                        key={virtualRow.key}
                        product={p}
                        index={actualIndex}
                        virtualRowKey={p.id}
                        visibleCols={visibleCols}
                        isCompact={isCompact}
                        isSelected={isSelected}
                        isFocused={isFocused}
                        isHighlighted={isHighlighted}
                        score={score}
                        columnExtremes={columnExtremes}
                        toggleSelection={toggleSelection}
                        setFocusedIndex={setFocusedIndex}
                        onViewDetails={onViewDetails}
                        onAnalyze={handleAnalyze}
                        onContextMenu={handleContextMenu}
                        onSearchChange={onSearchChange}
                        onCategorySelect={onCategorySelect}
                        setHoveredProduct={setHoveredProduct}
                        setEditingProduct={setEditingProduct}
                        onCellEdit={handleCellEdit}
                        formulaExecutor={formulaExecutor}
                        stickyOffsets={stickyOffsets}
                        topsisRank={useTopsis && topsisTop3Ids.includes(p.id) ? topsisTop3Ids.indexOf(p.id) + 1 : 0}
                        isOutlier={outlierResults[p.id]?.isOutlier || false}
                        mahalanobisAnomaly={outlierResults[p.id]}
                      />
                    );
                  })}
                  {rowVirtualizer.getVirtualItems().length > 0 && (
                    <tr
                      style={{
                        height: `${
                          rowVirtualizer.getTotalSize() -
                          (rowVirtualizer.getVirtualItems()[
                            rowVirtualizer.getVirtualItems().length - 1
                          ]?.end || 0)
                        }px`,
                      }}
                    />
                  )}
                </>
              )}
            </tbody>
          </table>
        </div>
        <AnimatePresence>
          {hoveredProduct && (
            <QuickRadarPopup
              key={`radar-${hoveredProduct.product.id}`}
              product={hoveredProduct.product}
              position={{ x: hoveredProduct.x, y: hoveredProduct.y }}
            />
          )}
        </AnimatePresence>
        <div className="flex items-center justify-between px-4 py-3 bg-white/50 dark:bg-slate-950/50 border-t border-slate-200/50 dark:border-slate-800/50 backdrop-blur-3xl z-20 shrink-0">
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
              {t("showing")}{" "}
              <span className="text-slate-700 dark:text-slate-200">
                {sortedData.length}
              </span>{" "}
              / {data.length}
            </span>
            {selectedIds.size > 0 && (
              <div className="h-4 w-px bg-slate-200 dark:bg-slate-800" />
            )}
            <AnimatePresence>
              {selectedIds.size > 0 && (
                <motion.span
                  key="selected-count-badge"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="text-[10px] font-black text-primary-500 uppercase tracking-widest"
                >
                  {selectedIds.size} {t("selected")}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>
        <EditProductModal
          isOpen={!!editingProduct}
          onClose={() => setEditingProduct(null)}
          product={editingProduct}
          onSave={async (p) => {
            onUpdate(p);
            setEditingProduct(null);
            return true;
          }}
        />
        <DeleteConfirmationModal
          isOpen={deletingIds.length > 0}
          onClose={() => setDeletingIds([])}
          onConfirm={() => {
            onDelete(deletingIds);
            setDeletingIds([]);
          }}
          productNames={deletingIds.map(
            (id) => data.find((p) => p.id === id)?.gradeName || "Unknown",
          )}
        />
      </div>
    );
  },
);
