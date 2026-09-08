import React from "react";
import { AlertTriangle, X } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence } from "motion/react";

interface DeleteConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  productNames: string[];
}

export const DeleteConfirmationModal: React.FC<
  DeleteConfirmationModalProps
> = ({ isOpen, onClose, onConfirm, productNames }) => {
  const { t } = useLanguage();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="delete-modal-root"
          className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
          ></motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative w-full max-w-md bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden rounded-[2.5rem] shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-rose-100 dark:border-rose-900/30 bg-rose-50/50 dark:bg-rose-950/20">
              <div className="flex items-center gap-3 text-rose-600 dark:text-rose-500">
                <div className="p-1.5 bg-rose-100 dark:bg-rose-900/40 border border-rose-200 dark:border-rose-800 rounded-xl shadow-sm">
                  <AlertTriangle size={18} />
                </div>
                <h3 className="text-sm font-serif tracking-tight">
                  {t("confirmDelete")}
                </h3>
              </div>
              <motion.button
                whileHover={{
                  scale: 1.1,
                  backgroundColor: "rgba(225, 29, 72, 1)",
                  color: "#fff",
                }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 shadow-sm rounded-xl transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 z-10"
              >
                <X size={16} />
              </motion.button>
            </div>

            {/* Content */}
            <div className="p-8 bg-white dark:bg-slate-950">
              <p className="text-[11px] font-mono text-slate-600 dark:text-slate-400 mb-4 leading-relaxed">
                {t("deleteConfirmMsg")}
              </p>

              <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-inner max-h-48 overflow-y-auto custom-scrollbar p-5">
                <ul className="space-y-3">
                  {productNames.map((name, index) => (
                    <li
                      key={index}
                      className="text-[10px] font-mono text-slate-700 dark:text-slate-300 flex items-center gap-3"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(225,29,72,0.4)]"></span>
                      {name}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 px-6 py-5 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
              <motion.button
                whileHover={{
                  scale: 1.05,
                  backgroundColor: "rgba(226, 232, 240, 0.5)",
                }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="px-5 py-2.5 text-[10px] font-mono uppercase tracking-widest text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors border border-transparent rounded-xl"
              >
                {t("cancel")}
              </motion.button>
              <motion.button
                whileHover={{
                  scale: 1.05,
                  backgroundColor: "#e11d48",
                  boxShadow:
                    "0 20px 25px -5px rgba(225, 29, 72, 0.4), 0 10px 10px -5px rgba(225, 29, 72, 0.1)",
                }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  onConfirm();
                  onClose();
                }}
                className="px-8 py-3 text-[10px] font-mono font-bold uppercase tracking-widest text-white bg-rose-600 border border-rose-500 transition-all rounded-[1.5rem] shadow-lg shadow-rose-500/20"
              >
                {t("delete")}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
