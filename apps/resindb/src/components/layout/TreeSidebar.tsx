import React, { useState, useMemo, useCallback } from "react";
import { Category } from '@/types/index';
import {
  Layers,
  Search,
  Sparkles,
  ChevronsDown,
  ChevronsUp,
  X,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence } from "motion/react";
import { TreeNode } from "@/components/ui/TreeNode";

interface TreeSidebarProps {
  categories: Category[];
  selectedCategoryIds: Set<string>;
  onToggleCategory: (id: string) => void;
  onClearCategories: () => void;
  totalCount?: number;
  counts?: Record<string, number>;
  minCompleteness: number;
  onMinCompletenessChange: (val: number) => void;
  isLoading?: boolean;
  className?: string; // added optional className
}

export const TreeSidebar: React.FC<TreeSidebarProps> = ({
  categories,
  selectedCategoryIds,
  onToggleCategory,
  onClearCategories,
  totalCount = 0,
  counts = {},
  minCompleteness,
  onMinCompletenessChange,
  isLoading = false,
  className,
}) => {
  const { t, language } = useLanguage();
  const [searchTerm, setSearchTerm] = useState("");
  const [globalExpand, setGlobalExpand] = useState<boolean | null>(true);

  const filterCategories = useCallback(
    (cats: Category[], term: string): Category[] => {
      const filter = (categoriesToFilter: Category[]): Category[] => {
        return categoriesToFilter.reduce<Category[]>((acc, cat) => {
          const name = language === "en" && cat.nameEn ? cat.nameEn : cat.name;
          const matches = name.toLowerCase().includes(term.toLowerCase());
          let filteredChildren: Category[] = [];

          if (cat.children) {
            filteredChildren = filter(cat.children);
          }

          if (matches || filteredChildren.length > 0) {
            acc.push({ ...cat, children: filteredChildren });
          }
          return acc;
        }, []);
      };
      return filter(cats);
    },
    [language],
  );

  const displayedCategories = useMemo(() => {
    if (!searchTerm.trim()) return categories;
    return filterCategories(categories, searchTerm);
  }, [categories, searchTerm, filterCategories]);

  const hasSelection = selectedCategoryIds.size > 0;

  // Determine expansion state: Search active forces expand, otherwise manual or global toggle
  const effectiveExpandState = searchTerm ? true : globalExpand;

  return (
    <div
      className={`flex flex-col h-full bg-slate-50/50 dark:bg-slate-950/50 border-r border-slate-200/50 dark:border-slate-800/50 backdrop-blur-3xl relative ${className}`}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/30 to-transparent dark:from-white/5 dark:to-transparent pointer-events-none" />
      <div className="p-3 pb-2 shrink-0 space-y-2.5 bg-white/50 dark:bg-slate-900/50 border-b border-slate-200/50 dark:border-slate-800/50 backdrop-blur-md sticky top-0 z-10">
        {/* Header & Controls */}
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-black text-slate-800 dark:text-white uppercase tracking-widest flex items-center gap-2">
            <Layers size={14} className="text-primary-500" />
            {t("categories")}
          </h2>
          <div className="flex items-center gap-1">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setGlobalExpand(true)}
              className="p-1.5 text-slate-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
              title={t("expandAll")}
            >
              <ChevronsDown size={14} />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setGlobalExpand(false)}
              className="p-1.5 text-slate-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
              title={t("collapseAll")}
            >
              <ChevronsUp size={14} />
            </motion.button>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative group">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary-500 transition-colors z-10"
            size={16}
          />
          <div className="absolute inset-0 bg-primary-500/10 rounded-lg blur opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 pointer-events-none" />
          <input
            type="text"
            placeholder={t("searchCategories")}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-8 py-2.5 bg-white/60 dark:bg-slate-900/60 backdrop-blur border border-slate-200/80 dark:border-slate-800/80 rounded-xl text-[13px] font-medium text-slate-800 dark:text-white focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all placeholder:text-slate-400 shadow-sm relative z-0"
          />
          <AnimatePresence>
            {searchTerm && (
              <motion.button
                key="clear-search-btn"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                whileHover={{
                  scale: 1.1,
                  backgroundColor: "rgba(244, 63, 94, 0.1)",
                }}
                whileTap={{ scale: 0.9, rotate: 90 }}
                onClick={() => setSearchTerm("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 p-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg transition-colors z-10"
              >
                <X size={14} />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* All Products Root Node (Reset Button) */}
        <motion.div
          whileHover={{
            scale: 1.02,
            y: -2,
            boxShadow: "0 4px 12px rgba(14,165,233,0.1)",
          }}
          whileTap={{ scale: 0.98, y: 0 }}
          className={`
              flex items-center justify-between px-4 py-3 rounded-xl cursor-pointer transition-all duration-300 border group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50
              ${
                !hasSelection
                  ? "bg-gradient-to-br from-primary-600 via-primary-500 to-indigo-600 text-white shadow-md shadow-primary-500/20 border-transparent"
                  : "bg-white dark:bg-slate-800 border-slate-200/80 dark:border-slate-800/80 text-slate-700 dark:text-slate-300 hover:border-primary-300 hover:bg-primary-50/50 dark:hover:bg-slate-700/50 shadow-sm"
              }
            `}
          onClick={onClearCategories}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onClearCategories();
            }
          }}
        >
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div
              className={`p-1.5 rounded-lg shrink-0 transition-colors ${!hasSelection ? "bg-white/20" : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/30 group-hover:text-primary-600"}`}
            >
              <Layers size={16} />
            </div>
            <span
              className="font-mono font-bold text-[13px] tracking-tight uppercase truncate"
              title={t("allProducts")}
            >
              {t("allProducts")}
            </span>
          </div>
          <motion.span
            initial={false}
            animate={{ scale: !hasSelection ? 1.05 : 1 }}
            className={`px-2 py-0.5 rounded-lg text-[10px] font-mono shrink-0 transition-colors ${!hasSelection ? "bg-white/20 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400"}`}
          >
            {totalCount}
          </motion.span>
        </motion.div>

        {/* Data Quality Filter */}
        <div className="p-4 bg-white dark:bg-slate-800/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl space-y-4 shadow-sm backdrop-blur-sm">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-primary-50 dark:bg-primary-900/30 rounded-md">
                <Sparkles
                  size={14}
                  className="text-primary-600 dark:text-primary-400"
                />
              </div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400">
                Data Quality
              </span>
            </div>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-md shadow-sm ${minCompleteness > 80 ? "bg-emerald-500 text-white" : minCompleteness > 50 ? "bg-amber-500 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700"}`}
            >
              {minCompleteness > 0 ? `${minCompleteness}%+` : "All"}
            </span>
          </div>
          <div className="relative h-2 flex items-center group/slider">
            <div className="absolute inset-0 bg-slate-100 dark:bg-slate-800 rounded-full transition-colors group-hover/slider:bg-slate-200 dark:group-hover/slider:bg-slate-700" />
            <motion.div
              initial={false}
              animate={{ width: `${minCompleteness}%` }}
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-400 to-primary-600 rounded-full shadow-[0_0_12px_rgba(14,165,233,0.4)] group-hover/slider:shadow-[0_0_15px_rgba(14,165,233,0.6)] transition-shadow"
            />
            <input
              type="range"
              min="0"
              max="90"
              step="10"
              value={minCompleteness}
              onChange={(e) =>
                onMinCompletenessChange(parseInt(e.target.value))
              }
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            />
            <motion.div
              initial={false}
              animate={{ left: `calc(${minCompleteness}% - 10px)` }}
              whileHover={{ scale: 1.2 }}
              whileTap={{ scale: 0.9 }}
              className="absolute w-5 h-5 bg-white border-2 border-primary-500 rounded-full shadow-xl pointer-events-none transition-all duration-200 z-0"
            />
          </div>
          <div className="flex justify-between text-[9px] font-black text-slate-400 uppercase tracking-[0.3em] px-1">
            <span>Any</span>
            <span>50%</span>
            <span>90%</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 custom-scrollbar pb-6 pt-3">
        {isLoading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-6 bg-slate-200 dark:bg-slate-800 rounded animate-pulse" style={{ opacity: 1 - i * 0.15 }} />
            ))}
          </div>
        ) : displayedCategories.length > 0 ? (
          <div className="space-y-1">
            {displayedCategories.map((cat, idx) => (
              <TreeNode
                key={cat.id}
                category={cat}
                selectedIds={selectedCategoryIds}
                onToggle={onToggleCategory}
                depth={0}
                forceExpand={effectiveExpandState}
                counts={counts}
                isLast={idx === displayedCategories.length - 1}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center py-12 text-center px-4"
          >
            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mb-4 border border-slate-200 dark:border-slate-700 shadow-inner">
              <Search
                size={24}
                className="text-slate-300 dark:text-slate-600"
              />
            </div>
            <p className="text-sm font-bold text-slate-600 dark:text-slate-300 mb-1">
              {language === "en" ? "No categories found" : "未找到分类"}
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {language === "en" ? "Try searching with other keywords" : "尝试使用其他关键词搜索"}
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
};
