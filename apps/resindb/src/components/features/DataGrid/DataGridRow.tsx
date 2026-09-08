import React, { useState, useCallback, useMemo } from "react";
import { Product, ColumnConfig } from '@/types/index';
import { motion, AnimatePresence } from "motion/react";
import {
  CheckSquare,
  Square,
  Copy,
  Check,
  Factory,
  Radar,
  Calculator,
  Eye,
  Edit,
  Sparkles,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { QuickEditOverlay } from "./QuickEditOverlay";

const renderCellContent = (
  val: unknown,
  unit?: string,
  isLongText = false,
  isBest = false,
  isCompact = false,
  isAnomaly = false,
): React.ReactNode => {
  if (val === null || val === undefined || val === "") {
    return (
      <span className="text-slate-300 dark:text-slate-700 font-mono">-</span>
    );
  }

  if (typeof val === "number") {
    if (isNaN(val))
      return (
        <span className="text-slate-300 dark:text-slate-700 font-mono">-</span>
      );
    return (
      <div
        className={`flex items-baseline gap-1 transition-all duration-150 hover:scale-105 hover:-translate-y-0.5 transform-gpu cursor-pointer ${isBest ? "bg-emerald-100/50 dark:bg-emerald-900/30 px-2 py-0.5 rounded-md -ml-2 border border-emerald-200/50 dark:border-emerald-800/50 w-fit drop-shadow-sm" : isAnomaly ? "bg-rose-100/80 dark:bg-rose-900/40 px-2 py-0.5 rounded-md -ml-2 border border-rose-300 dark:border-rose-700 w-fit drop-shadow-sm" : ""}`}
      >
        <span
          className={`font-mono font-bold tracking-tight ${isBest ? "text-emerald-700 dark:text-emerald-400" : isAnomaly ? "text-rose-700 dark:text-rose-400" : "text-primary-600 dark:text-primary-400"} ${isCompact ? "text-[11px]" : "text-xs"}`}
        >
          {val}
        </span>
        {unit && (
          <span
            className={`font-black uppercase tracking-tighter ${isBest ? "text-emerald-500/70" : isAnomaly ? "text-rose-500/70" : "text-slate-400"} ${isCompact ? "text-[10px]" : "text-[11px]"}`}
          >
            {unit}
          </span>
        )}
      </div>
    );
  }

  const displayStr =
    typeof val === "object" ? JSON.stringify(val) : String(val);
  return (
    <div
      className={`text-slate-700 dark:text-slate-300 font-medium ${isCompact ? "text-[11px]" : "text-xs"} ${isLongText ? "line-clamp-1 max-w-[240px]" : "truncate max-w-[180px]"}`}
      title={displayStr}
    >
      {displayStr}
    </div>
  );
};

export interface DataGridRowProps {
  product: Product;
  index: number;
  virtualRowKey: React.Key;
  visibleCols: ColumnConfig[];
  isCompact: boolean;
  isSelected: boolean;
  isFocused: boolean;
  isHighlighted?: boolean;
  score: number;
  columnExtremes: Record<string, number>;
  toggleSelection: (id: string) => void;
  setFocusedIndex: (idx: number) => void;
  onViewDetails: (p: Product) => void;
  onAnalyze: (p: Product) => void;
  onContextMenu: (
    e: React.MouseEvent,
    p: Product,
    colKey?: string,
    cellVal?: unknown,
  ) => void;
  onSearchChange?: (query: string) => void;
  onCategorySelect: (id: string) => void;
  setHoveredProduct: (
    val: { product: Product; x: number; y: number } | null,
  ) => void;
  setEditingProduct: (p: Product) => void;
  onCellEdit?: (p: Product, colKey: string, newValue: string) => void;
  formulaExecutor: (p: Product) => Record<string, number>;
  stickyOffsets: Record<string, number>;
  topsisRank?: number;
  isOutlier?: boolean;
  anomalyKey?: string | null;
  mahalanobisAnomaly?: {
    isOutlier: boolean;
    contributingFeatures: string[];
    distance: number;
  };
}

export const DataGridRow = React.memo(
  ({
    product: p,
    index,
    visibleCols,
    isCompact,
    isSelected,
    isFocused,
    isHighlighted = false,
    score,
    columnExtremes,
    toggleSelection,
    setFocusedIndex,
    onViewDetails,
    onAnalyze,
    onContextMenu,
    onSearchChange,
    onCategorySelect,
    setHoveredProduct,
    setEditingProduct,
    formulaExecutor,
    stickyOffsets,
    onCellEdit,
    topsisRank = 0,
    isOutlier = false,
    anomalyKey = null,
    mahalanobisAnomaly
  }: DataGridRowProps) => {
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [editingCell, setEditingCell] = useState<{ colKey: string; tempValue: string } | null>(null);
    const [quickEditColKey, setQuickEditColKey] = useState<string | null>(null);
    const { t, tProp, language } = useLanguage();

    const handleCopy = useCallback(
      (e: React.MouseEvent | null, text: string, id: string) => {
        if (e) e.stopPropagation();
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      },
      [],
    );

    const computedValues = useMemo(() => formulaExecutor(p), [p, formulaExecutor]);

    const handleToggleSelection = useCallback(
      (e: React.MouseEvent) => {
        e.stopPropagation();
        toggleSelection(p.id);
      },
      [toggleSelection, p.id],
    );

    const handleRowClick = useCallback(() => {
      toggleSelection(p.id);
      setFocusedIndex(index);
    }, [toggleSelection, p.id, setFocusedIndex, index]);

    const handleDblClick = useCallback(
      () => onViewDetails(p),
      [onViewDetails, p],
    );

    const handleContextMenu = useCallback(
      (e: React.MouseEvent) => onContextMenu(e, p),
      [onContextMenu, p],
    );
    
    // Highlight top 3 TOPSIS ranks
    const isTopTopsis = topsisRank > 0 && topsisRank <= 3;
    const topsisStyles = isTopTopsis 
       ? topsisRank === 1 
           ? "bg-amber-100/40 dark:bg-amber-900/40 ring-1 ring-amber-300 dark:ring-amber-700 z-10"
           : topsisRank === 2
               ? "bg-slate-200/40 dark:bg-slate-800/40 ring-1 ring-slate-300 dark:ring-slate-700 z-10"
               : "bg-orange-100/30 dark:bg-orange-900/30 ring-1 ring-orange-200 dark:ring-orange-800 z-10"
       : "";

    const anomalyStyles = mahalanobisAnomaly?.isOutlier 
       ? "ring-2 ring-rose-500/80 shadow-[0_0_15px_rgba(244,63,94,0.4)] z-20"
       : "";

    return (
      <motion.tr
        style={{ height: isCompact ? 35 : 55 }}
        data-index={index}
        className={`group transition-all duration-200 cursor-pointer relative bg-white dark:bg-slate-950 ${isSelected ? "bg-primary-50/80 dark:bg-primary-900/20" : "hover:bg-slate-50 dark:hover:bg-slate-900"} ${isFocused ? "ring-2 ring-primary-500 ring-inset z-20 bg-primary-500/5 dark:bg-primary-500/10" : ""} ${topsisStyles} ${anomalyStyles} ${isHighlighted ? "ring-4 ring-amber-500 bg-amber-500/10 dark:bg-amber-500/20 z-30 shadow-[0_0_20px_rgba(245,158,11,0.25)]" : ""}`}
        onClick={handleRowClick}
        onDoubleClick={handleDblClick}
        onContextMenu={handleContextMenu}
        title={mahalanobisAnomaly?.isOutlier ? (language === "en" ? `Deviates from 95% joint covariance threshold due to anomaly in ${mahalanobisAnomaly.contributingFeatures.map(k => tProp(k)).join(" and ")}` : `由于 ${mahalanobisAnomaly.contributingFeatures.map(k => tProp(k)).join(" 和 ")} 属性的悖逆，偏离群体协方差结构 95% 阈值`) : undefined}
      >
        <td
          style={{ left: stickyOffsets["_checkbox"] }}
          className={`px-4 border-b border-slate-200/50 dark:border-slate-800/50 ${isCompact ? "py-2.5" : "py-4"} sticky z-20 bg-white dark:bg-slate-950 transition-colors group-hover:bg-slate-50 dark:group-hover:bg-slate-900 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]`}
          onClick={handleToggleSelection}
        >
          <motion.button
            whileHover={{
              scale: 1.2,
              rotate: 5,
              backgroundColor: "rgba(99, 102, 241, 0.1)",
            }}
            whileTap={{ scale: 0.8 }}
            onClick={handleToggleSelection}
            className={`p-2 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg ${isSelected ? "text-primary-500 bg-primary-50 dark:bg-primary-900/40" : "text-slate-300 group-hover:text-slate-400"}`}
          >
            {isSelected ? <CheckSquare size={18} /> : <Square size={18} />}
          </motion.button>
          <AnimatePresence>
            {isSelected && (
              <motion.div
                key="selection-indicator"
                initial={{ opacity: 0, scaleY: 0 }}
                animate={{ opacity: 1, scaleY: 1 }}
                exit={{ opacity: 0, scaleY: 0 }}
                className="absolute left-0 top-0 bottom-0 w-1 bg-primary-500 origin-center"
              />
            )}
          </AnimatePresence>
        </td>
        <td
          style={{ left: stickyOffsets["_score"] }}
          className={`px-4 border-b border-slate-200/50 dark:border-slate-800/50 sticky z-20 bg-white dark:bg-slate-950 transition-colors group-hover:bg-slate-50 dark:group-hover:bg-slate-900 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)] ${isCompact ? "py-2.5" : "py-4"}`}
        >
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner">
              <div
                style={{ width: `${score}%` }}
                className={`h-full rounded-full transition-all duration-1000 ease-out ${score > 80 ? "bg-emerald-500" : score > 50 ? "bg-amber-500" : "bg-rose-500"}`}
              />
            </div>
            <span
              title="Material Data Quality Score: Evaluates Identification (25%), Core Specs (45%), Technical Depth (20%), and Data Richness (10%)."
              className={`font-mono text-xs tabular-nums cursor-help underline decoration-dotted decoration-slate-300 dark:decoration-slate-700 ${score > 80 ? "text-emerald-600 group-hover:text-emerald-400" : score > 50 ? "text-amber-600 group-hover:text-amber-400" : "text-rose-600 group-hover:text-rose-400"}`}
            >
              {score}%
            </span>
          </div>
        </td>
        {visibleCols.map((col) => {
          const isSticky = col.key === "gradeName" || col.isPinned;
          const stickyLeft = stickyOffsets[col.key];

          let isBest = false;
          if (!col.isSystem) {
            const val =
              col.isComputed && col.formulaId
                ? computedValues[col.formulaId]
                : p.properties?.[col.key]?.value;

            const numVal = parseFloat(String(val));
            if (
              !isNaN(numVal) &&
              columnExtremes[col.key] !== undefined &&
              columnExtremes[col.key] === numVal
            ) {
              isBest = true;
            }
          }
          
          const isAnomaly = (isOutlier && anomalyKey === col.key) || (mahalanobisAnomaly?.isOutlier && mahalanobisAnomaly.contributingFeatures.includes(col.key));

          return (
            <td
              key={col.key}
              style={{ left: isSticky ? stickyLeft : undefined }}
              className={`px-4 border-b border-slate-200/50 dark:border-slate-800/50 font-mono ${isCompact ? "py-2.5" : "py-4"} align-middle relative group/cell ${isSticky ? "sticky z-10 bg-white dark:bg-slate-950 transition-colors shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]" : ""} ${isAnomaly ? "bg-rose-50 dark:bg-rose-900/10 group-hover:bg-rose-100 dark:group-hover:bg-rose-900/20" : isSticky ? "group-hover:bg-slate-50 dark:group-hover:bg-slate-900" : ""}`}
              onDoubleClick={(e) => {
                if (col.isComputed) return;
                e.stopPropagation();
                setQuickEditColKey(col.key);
              }}
              onContextMenu={(e) => {
                e.stopPropagation();
                const val =
                  col.isComputed && col.formulaId
                    ? computedValues[col.formulaId]
                    : p.properties?.[col.key]?.value;
                const cellValue =
                  col.key === "gradeName"
                    ? p.gradeName
                    : col.key === "manufacturer"
                      ? p.manufacturer
                      : val;
                onContextMenu(e, p, col.key, cellValue);
              }}
            >
              {isBest && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute inset-0 bg-emerald-500/5 dark:bg-emerald-400/5 pointer-events-none"
                />
              )}
              {col.key === "gradeName" ? (
                <div className="flex flex-col gap-1 items-start py-0.5 justify-center">
                  <div className="flex items-center gap-2 group/cell">
                    {isTopTopsis && (
                      <span 
                        className={`flex flex-shrink-0 items-center justify-center w-5 h-5 rounded-full text-[10px] font-black shadow-sm ${
                          topsisRank === 1 
                            ? 'bg-amber-400 text-amber-900 ring-2 ring-amber-200 dark:ring-amber-800' 
                            : topsisRank === 2 
                               ? 'bg-slate-300 text-slate-700 ring-2 ring-slate-200 dark:ring-slate-600' 
                               : 'bg-orange-300 text-orange-900 ring-2 ring-orange-200 dark:ring-orange-800'
                        }`}
                      >
                        #{topsisRank}
                      </span>
                    )}
                    <span
                      className={`font-bold transition-colors truncate ${isCompact ? "text-xs" : "text-sm"} ${isTopTopsis ? (topsisRank === 1 ? 'text-amber-700 dark:text-amber-400' : 'text-slate-800 dark:text-slate-300') : ''}`}
                    >
                      {p.gradeName}
                    </span>
                    <div className="flex items-center gap-1 opacity-0 group-hover/cell:opacity-100 transition-all">
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={(e) => handleCopy(e, p.gradeName, p.id)}
                        className={`p-1.5 rounded-lg shadow-sm border transition-all active:scale-90 ${copiedId === p.id ? "text-emerald-500 bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800" : "text-slate-400 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:text-slate-600 hover:border-slate-300 dark:hover:text-slate-200 dark:hover:border-slate-600"}`}
                      >
                        {copiedId === p.id ? (
                          <Check size={12} />
                        ) : (
                          <Copy size={12} />
                        )}
                      </motion.button>
                      <div
                        onMouseEnter={(e) => {
                          e.stopPropagation();
                          setHoveredProduct({
                            product: p,
                            x: e.clientX,
                            y: e.clientY,
                          });
                        }}
                        onMouseLeave={() => setHoveredProduct(null)}
                        className="cursor-help text-indigo-500 scale-75 group-hover:scale-100 shrink-0 p-1"
                      >
                        <Radar size={14} />
                      </div>
                    </div>
                  </div>
                  {p.tags && p.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {p.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-indigo-50/80 text-indigo-600 border border-indigo-100 dark:bg-indigo-950/40 dark:text-indigo-400 dark:border-indigo-900/30 whitespace-nowrap leading-none"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : col.key === "manufacturer" ? (
                <div className="flex flex-col gap-1 items-start">
                  <motion.button
                    whileHover={{ scale: 1.02, x: 2 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSearchChange?.(`生产厂家: ${p.manufacturer}`);
                    }}
                    className="flex items-center gap-1.5 hover:text-primary-600 transition-colors text-left"
                  >
                    <Factory size={12} className="opacity-50 shrink-0" />
                    <span
                      className={`font-medium truncate ${isCompact ? "text-[11px]" : "text-xs"}`}
                    >
                      {p.manufacturer}
                    </span>
                  </motion.button>
                  {!isCompact && p.categoryIds[p.categoryIds.length - 1] && (
                    <motion.button
                      whileHover={{
                        scale: 1.05,
                        backgroundColor: "rgba(79, 70, 229, 0.1)",
                      }}
                      whileTap={{ scale: 0.95 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onCategorySelect(
                          p.categoryIds[p.categoryIds.length - 1],
                        );
                      }}
                      className="text-[10px] px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-primary-600 rounded-md transition-all truncate max-w-full"
                    >
                      {p.categoryIds[p.categoryIds.length - 1]
                        .replace("sub_", "")
                        .replace("cat_", "")
                        .toUpperCase()}
                    </motion.button>
                  )}
                </div>
              ) : col.isComputed && col.formulaId ? (
                <div className="flex items-center gap-1.5">
                  <Calculator size={12} className="text-primary-400 shrink-0" />
                  {renderCellContent(
                    computedValues[col.formulaId],
                    col.unit || "",
                    false,
                    isBest,
                    isCompact,
                    isAnomaly
                  )}
                </div>
              ) : (col.key === "聚合工艺" || col.key === "Polymerization Process" || col.key === "催化剂类型" || col.key === "Catalyst Type") && p.properties?.[col.key]?.value ? (
                <div className={`px-2 py-0.5 rounded hover:scale-105 transition-transform cursor-default inline-flex items-center gap-1.5 text-[11px] font-medium border ${col.key === "聚合工艺" || col.key === "Polymerization Process" ? "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-800" : "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200 dark:bg-fuchsia-900/30 dark:text-fuchsia-300 dark:border-fuchsia-800"}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70"></span>
                  {String(p.properties?.[col.key]?.value)}
                </div>
              ) : editingCell?.colKey === col.key ? (
                <input
                  autoFocus
                  type="text"
                  value={editingCell.tempValue}
                  onClick={(e) => e.stopPropagation()}
                  onDoubleClick={(e) => e.stopPropagation()}
                  onChange={(e) => setEditingCell({ ...editingCell, tempValue: e.target.value })}
                  onBlur={() => {
                     onCellEdit?.(p, col.key, editingCell.tempValue);
                     setEditingCell(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      onCellEdit?.(p, col.key, editingCell.tempValue);
                      setEditingCell(null);
                    } else if (e.key === "Escape") {
                      setEditingCell(null);
                    }
                  }}
                  className="w-full px-2 py-1 text-xs border-2 border-primary-500 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none"
                />
              ) : (
                renderCellContent(
                  p.properties?.[col.key]?.value,
                  p.properties?.[col.key]?.unit,
                  col.key.includes("应用"),
                  isBest,
                  isCompact,
                  isAnomaly
                )
              )}

              {!col.isComputed && (
                <div className="absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover/cell:opacity-100 transition-all z-20">
                  <motion.button
                    whileHover={{ scale: 1.15, rotate: 10 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setQuickEditColKey(col.key);
                    }}
                    className="p-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-primary-600 dark:hover:text-primary-400 border border-slate-200 dark:border-slate-700 shadow-sm transition-colors outline-none cursor-pointer"
                    title={t("快速编辑", "Quick Edit")}
                  >
                    <Edit size={10} />
                  </motion.button>
                </div>
              )}

              {quickEditColKey === col.key && (
                <QuickEditOverlay
                  colKey={col.key}
                  colLabel={
                    col.key === "gradeName"
                      ? t("牌号名称", "Grade Name")
                      : col.key === "manufacturer"
                        ? t("生产厂家", "Manufacturer")
                        : tProp(col.key)
                  }
                  initialValue={
                    col.key === "gradeName"
                      ? p.gradeName
                      : col.key === "manufacturer"
                        ? p.manufacturer
                        : (p.properties?.[col.key]?.value ?? "")
                  }
                  unit={
                    col.key === "gradeName" || col.key === "manufacturer"
                      ? undefined
                      : p.properties?.[col.key]?.unit
                  }
                  onSave={(newValue) => {
                    onCellEdit?.(p, col.key, newValue);
                    setQuickEditColKey(null);
                  }}
                  onClose={() => setQuickEditColKey(null)}
                />
              )}
            </td>
          );
        })}
        <td
          className={`px-4 border-b border-transparent ${isCompact ? "py-2.5" : "py-4"} text-right sticky right-0 z-20 bg-white dark:bg-slate-950 transition-colors group-hover:bg-slate-50 dark:group-hover:bg-slate-900 shadow-[-2px_0_5px_-2px_rgba(0,0,0,0.05)]`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 lg:group-hover:opacity-100 max-lg:opacity-100 transition-all translate-x-2 group-hover:translate-x-0">
            <motion.button
              whileHover={{
                scale: 1.1,
                backgroundColor: "rgba(99, 102, 241, 0.1)",
              }}
              whileTap={{ scale: 0.9 }}
              onClick={() => onViewDetails(p)}
              className="p-2 opacity-50 hover:opacity-100 rounded-lg text-slate-500 hover:text-primary-500 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
              title={t("details")}
            >
              <Eye size={16} />
            </motion.button>
            <motion.button
              whileHover={{
                scale: 1.1,
                backgroundColor: "rgba(79, 70, 229, 0.1)",
              }}
              whileTap={{ scale: 0.9 }}
              onClick={() => onAnalyze(p)}
              className="p-2 opacity-50 hover:opacity-100 rounded-lg text-slate-500 hover:text-indigo-500 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
              title={t("smartAnalysis", "Smart Analysis")}
            >
              <Sparkles size={16} />
            </motion.button>
            <motion.button
              whileHover={{
                scale: 1.1,
                backgroundColor: "rgba(245, 158, 11, 0.1)",
              }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setEditingProduct(p)}
              className="p-2 opacity-50 hover:opacity-100 rounded-lg text-slate-500 hover:text-amber-500 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50"
              title={t("editProduct")}
            >
              <Edit size={16} />
            </motion.button>
          </div>
        </td>
      </motion.tr>
    );
  },
  (prev, next) => {
    return (
      prev.product === next.product &&
      prev.index === next.index &&
      prev.isCompact === next.isCompact &&
      prev.isSelected === next.isSelected &&
      prev.isFocused === next.isFocused &&
      prev.score === next.score &&
      prev.columnExtremes === next.columnExtremes &&
      prev.visibleCols === next.visibleCols &&
      prev.formulaExecutor === next.formulaExecutor &&
      prev.stickyOffsets === next.stickyOffsets &&
      prev.mahalanobisAnomaly === next.mahalanobisAnomaly &&
      prev.isOutlier === next.isOutlier &&
      prev.anomalyKey === next.anomalyKey &&
      prev.topsisRank === next.topsisRank
    );
  },
);
