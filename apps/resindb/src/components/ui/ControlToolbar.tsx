import React, { useState, useEffect, useCallback } from "react";
import { motion } from "motion/react";
import { Search, RefreshCw, Layers, X, Database } from "lucide-react";
import { Breadcrumbs } from '@/components/features/Dashboard/DashboardComponents';

interface ControlToolbarProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  isRefreshing: boolean;
  handleRefreshStats: () => void;
  showSummary: boolean;
  setShowSummary: (val: boolean) => void;
  onOpenDatabaseSync: () => void;
  t: (key: string, fallback?: string) => string;
}

export const ControlToolbar: React.FC<ControlToolbarProps> = React.memo(
  ({
    searchQuery,
    setSearchQuery,
    isRefreshing,
    handleRefreshStats,
    showSummary,
    setShowSummary,
    onOpenDatabaseSync,
    t,
  }) => {
    // Local state for debouncing
    const [localQuery, setLocalQuery] = useState(searchQuery);

    // Sync from props if external changes happen (like clear filters)
    useEffect(() => {
      setLocalQuery(searchQuery);
    }, [searchQuery]);

    // Use effect for debouncing local state changes up to parent
    useEffect(() => {
      const timer = setTimeout(() => {
        if (localQuery !== searchQuery) {
          setSearchQuery(localQuery);
        }
      }, 300);
      return () => clearTimeout(timer);
    }, [localQuery, setSearchQuery, searchQuery]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setLocalQuery(e.target.value);
    };

    const handleClearSearch = useCallback(() => {
      setLocalQuery("");
      setSearchQuery("");
    }, [setSearchQuery]);

    return (
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shrink-0">
        {/* Left: Breadcrumbs & Quick Filters */}
        <div className="flex items-center gap-4 flex-1 min-w-0 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <div className="shrink-0 flex items-center">
            <Breadcrumbs view="dashboard" />
          </div>

          {/* Expandable Search Input */}
          <div className="relative shrink-0 flex items-center group">
            <Search
              size={16}
              className="absolute left-3 text-slate-400 group-focus-within:text-primary-500 transition-colors pointer-events-none z-10"
            />
            <input
              id="global-search-input"
              type="text"
              placeholder={t("searchPlaceholder", "Search...")}
              value={localQuery}
              onChange={handleChange}
              className="pl-9 pr-8 py-2 h-10 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-full text-sm font-medium w-36 focus:w-64 xl:focus:w-80 transition-[width,box-shadow] duration-300 ease-in-out outline-none focus:ring-4 focus:ring-primary-500/10 focus:border-primary-500 shadow-sm hover:shadow-md"
            />
            {localQuery && (
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={handleClearSearch}
                className="absolute right-3 text-slate-400 hover:text-rose-500 focus:outline-none z-10 p-0.5 rounded-full hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
                title={t("clearSearch", "Clear")}
              >
                <X size={14} />
              </motion.button>
            )}
          </div>

          {/* Quick Filters */}
          <div className="flex items-center gap-2 shrink-0 border-l border-slate-200 dark:border-slate-800 pl-4 py-1">
            {[
              { label: t("highFlow"), query: "熔体质量流动速率 > 10" },
              { label: t("lowDensity"), query: "密度 < 0.93" },
              { label: t("highImpact"), query: "悬臂梁缺口冲击强度 > 10" },
              { label: t("filmGrade"), query: "典型应用: 薄膜" },
              { label: t("injectionGrade"), query: "典型应用: 注塑" },
            ].map((filter, idx) => (
              <motion.button
                key={idx}
                whileHover={{
                  y: -2,
                  scale: 1.05,
                }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setLocalQuery(filter.query);
                  setSearchQuery(filter.query); // Immediate trigger for quick clicks
                }}
                className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-full text-xs font-semibold text-slate-600 dark:text-slate-400 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all whitespace-nowrap shadow-sm hover:shadow-md"
              >
                {filter.label}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <motion.button
            whileHover={{ scale: 1.1, rotate: 15 }}
            whileTap={{ scale: 0.9 }}
            onClick={handleRefreshStats}
            disabled={isRefreshing}
            className="p-1.5 bg-white dark:bg-slate-950 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-all text-slate-400 hover:text-primary-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed border border-slate-200/80 dark:border-slate-800/80 shadow-sm"
            title={t("refresh")}
          >
            <RefreshCw
              size={14}
              className={
                isRefreshing
                  ? "animate-spin text-primary-500"
                  : "transition-transform duration-200"
              }
            />
          </motion.button>
          <motion.button
            whileHover={{
              scale: 1.05,
              backgroundColor: "rgba(16, 185, 129, 0.1)",
            }}
            whileTap={{ scale: 0.95 }}
            onClick={onOpenDatabaseSync}
            className="flex items-center text-[10px] font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 transition-all uppercase tracking-wider px-2 py-1 bg-emerald-50/50 dark:bg-emerald-900/20 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-md border border-emerald-100/50 dark:border-emerald-800/30 shadow-sm"
          >
            <Database size={14} className="mr-1.5" />
            {t("dbSync", "数据库验证 / 溯源")}
          </motion.button>
          <motion.button
            whileHover={{
              scale: 1.05,
              backgroundColor: "rgba(79, 70, 229, 0.1)",
            }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowSummary(!showSummary)}
            className="flex items-center text-[10px] font-bold text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-all uppercase tracking-wider px-2 py-1 bg-primary-50/50 dark:bg-primary-900/20 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-md border border-primary-100/50 dark:border-primary-800/30 shadow-sm"
          >
            <Layers size={14} className="mr-1.5" />
            {showSummary ? t("hideReport") : t("showReport")}
          </motion.button>
        </div>
      </div>
    );
  },
);
