import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  Table as TableIcon, 
  Settings2, 
  ChevronRight, 
  ChevronDown,
  BarChart3,
  Rows,
  Sigma
} from "lucide-react";
import { Product, ColumnConfig, FormulaConfig } from '@/types/index';
import { formulaEngine } from "@/lib/formulaParser";
import { useLanguage } from "@/contexts/LanguageContext";
import groupBy from "lodash/groupBy";
import { summarizeFinite } from '@/lib/numericAggregation';
import { parseFiniteNumericValue } from '@/services/mathUtils';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface PivotRow {
  _groupKey: string;
  _level: number;
  _count: number;
  _items: Product[];
  _children?: PivotRow[];
  [key: string]: string | number | Product[] | PivotRow[] | undefined;
}

interface PivotViewProps {
  data: Product[];
  columns: ColumnConfig[];
  formulas: FormulaConfig[];
}

export const PivotView: React.FC<PivotViewProps> = React.memo(({ data, columns, formulas }) => {
    const { tProp, t } = useLanguage();
  
  // Pivot Configuration State
  const [rowGroups, setRowGroups] = useState<string[]>(["gradeName"]);
  const [valueMetrics, setValueMetrics] = useState<string[]>([]);
  const [aggType, setAggType] = useState<"avg" | "sum" | "count" | "min" | "max">("avg");
  const [viewMode, setViewMode] = useState<"table" | "chart">("table");

  const availableCols = useMemo(() => {
    return columns.filter(c => !c.isSystem);
  }, [columns]);

  const numericCols = useMemo(() => {
    return availableCols.filter(c => {
      // Heuristic for numeric columns
      const sample = data.length > 0 ? data[0].properties[c.key]?.value : null;
      return typeof sample === "number" || (c.isComputed);
    });
  }, [availableCols, data]);

  // Pivot Logic
  const formulaExecutor = useMemo(() => formulaEngine.compileGraph(formulas), [formulas]);

  const pivotData = useMemo(() => {
    if (rowGroups.length === 0) return [];

    const groupRecursive = (items: Product[], groupIdx: number): PivotRow[] => {
      const groupKey = rowGroups[groupIdx];
      const col = columns.find(c => c.key === groupKey);
      
      const grouped = groupBy(items, (item) => {
        if (col?.isComputed && col.formulaId) {
          const f = formulas.find(form => form.id === col.formulaId);
          if (f) {
            return formulaExecutor(item)[f.id] ?? "N/A";
          }
        }
        const val = (item.properties[groupKey]?.value ?? (item as unknown as Record<string, unknown>)[groupKey]);
        return val ?? "N/A";
      });

      return Object.entries(grouped).map(([key, groupItems]) => {
        const row: PivotRow = {
          _groupKey: key,
          _level: groupIdx,
          _count: groupItems.length,
          _items: groupItems,
        };

        // Calculate metrics
        valueMetrics.forEach(mKey => {
          const col = columns.find(c => c.key === mKey);
          const summary = summarizeFinite(groupItems, (item) => {
            if (col?.isComputed && col.formulaId) {
              const formula = formulas.find((entry) => entry.id === col.formulaId);
              return formula
                ? parseFiniteNumericValue(formulaExecutor(item)[formula.id])
                : null;
            }
            return parseFiniteNumericValue(item.properties[mKey]?.value);
          });

          if (!summary) {
            row[mKey] = 0;
            return;
          }

          switch(aggType) {
            case "sum": row[mKey] = summary.sum; break;
            case "avg": row[mKey] = summary.mean; break;
            case "min": row[mKey] = summary.minimum; break;
            case "max": row[mKey] = summary.maximum; break;
            case "count": row[mKey] = summary.count; break;
          }
        });

        if (groupIdx < rowGroups.length - 1) {
          row._children = groupRecursive(groupItems, groupIdx + 1);
        }

        return row;
      });
    };

    return groupRecursive(data, 0);
  }, [data, rowGroups, valueMetrics, aggType, columns, formulas, formulaExecutor]);

  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleExpand = (path: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div className="flex h-full bg-slate-50 dark:bg-slate-950 overflow-hidden">
      {/* Configuration Sidebar */}
      <div className="w-72 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 p-4 overflow-y-auto custom-scrollbar">
        <div className="flex items-center gap-2.5 mb-5 shrink-0">
          <div className="p-1.5 bg-primary-100 dark:bg-primary-900/30 text-primary-600 rounded-lg">
            <Settings2 size={16} />
          </div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">{t("pivotSettings")}</h2>
        </div>

        <div className="space-y-5">
          {/* Rows */}
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
              <Rows size={12} />
              {t("rowGroups")}
            </label>
            <div className="space-y-2">
              {availableCols.map(col => (
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  key={col.key}
                  onClick={() => {
                    setRowGroups(prev => 
                      prev.includes(col.key) ? prev.filter(k => k !== col.key) : [...prev, col.key]
                    );
                  }}
                  className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-sm transition-all ${
                    rowGroups.includes(col.key)
                      ? "bg-primary-50 dark:bg-primary-900/30 text-primary-600 border border-primary-100 dark:border-primary-800"
                      : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-primary-300"
                  }`}
                >
                  {tProp(col.label)}
                  {rowGroups.includes(col.key) && (
                    <span className="text-[10px] bg-primary-500 text-white w-5 h-5 flex items-center justify-center rounded-full font-bold">
                      {rowGroups.indexOf(col.key) + 1}
                    </span>
                  )}
                </motion.button>
              ))}
            </div>
          </div>

          {/* Values */}
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
              <Sigma size={12} />
              {t("aggregationValues")}
            </label>
            <select 
              value={aggType}
              onChange={(e) => setAggType(e.target.value as "avg" | "sum" | "count" | "min" | "max")}
              className="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="avg">{t("average")}</option>
              <option value="sum">{t("sum")}</option>
              <option value="min">{t("min")}</option>
              <option value="max">{t("max")}</option>
              <option value="count">{t("count")}</option>
            </select>
            <div className="space-y-2 pt-2">
              {numericCols.map(col => (
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  key={col.key}
                  onClick={() => {
                    setValueMetrics(prev => 
                      prev.includes(col.key) ? prev.filter(k => k !== col.key) : [...prev, col.key]
                    );
                  }}
                  className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-sm transition-all ${
                    valueMetrics.includes(col.key)
                      ? "bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 border border-emerald-100 dark:border-emerald-800"
                      : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-emerald-300"
                  }`}
                >
                  {tProp(col.label)}
                </motion.button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main View Area */}
      <div className="flex-1 flex flex-col p-4 sm:p-5 md:p-6 pb-4 overflow-hidden">
        <div className="flex items-center justify-between mb-5 shrink-0">
          <div>
            <h1 className="text-xl md:text-2xl font-black text-slate-900 dark:text-white flex items-center gap-2.5">
              {t("pivotTable")}
              <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 text-xs rounded-full">
                {t("rootGroups").replace("{count}", String(pivotData.length))}
              </span>
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              {t("pivotAnalysisDesc").replace("{groups}", String(rowGroups.length)).replace("{total}", String(data.length))}
            </p>
          </div>
          
          <div className="flex bg-white dark:bg-slate-900 rounded-2xl p-1 border border-slate-200 dark:border-slate-800 shadow-sm">
            <motion.button 
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setViewMode("table")}
              className={`px-4 py-2 ${viewMode === "table" ? "bg-primary-500 text-white shadow-lg shadow-primary-500/20" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"} rounded-xl text-sm font-bold flex items-center gap-2 transition-all`}
            >
              <TableIcon size={16} /> {t("table")}
            </motion.button>
            <motion.button 
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setViewMode("chart")}
              className={`px-4 py-2 ${viewMode === "chart" ? "bg-primary-500 text-white shadow-lg shadow-primary-500/20" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"} rounded-xl text-sm font-bold flex items-center gap-2 transition-all`}
            >
              <BarChart3 size={16} /> {t("chart")}
            </motion.button>
          </div>
        </div>

        <div className="flex-1 overflow-auto rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-xl shadow-slate-200/50 dark:shadow-none custom-scrollbar p-0">
          {viewMode === "table" ? (
            <table className="w-full border-collapse">
              <thead className="sticky top-0 z-20 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-6 py-4 text-left text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    {t("groups")}
                  </th>
                  <th className="px-6 py-4 text-center text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    {t("count")}
                  </th>
                  {valueMetrics.map(mKey => (
                    <th key={mKey} className="px-6 py-4 text-right text-[10px] font-black text-slate-400 uppercase tracking-widest">
                      {tProp(columns.find(c => c.key === mKey)?.label || "")} ({aggType.toUpperCase()})
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pivotData.length === 0 ? (
                  <tr>
                    <td colSpan={2 + valueMetrics.length} className="px-6 py-20 text-center text-slate-400 italic">
                      {t("pivotEmptyState")}
                    </td>
                  </tr>
                ) : (
                  <PivotRows 
                    rows={pivotData} 
                    valueMetrics={valueMetrics} 
                    expandedRows={expandedRows} 
                    toggleExpand={toggleExpand}
                    path=""
                  />
                )}
              </tbody>
            </table>
          ) : (
            <div className="w-full h-full p-6">
              {pivotData.length === 0 || valueMetrics.length === 0 ? (
                <div className="flex items-center justify-center h-full text-slate-400 italic">
                  Select grouping criteria and at least one aggregation value to generate chart
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={pivotData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                    <XAxis 
                      dataKey="_groupKey" 
                      angle={-45} 
                      textAnchor="end" 
                      tick={{ fill: 'currentColor' }} 
                      className="text-xs text-slate-500 font-mono"
                      height={60}
                    />
                    <YAxis 
                      tick={{ fill: 'currentColor' }} 
                      className="text-xs text-slate-500 font-mono" 
                    />
                    <RechartsTooltip 
                      contentStyle={{ 
                        backgroundColor: "var(--color-slate-900)", 
                        border: "none", 
                        borderRadius: "0.75rem", 
                        color: "white" 
                      }} 
                      itemStyle={{ color: "white" }} 
                      cursor={{ fill: 'var(--color-primary-500)', opacity: 0.1 }}
                    />
                    <Legend wrapperStyle={{ paddingTop: "20px" }} />
                    {valueMetrics.map((mKey, idx) => (
                      <Bar 
                        key={mKey} 
                        dataKey={mKey} 
                        name={`${tProp(columns.find(c => c.key === mKey)?.label || "")} (${aggType})`} 
                        fill={['#475569', '#10b981', '#f59e0b', '#0ea5e9', '#f43f5e'][idx % 5]} 
                        radius={[4, 4, 0, 0]} 
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

const PivotRows: React.FC<{ 
  rows: PivotRow[], 
  valueMetrics: string[], 
  expandedRows: Set<string>,
  toggleExpand: (path: string) => void,
  path: string
}> = ({ rows, valueMetrics, expandedRows, toggleExpand, path }) => {
  return (
    <>
      {rows.map((row, idx) => {
        const currentPath = path ? `${path}.${row._groupKey}` : row._groupKey;
        const isExpanded = expandedRows.has(currentPath);
        const hasChildren = row._children && row._children.length > 0;

        return (
          <React.Fragment key={currentPath}>
            <motion.tr 
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: idx * 0.02 }}
              className={`group transition-colors ${row._level === 0 ? "bg-slate-50/50 dark:bg-slate-900/50" : "hover:bg-slate-50 dark:hover:bg-slate-900"}`}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center gap-2" style={{ paddingLeft: row._level * 24 }}>
                  {hasChildren ? (
                    <motion.button 
                      whileHover={{ scale: 1.15 }}
                      whileTap={{ scale: 0.85 }}
                      onClick={() => toggleExpand(currentPath)}
                      className="p-1 text-slate-400 hover:text-primary-500 transition-colors"
                    >
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </motion.button>
                  ) : (
                    <div className="w-5" />
                  )}
                  <span className={`text-sm ${row._level === 0 ? "font-bold text-slate-900 dark:text-white" : "text-slate-600 dark:text-slate-400"}`}>
                    {row._groupKey}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4 text-center">
                <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-500 text-[10px] font-bold rounded-full">
                  {row._count}
                </span>
              </td>
              {valueMetrics.map(mKey => (
                <td key={mKey} className="px-6 py-4 text-right font-mono text-sm font-medium text-emerald-600 dark:text-emerald-400">
                  {typeof row[mKey] === "number" ? (row[mKey] as number).toLocaleString(undefined, { maximumFractionDigits: 2 }) : (row[mKey] as string)}
                </td>
              ))}
            </motion.tr>
            <AnimatePresence>
              {isExpanded && hasChildren && (
                <PivotRows 
                  rows={row._children || []} 
                  valueMetrics={valueMetrics} 
                  expandedRows={expandedRows} 
                  toggleExpand={toggleExpand}
                  path={currentPath}
                />
              )}
            </AnimatePresence>
          </React.Fragment>
        );
      })}
    </>
  );
};
