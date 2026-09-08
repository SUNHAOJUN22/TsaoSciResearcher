import React from "react";
import { Search } from "lucide-react";
import { motion } from "motion/react";
import { useLanguage } from "@/contexts/LanguageContext";

interface SearchControlProps {
  onOpenCommandPalette: () => void;
}

export const SearchControl: React.FC<SearchControlProps> = ({
  onOpenCommandPalette,
}) => {
  const { t } = useLanguage();

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onOpenCommandPalette}
      className="h-10 flex items-center gap-3 px-3 md:px-4 bg-white/60 dark:bg-slate-900/40 backdrop-blur-3xl border border-slate-200/50 dark:border-slate-800/50 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-all group min-w-0 md:min-w-[160px] shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg shadow-sm flex"
    >
      <Search
        size={14}
        className="shrink-0 group-hover:text-primary-500 transition-colors"
      />
      <span className="hidden lg:inline text-[10px] font-mono tracking-widest uppercase whitespace-nowrap">
        {t("searchFunction")}
      </span>
      <div className="flex items-center gap-1.5 ml-auto shrink-0 hidden xl:flex">
        <span className="px-1.5 py-0.5 bg-white/80 dark:bg-slate-800/80 border border-slate-200/50 dark:border-slate-700/50 text-[9px] font-mono rounded text-slate-400 backdrop-blur-sm shadow-sm opacity-80 group-hover:opacity-100 transition-opacity">
          ⌘
        </span>
        <span className="px-1.5 py-0.5 bg-white/80 dark:bg-slate-800/80 border border-slate-200/50 dark:border-slate-700/50 text-[9px] font-mono rounded text-slate-400 backdrop-blur-sm shadow-sm opacity-80 group-hover:opacity-100 transition-opacity">
          F
        </span>
      </div>
    </motion.button>
  );
};
