import React, { useRef, useState, useEffect } from "react";
import { Plus, ChevronDown, Upload, Download, Loader2, Shield } from "lucide-react";
import { motion, AnimatePresence, Variants } from "motion/react";
import { useLanguage } from "@/contexts/LanguageContext";

interface QuickActionMenuProps {
  onOpenImport: () => void;
  onOpenSmartExport: () => void;
  isExporting: boolean;
  onOpenAdmin: () => void;
  onOpenQualityAudit: () => void;
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

export const QuickActionMenu: React.FC<QuickActionMenuProps> = ({
  onOpenImport,
  onOpenSmartExport,
  isExporting,
  onOpenAdmin,
  onOpenQualityAudit,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { t, language } = useLanguage();

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
        className={`h-10 px-3 md:px-4 flex items-center gap-2 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 shrink-0 rounded-lg shadow-sm border border-transparent ${isOpen ? "bg-primary-600 text-white" : "bg-slate-800 dark:bg-primary-600 text-white hover:bg-slate-700 dark:hover:bg-primary-500"}`}
      >
        <Plus size={14} className="shrink-0" />
        <span
          className="text-[10px] font-mono tracking-widest uppercase hidden xl:inline whitespace-nowrap truncate max-w-[80px]"
          title={t("quickActions")}
        >
          {t("quickActions")}
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
            className="absolute top-full mt-2 right-0 z-[100] w-56 bg-white dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800/80 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-lg p-1.5"
          >
            <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-800 mb-1 bg-slate-50 dark:bg-slate-900">
              <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                {t("commonFunctions")}
              </h4>
            </div>
            <motion.button
              whileHover={{ backgroundColor: "rgba(79, 70, 229, 0.1)" }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setIsOpen(false);
                onOpenImport();
              }}
              className="w-full px-3 py-2 text-left text-xs font-mono text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 group border border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-lg"
            >
              <Upload size={12} className="text-blue-500" />
              {t("importData")}
            </motion.button>
            <motion.button
              whileHover={{ backgroundColor: "rgba(79, 70, 229, 0.1)" }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                if (!isExporting) {
                  setIsOpen(false);
                  onOpenSmartExport();
                }
              }}
              disabled={isExporting}
              className={`w-full px-3 py-2 text-left text-xs font-mono text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 group border border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-lg ${isExporting ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              {isExporting ? (
                <Loader2 size={12} className="text-emerald-500 animate-spin" />
              ) : (
                <Download size={12} className="text-emerald-500" />
              )}
              {isExporting ? t("exporting", "Exporting...") : language === 'zh' ? "智能导出数据" : "Smart Export"}
            </motion.button>
            <div className="my-1 border-t border-slate-200 dark:border-slate-800" />
            <motion.button
              whileHover={{ backgroundColor: "rgba(79, 70, 229, 0.1)" }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setIsOpen(false);
                onOpenQualityAudit();
              }}
              className="w-full px-3 py-2 text-left text-xs font-mono text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 group border border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-lg"
            >
              <Shield size={12} className="text-teal-500" />
              {t("dataQualityAudit", "Data Quality Audit")}
            </motion.button>
            <motion.button
              whileHover={{ backgroundColor: "rgba(79, 70, 229, 0.1)" }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setIsOpen(false);
                onOpenAdmin();
              }}
              className="w-full px-3 py-2 mt-1 text-left text-xs font-mono text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 group border border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-lg"
            >
              <Shield size={12} className="text-amber-500" />
              {t("systemSettings")}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
