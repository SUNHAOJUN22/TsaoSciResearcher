import React, { useRef, useState, useEffect, useMemo } from "react";
import {
  SlidersHorizontal,
  ChevronDown,
  Check,
  Square,
  CheckSquare,
} from "lucide-react";
import { motion, AnimatePresence, Variants } from "motion/react";
import { ColumnConfig } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";

interface ColumnVisibilityMenuProps {
  columns: ColumnConfig[];
  onToggleColumn: (key: string) => void;
  onToggleAllColumns: (visible: boolean) => void;
}

const popoverVariants: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 400, damping: 25 },
  },
  exit: {
    opacity: 0,
    y: -4,
    scale: 0.98,
    transition: { duration: 0.12, ease: "easeIn" },
  },
};

export const ColumnVisibilityMenu: React.FC<ColumnVisibilityMenuProps> = ({
  columns,
  onToggleColumn,
  onToggleAllColumns,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { t, tProp } = useLanguage();

  const areAllDynamicVisible = useMemo(() => {
    const dynamicCols = columns.filter((c) => !c.isSystem);
    return dynamicCols.length > 0 && dynamicCols.every((c) => c.visible);
  }, [columns]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative shrink-0" ref={containerRef}>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className={`h-10 px-3 md:px-4 flex items-center gap-2 border transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 shrink-0 rounded-lg shadow-sm ${isOpen ? "bg-primary-50 border-primary-200/80 text-primary-600 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-400" : "bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800/80 text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-700"}`}
      >
        <SlidersHorizontal size={14} className="shrink-0" />
        <span
          className="text-[10px] font-mono uppercase tracking-widest whitespace-nowrap truncate max-w-[100px] hidden xl:inline"
          title={t("configureColumns")}
        >
          {t("configureColumns")}
        </span>
        <ChevronDown
          size={14}
          className={`transition-transform duration-300 shrink-0 ${isOpen ? "rotate-180" : ""}`}
        />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            variants={popoverVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800/80 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-lg overflow-hidden z-[200]"
          >
            <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 flex items-center justify-between">
              <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                {t("configureColumns")}
              </h4>
              <motion.button
                whileHover={{
                  scale: 1.05,
                  backgroundColor: "rgba(79, 70, 229, 0.9)",
                }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onToggleAllColumns(!areAllDynamicVisible)}
                className="flex items-center gap-1.5 px-2 py-1 border border-primary-600 bg-primary-600 text-white text-[9px] font-mono uppercase tracking-widest hover:bg-primary-500 transition-colors rounded-md shadow-sm"
              >
                {areAllDynamicVisible ? (
                  <Square size={10} />
                ) : (
                  <CheckSquare size={10} />
                )}
                {areAllDynamicVisible ? t("deselectAll") : t("selectAll")}
              </motion.button>
            </div>
            <div className="max-h-80 overflow-y-auto custom-scrollbar p-2">
              <motion.button
                whileHover={{
                  scale: 1.02,
                  backgroundColor: "rgba(241, 245, 249, 0.5)",
                  x: 4,
                }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onToggleAllColumns(!areAllDynamicVisible)}
                className="w-full flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-900 mb-1 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 border border-slate-200 dark:border-slate-800 rounded-lg"
              >
                <span className="text-[10px] font-mono text-primary-600 dark:text-primary-400 uppercase tracking-widest">
                  {areAllDynamicVisible ? t("deselectAll") : t("selectAll")}
                </span>
                <div
                  className={`w-4 h-4 border flex items-center justify-center transition-colors ${areAllDynamicVisible ? "bg-primary-600 border-primary-600 text-white" : "border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-950"} rounded shadow-inner`}
                >
                  {areAllDynamicVisible && <Check size={10} strokeWidth={3} />}
                </div>
              </motion.button>

              <div className="h-px bg-slate-200 dark:bg-slate-800 my-2 mx-1"></div>

              {columns.map((col) => (
                <motion.button
                  key={col.key}
                  whileHover={{
                    backgroundColor: "rgba(79, 70, 229, 0.05)",
                    x: 2,
                  }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onToggleColumn(col.key)}
                  className="w-full flex items-center justify-between p-2 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 border border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-lg gap-2"
                >
                  <span
                    className={`text-xs font-mono truncate ${col.visible ? "text-slate-800 dark:text-slate-200" : "text-slate-400"}`}
                  >
                    {tProp(col.label)}
                  </span>
                  <div
                    className={`w-4 h-4 border flex items-center justify-center transition-colors shrink-0 rounded ${col.visible ? "bg-primary-600 border-primary-600 text-white shadow-lg shadow-primary-500/20" : "border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-950"}`}
                  >
                    {col.visible && <Check size={10} />}
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
