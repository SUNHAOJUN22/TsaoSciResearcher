import React from "react";
import { motion } from "motion/react";
import { LayoutDashboard, PieChart, ShieldCheck, TableProperties, Network } from "lucide-react";
import { AppView } from '@/types/index';

export const MobileBottomNav: React.FC<{
  activeView: AppView;
  setActiveView: (view: AppView) => void;
  onOpenAdmin: () => void;
  t: (key: string, fallback?: string) => string;
}> = ({ activeView, setActiveView, onOpenAdmin, t }) => {
  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-[100] bg-white/90 dark:bg-slate-950/90 backdrop-blur-xl border-t border-slate-200/50 dark:border-slate-800/50 px-6 pb-[calc(env(safe-area-inset-bottom)+0.5rem)] pt-3 flex items-center justify-between shadow-[0_-8px_30px_rgb(0,0,0,0.12)]">
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => setActiveView("dashboard")}
        className={`flex flex-col items-center gap-1 transition-colors ${activeView === "dashboard" ? "text-primary-600 dark:text-primary-400" : "text-slate-400 dark:text-slate-500"}`}
      >
        <LayoutDashboard
          size={20}
          strokeWidth={activeView === "dashboard" ? 2.5 : 2}
        />
        <span className="text-[9px] font-black uppercase tracking-widest leading-none">
          {t("dataWarehouse")}
        </span>
      </motion.button>
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => setActiveView("analytics")}
        className={`flex flex-col items-center gap-1 transition-colors ${activeView === "analytics" ? "text-primary-600 dark:text-primary-400" : "text-slate-400 dark:text-slate-500"}`}
      >
        <PieChart
          size={20}
          strokeWidth={activeView === "analytics" ? 2.5 : 2}
        />
        <span className="text-[9px] font-black uppercase tracking-widest leading-none">
          {t("scientificVisualization")}
        </span>
      </motion.button>
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => setActiveView("pivot")}
        className={`flex flex-col items-center gap-1 transition-colors ${activeView === "pivot" ? "text-primary-600 dark:text-primary-400" : "text-slate-400 dark:text-slate-500"}`}
      >
        <TableProperties
          size={20}
          strokeWidth={activeView === "pivot" ? 2.5 : 2}
        />
        <span className="text-[9px] font-black uppercase tracking-widest leading-none">
          Pivot
        </span>
      </motion.button>
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => setActiveView("dependencies")}
        className={`flex flex-col items-center gap-1 transition-colors ${activeView === "dependencies" ? "text-primary-600 dark:text-primary-400" : "text-slate-400 dark:text-slate-500"}`}
      >
        <Network
          size={20}
          strokeWidth={activeView === "dependencies" ? 2.5 : 2}
        />
        <span className="text-[9px] font-black uppercase tracking-widest leading-none">
          Map
        </span>
      </motion.button>
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={onOpenAdmin}
        className="flex flex-col items-center gap-1 text-slate-400 dark:text-slate-500 hover:text-indigo-500 transition-colors"
      >
        <ShieldCheck size={20} strokeWidth={2} />
        <span className="text-[9px] font-black uppercase tracking-widest leading-none">
          {t("adminPanel")}
        </span>
      </motion.button>
    </div>
  );
};
