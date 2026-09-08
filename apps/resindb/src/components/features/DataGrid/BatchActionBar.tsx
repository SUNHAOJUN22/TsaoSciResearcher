import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { GitCompare, Edit, Download, Trash2, X, ShieldCheck, Tag, Sliders, Undo2, ClipboardCheck } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { HistoryRecord } from "@/lib/adapters/types";
import { Product } from "@/types/index";

interface BatchActionBarProps {
  selectedIds: Set<string>;
  setSelectedIds: (ids: Set<string>) => void;
  setIsComparisonOpen: (isOpen: boolean) => void;
  setIsBatchEditOpen: (isOpen: boolean) => void;
  setIsBulkTaggingOpen: (isOpen: boolean) => void;
  setIsBulkReorderOpen: (isOpen: boolean) => void;
  handleExport: () => void;
  onOpenQaReport: () => void;
  handleDelete: (ids: string[]) => void;
  addToast: (
    type: "info" | "success" | "error",
    message: string,
  ) => void;
  history?: Omit<HistoryRecord, 'snapshot'>[];
  restoreSnapshot?: (id: string) => Promise<void>;
  allProducts: Product[];
}

export const BatchActionBar: React.FC<BatchActionBarProps> = ({
  selectedIds,
  setSelectedIds,
  setIsComparisonOpen,
  setIsBatchEditOpen,
  setIsBulkTaggingOpen,
  setIsBulkReorderOpen,
  handleExport,
  onOpenQaReport,
  handleDelete,
  addToast,
  history = [],
  restoreSnapshot,
  allProducts,
}) => {
  const { t, language } = useLanguage();
  const [isValidating, setIsValidating] = useState(false);
  
  // Only allow undo if the most recent user action was a batch action
  const lastBatchAction = history[0] && (
    history[0].description.includes("批量") || 
    history[0].description.toLowerCase().includes("bulk") || 
    history[0].description.toLowerCase().includes("batch")
  ) ? history[0] : undefined;

  const handleUndo = async () => {
    if (lastBatchAction && restoreSnapshot) {
      await restoreSnapshot(lastBatchAction.id);
      addToast("success", language === "zh" ? `已撤销: ${lastBatchAction.description}` : `Undid: ${lastBatchAction.description}`);
    }
  };

  const handleValidateSelection = () => {
    setIsValidating(true);
    setTimeout(() => {
      setIsValidating(false);
      const selected = allProducts.filter(p => selectedIds.has(p.id));
      const categories = new Set(selected.map(p => p.categoryIds[0] || 'Unknown'));
      const errors: string[] = [];

      // Check category mismatch
      if (categories.size > 1) {
        errors.push(language === 'zh' ? "存在跨分类品种（如 PE 和 PP 混选），请注意物理属性不相容风险" : "Mixed categories detect. Watch for incompatible properties.");
      }

      // Check specific property logic, e.g. Melt Flow Rate for PE
      let missingMFR = false;
      let implausibleDensity = false;

      selected.forEach(p => {
        const props = p.properties || {};
        const getProp = (key: string) => {
          const match = Object.keys(props).find(k => k.toLowerCase() === key.toLowerCase() || k.toLowerCase().includes(key.toLowerCase()));
          return match ? props[match].value : undefined;
        };

        const mfr = getProp('melt flow') || getProp('熔体质量流动速率');
        const density = getProp('density') || getProp('密度');
        
        if (p.categoryIds.some(id => id.includes('pe') || id.includes('pp')) && (mfr === undefined || mfr === '')) {
            missingMFR = true;
        }

        if (density !== undefined && Number(density) > 3) {
            implausibleDensity = true;
        }
      });

      if (missingMFR) {
          errors.push(language === 'zh' ? "部分聚烯烃(PE/PP)类产品缺失关键属性「熔指」(Melt Flow Rate)" : "Missing Melt Flow Rate for some PE/PP products.");
      }
      if (implausibleDensity) {
          errors.push(language === 'zh' ? "部分产品「密度」(Density) 异常（超过 3 g/cm³）" : "Implausible specific Density detected (> 3.0).");
      }

      if (errors.length > 0) {
        errors.forEach(e => addToast("error", e));
      } else {
        addToast("success", language === 'zh' ? "选中产品校验通过，属性范围合规" : "Selected products passed compliance validation.");
      }
    }, 400); // simulate async check
  };

  if (selectedIds.size === 0) return null;

  return (
    <motion.div
      initial={{ y: 80, opacity: 0, x: "-50%" }}
      animate={{ y: 0, opacity: 1, x: "-50%" }}
      exit={{ y: 80, opacity: 0, x: "-50%" }}
      transition={{ type: "spring", stiffness: 260, damping: 25 }}
      layout
      className="fixed bottom-6 left-1/2 z-[100] pointer-events-none w-full max-w-fit px-4"
    >
      <div className="pointer-events-auto bg-slate-950/90 dark:bg-white/95 backdrop-blur-3xl px-6 py-4 rounded-[2.5rem] border border-white/10 dark:border-slate-200/50 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.5)] flex items-center justify-center gap-8 ring-1 ring-white/5 dark:ring-slate-950/5">
        <div className="flex items-center gap-4 pr-8 border-r border-white/10 dark:border-slate-200">
          <div className="relative group/count">
            <motion.div
              key={selectedIds.size}
              initial={{ scale: 0.8, rotate: -10 }}
              animate={{ scale: 1, rotate: 0 }}
              whileHover={{ scale: 1.1, rotate: 5 }}
              whileTap={{ scale: 0.95 }}
              className="w-12 h-12 bg-primary-600 dark:bg-primary-500 rounded-2xl flex items-center justify-center text-white font-black text-lg shadow-[0_0_20px_rgba(var(--color-primary-600-rgb),0.4)] transition-transform cursor-pointer"
            >
              {selectedIds.size}
            </motion.div>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-slate-950 dark:border-white animate-pulse" />
          </div>
          <div>
            <p className="text-[10px] font-black text-white dark:text-slate-950 uppercase tracking-[0.2em]">
              {t("selected")}
            </p>
            <p className="text-[9px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-[0.1em] mt-0.5">
              {t("recordsSelected")}
            </p>
          </div>
        </div>

        <motion.div layout className="flex items-center gap-6">
          <AnimatePresence>
            {lastBatchAction && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8, x: -10 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.8, x: -10 }}
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleUndo}
                className="flex flex-col items-center gap-1.5 group focus:outline-none focus:ring-0 mr-2"
              >
                <div className="p-3.5 bg-sky-50 dark:bg-sky-950/30 rounded-[1.25rem] text-sky-600 dark:text-sky-400 group-hover:bg-sky-500 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(14,165,233,0.4)] transition-all border border-sky-100 dark:border-sky-900/50">
                  <Undo2 size={20} strokeWidth={2.5} />
                </div>
                <span className="text-[8px] font-black text-sky-600 dark:text-sky-400 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-1 group-hover:translate-y-0">
                  {language === 'zh' ? '撤销上一步' : 'Undo Last'}
                </span>
              </motion.button>
            )}
          </AnimatePresence>

          {[
            {
              icon: GitCompare,
              label: t("compareAnalysis"),
              color: "emerald",
              onClick: () => {
                if (selectedIds.size < 1) {
                  addToast("info", "请选择至少一个牌号。您可以在比对面板中同屏搜索/追加加载标准大盘对照牌号。");
                  return;
                }
                setIsComparisonOpen(true);
              },
            },
            {
              icon: ClipboardCheck,
              label: language === "zh" ? "合规校验" : "Validate",
              color: "sky",
              onClick: handleValidateSelection,
            },
            {
              icon: Edit,
              label: t("batchEdit"),
              color: "amber",
              onClick: () => setIsBatchEditOpen(true),
            },
            {
              icon: Tag,
              label: language === "zh" ? "批量标签" : "Bulk Tags",
              color: "violet",
              onClick: () => setIsBulkTaggingOpen(true),
            },
            {
              icon: Sliders,
              label: language === "zh" ? "自定义重排" : "Reorder Priority",
              color: "fuchsia",
              onClick: () => setIsBulkReorderOpen(true),
            },
            {
              icon: ShieldCheck,
              label: language === "zh" ? "PDF安全质检报告" : "PDF QA Report",
              color: "indigo",
              onClick: onOpenQaReport,
            },
            {
              icon: Download,
              label: t("generateReport"),
              color: "primary",
              onClick: handleExport,
            },
            {
              icon: Trash2,
              label: t("delete"),
              color: "rose",
              onClick: () => handleDelete(Array.from(selectedIds)),
            },
          ].map((action, idx) => (
            <motion.button
              key={idx}
              layout
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={action.onClick}
              className="flex flex-col items-center gap-1.5 group focus:outline-none focus:ring-0"
            >
              <div
                className={`p-3.5 bg-white/5 dark:bg-slate-100 rounded-[1.25rem] text-white dark:text-slate-700 transition-all ${
                  action.color === "emerald"
                    ? "group-hover:bg-emerald-500 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(16,185,129,0.4)]"
                    : action.color === "amber"
                      ? "group-hover:bg-amber-500 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(245,158,11,0.4)]"
                      : action.color === "sky"
                        ? "group-hover:bg-sky-500 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(14,165,233,0.4)]"
                        : action.color === "rose"
                          ? "group-hover:bg-rose-600 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(225,29,72,0.4)]"
                        : action.color === "indigo"
                          ? "group-hover:bg-indigo-600 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(79,70,229,0.4)]"
                          : action.color === "violet"
                            ? "group-hover:bg-violet-600 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(139,92,246,0.4)]"
                            : action.color === "fuchsia"
                              ? "group-hover:bg-fuchsia-600 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(217,70,239,0.4)]"
                              : "group-hover:bg-primary-600 group-hover:text-white group-hover:shadow-[0_0_15px_rgba(var(--color-primary-600-rgb),0.4)]"
                }`}
              >
                {action.icon === ClipboardCheck && isValidating ? (
                  <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : (
                  <action.icon size={20} strokeWidth={2.5} />
                )}
              </div>
              <span className="text-[8px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-1 group-hover:translate-y-0">
                {action.label}
              </span>
            </motion.button>
          ))}
        </motion.div>

        <motion.button
          whileHover={{ scale: 1.1, rotate: 90 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setSelectedIds(new Set())}
          className="ml-4 p-2 text-slate-500 hover:text-rose-500 transition-colors rounded-xl hover:bg-white/5 dark:hover:bg-slate-100"
          title="Clear selection"
        >
          <X size={16} strokeWidth={3} />
        </motion.button>
      </div>
    </motion.div>
  );
};
