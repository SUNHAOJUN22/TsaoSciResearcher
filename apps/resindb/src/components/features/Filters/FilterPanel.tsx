import React from "react";
import { X, Filter } from "lucide-react";
import { ColumnConfig, FilterGroup } from '@/types/index';
import { motion, AnimatePresence } from "motion/react";
import { FilterBuilder } from '@/components/features/Filters/FilterBuilder';
import { useLanguage } from "@/contexts/LanguageContext";

interface FilterPanelProps {
  isOpen: boolean;
  onClose: () => void;
  columns: ColumnConfig[];
  filterGroup: FilterGroup;
  onFilterChange: (group: FilterGroup) => void;
  onClearFilters: () => void;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  isOpen,
  onClose,
  columns,
  filterGroup,
  onFilterChange,
  onClearFilters,
}) => {
  const { t } = useLanguage();
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="filter-panel-content"
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 35 }}
          className="fixed inset-y-0 right-0 h-full bg-white/90 dark:bg-slate-950/90 backdrop-blur-3xl border-l border-slate-200/50 dark:border-white/10 rounded-l-3xl shadow-[-20px_0_60px_-10px_rgba(0,0,0,0.3)] flex flex-col shrink-0 overflow-hidden z-[150] w-full sm:w-[480px]"
        >
          <div className="p-5 border-b border-slate-200/50 dark:border-slate-800/50 flex items-center justify-between shrink-0 bg-white/50 dark:bg-slate-900/50 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="p-2 border border-primary-200/80 dark:border-primary-800/50 bg-primary-50 dark:bg-primary-900/40 text-primary-600 dark:text-primary-400 rounded-xl shadow-sm">
                <Filter size={16} strokeWidth={2.5} />
              </div>
              <h3 className="text-xs font-black text-slate-800 dark:text-white tracking-[0.2em] uppercase">
                {t("advancedFilters")}
              </h3>
            </div>
            <motion.button
              whileHover={{
                scale: 1.1,
                backgroundColor: "rgba(241, 245, 249, 1)",
              }}
              whileTap={{ scale: 0.9 }}
              onClick={onClose}
              className="p-2 border border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-all rounded-xl focus:outline-none"
            >
              <X size={16} />
            </motion.button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                  {t("conditionCombination")}
                </h4>
                {filterGroup.conditions.length > 0 && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onClearFilters}
                    className="text-[10px] font-bold text-rose-500 hover:text-rose-600 transition-colors uppercase tracking-widest bg-rose-50 dark:bg-rose-900/20 px-2 py-1 rounded-lg border border-transparent hover:border-rose-200 dark:hover:border-rose-800/50 shadow-sm"
                  >
                    {t("clearAll")}
                  </motion.button>
                )}
              </div>

              <FilterBuilder
                filterGroup={filterGroup}
                onChange={onFilterChange}
                columns={columns}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
