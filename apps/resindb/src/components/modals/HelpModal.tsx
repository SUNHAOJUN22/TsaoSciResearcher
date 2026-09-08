import React from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, HelpCircle } from "lucide-react";

import { useLanguage } from "@/contexts/LanguageContext";

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface HelpItem {
  title: string;
  description: string;
}

const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const { language } = useLanguage();
  const isChinese = language === "zh";

  React.useEffect(() => {
    if (!isOpen) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const gettingStarted: HelpItem[] = isChinese
    ? [
        { title: "如何导入数据？", description: "支持 CSV、JSON、TXT 格式" },
        { title: "搜索与筛选", description: "组合属性过滤和关键词检索" },
        { title: "批量编辑", description: "一次更新选中的多条记录" },
      ]
    : [
        { title: "How do I import data?", description: "CSV, JSON and TXT are supported" },
        { title: "Search and filtering", description: "Combine property filters with keyword search" },
        { title: "Batch editing", description: "Update selected records in one operation" },
      ];

  const advancedFeatures: HelpItem[] = isChinese
    ? [
        { title: "多牌号比较", description: "雷达图、散点图和平行坐标分析" },
        { title: "便携导出", description: "支持 CSV、JSON、XML、PDF" },
        { title: "演示角色边界", description: "Admin、Editor、Viewer 仅用于界面演示" },
      ]
    : [
        { title: "Multi-grade comparison", description: "Radar, scatter and parallel-coordinate views" },
        { title: "Portable exports", description: "CSV, JSON, XML and PDF are supported" },
        { title: "Demo role boundaries", description: "Admin, Editor and Viewer demonstrate UI behavior only" },
      ];

  const title = isChinese ? "帮助中心" : "Help center";
  const subtitle = isChinese ? "已核验能力与使用边界" : "Verified capabilities and boundaries";
  const closeLabel = isChinese ? "关闭帮助中心" : "Close help center";

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="help-modal-root"
          className="fixed inset-0 z-[200] flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative bg-white dark:bg-slate-950 w-full max-w-2xl border border-slate-300 dark:border-slate-700 overflow-hidden flex flex-col rounded-[2.5rem] shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="help-modal-title"
            aria-describedby="help-modal-description"
          >
            <div className="px-6 py-5 border-b border-slate-300 dark:border-slate-700 flex items-center justify-between bg-slate-100/50 dark:bg-slate-900/50 backdrop-blur-md shrink-0">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                  <HelpCircle size={20} aria-hidden="true" />
                </div>
                <div>
                  <h3 id="help-modal-title" className="text-sm font-serif text-slate-800 dark:text-white tracking-tight">
                    {title}
                  </h3>
                  <p id="help-modal-description" className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    {subtitle}
                  </p>
                </div>
              </div>
              <motion.button
                type="button"
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                aria-label={closeLabel}
                className="p-2 bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400 transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 z-10 rounded-xl"
              >
                <X size={16} aria-hidden="true" />
              </motion.button>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 max-h-[60vh] overflow-y-auto custom-scrollbar bg-white dark:bg-slate-950">
              <div className="space-y-4">
                <h4 className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest ml-1">
                  {isChinese ? "快速入门" : "Getting started"}
                </h4>
                {gettingStarted.map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    whileHover={{ scale: 1.02, x: 8, borderColor: "rgba(79, 70, 229, 0.4)" }}
                    className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-all group rounded-2xl shadow-sm hover:shadow-md"
                  >
                    <p className="text-xs font-mono font-bold text-slate-800 dark:text-white group-hover:text-primary-600 transition-colors uppercase tracking-tight">
                      {item.title}
                    </p>
                    <p className="text-[10px] font-mono text-slate-500 mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </motion.div>
                ))}
              </div>
              <div className="space-y-4">
                <h4 className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest ml-1">
                  {isChinese ? "进阶功能" : "Advanced features"}
                </h4>
                {advancedFeatures.map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.15 + index * 0.05 }}
                    whileHover={{ scale: 1.02, x: 8, borderColor: "rgba(79, 70, 229, 0.4)" }}
                    className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-all group rounded-2xl shadow-sm hover:shadow-md"
                  >
                    <p className="text-xs font-mono font-bold text-slate-800 dark:text-white group-hover:text-primary-600 transition-colors uppercase tracking-tight">
                      {item.title}
                    </p>
                    <p className="text-[10px] font-mono text-slate-500 mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </div>
            <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-300 dark:border-slate-700 flex items-center justify-between gap-4">
              <p className="text-[9px] font-mono text-slate-400 uppercase tracking-widest font-bold">
                {isChinese ? "完整能力和安全边界请查看 README.md" : "See README.md for complete capabilities and security boundaries"}
              </p>
              <motion.button
                type="button"
                whileHover={{ scale: 1.05, backgroundColor: "#000" }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="px-8 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-mono font-bold text-[10px] uppercase tracking-widest transition-all rounded-xl shadow-lg"
              >
                {isChinese ? "关闭" : "Close"}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default HelpModal;
