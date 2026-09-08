import React, { useRef, useState, useEffect } from "react";
import { Bookmark, Star, ArrowRight, Trash, Plus } from "lucide-react";
import { motion, AnimatePresence, Variants } from "motion/react";
import { SavedView } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";

interface SavedViewsMenuProps {
  savedViews: SavedView[];
  onSaveView: (name: string) => void;
  onApplyView: (view: SavedView) => void;
  onDeleteView: (id: string) => void;
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

export const SavedViewsMenu: React.FC<SavedViewsMenuProps> = ({
  savedViews,
  onSaveView,
  onApplyView,
  onDeleteView,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [newViewName, setNewViewName] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const { t } = useLanguage();

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
        className={`h-10 px-3 md:px-4 flex items-center gap-2 border transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg shadow-sm ${isOpen ? "bg-primary-50 border-primary-200/80 text-primary-600 dark:bg-primary-900/30 dark:border-primary-700 dark:text-primary-400" : "bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800/80 text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-700"}`}
      >
        <Bookmark size={14} className="shrink-0" />
        <span
          className="hidden xl:inline text-[10px] font-mono tracking-widest uppercase whitespace-nowrap truncate max-w-[80px]"
          title={t("views")}
        >
          {t("views")}
        </span>
        {savedViews.length > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="px-1.5 py-0.5 bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 text-[9px] font-black rounded-lg shrink-0"
          >
            {savedViews.length}
          </motion.span>
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            variants={popoverVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute right-0 top-full mt-3 w-80 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-2xl rounded-3xl overflow-hidden z-[200]"
          >
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
              <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-3">
                {t("saveCurrentView")}
              </h4>
              <div className="flex gap-2">
                <motion.input
                  whileFocus={{
                    scale: 1.01,
                    boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                  }}
                  type="text"
                  placeholder={t("viewNamePlaceholder")}
                  className="flex-1 bg-white dark:bg-slate-950 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 text-xs font-mono outline-none focus:border-primary-500 shadow-sm transition-all hover:border-slate-300 dark:hover:border-slate-600"
                  value={newViewName}
                  onChange={(e) => setNewViewName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newViewName.trim()) {
                      onSaveView(newViewName);
                      setNewViewName("");
                    }
                  }}
                />
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => {
                    if (newViewName.trim()) {
                      onSaveView(newViewName);
                      setNewViewName("");
                    }
                  }}
                  className="px-3 py-1.5 bg-primary-600 text-white hover:bg-primary-500 transition-all border border-primary-600 rounded-xl shadow-sm hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
                >
                  <Plus size={14} />
                </motion.button>
              </div>
            </div>
            <div className="max-h-64 overflow-y-auto custom-scrollbar p-2">
              {savedViews.length === 0 ? (
                <div className="py-6 text-center opacity-50">
                  <Bookmark size={20} className="mx-auto mb-2" />
                  <p className="text-[10px] font-mono uppercase tracking-widest">
                    {t("noSavedViews")}
                  </p>
                </div>
              ) : (
                savedViews.map((view) => (
                  <div key={view.id} className="group flex items-center gap-2 p-1">
                    <motion.button
                      whileHover={{
                        scale: 0.99,
                        x: 2,
                        backgroundColor: "rgba(241, 245, 249, 0.5)",
                      }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => {
                        onApplyView(view);
                        setIsOpen(false);
                      }}
                      className="flex-1 flex items-center justify-between p-2 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left border border-transparent hover:border-slate-200 dark:hover:border-slate-700 rounded-xl"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <Star size={12} className="text-amber-500 shrink-0" />
                        <span className="text-xs font-mono text-slate-700 dark:text-slate-300 truncate">
                          {view.name}
                        </span>
                      </div>
                      <ArrowRight
                        size={10}
                        className="text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity"
                      />
                    </motion.button>
                    <motion.button
                      whileHover={{
                        scale: 1.1,
                        backgroundColor: "rgba(244, 63, 94, 0.1)",
                        color: "#f43f5e",
                      }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => onDeleteView(view.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors opacity-0 group-hover:opacity-100 border border-transparent hover:border-rose-200 dark:hover:border-rose-800 rounded-lg"
                    >
                      <Trash size={12} />
                    </motion.button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
