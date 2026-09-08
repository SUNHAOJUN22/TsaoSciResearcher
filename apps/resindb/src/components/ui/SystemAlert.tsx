import React from "react";
import { motion } from "motion/react";
import { AlertTriangle } from "lucide-react";

interface SystemAlertProps {
  systemStatus: "online" | "syncing" | "error";
  setSystemStatus: (val: "online" | "syncing" | "error") => void;
  t: (key: string, fallback?: string) => string;
}

export const SystemAlert: React.FC<SystemAlertProps> = React.memo(
  ({ systemStatus, setSystemStatus, t }) => {
    if (systemStatus !== "error") return null;

    return (
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="bg-rose-500/10 border border-rose-500/20 rounded-[2rem] p-5 flex items-center gap-4 text-rose-600 dark:text-rose-400 shrink-0"
      >
        <div className="p-3 bg-rose-500 rounded-2xl text-white shadow-lg shadow-rose-500/20">
          <AlertTriangle size={20} />
        </div>
        <div className="flex-1">
          <p className="text-xs font-black uppercase tracking-widest mb-0.5">
            {t("systemAlert")}
          </p>
          <p className="text-sm font-bold opacity-90">{t("systemAlertMsg")}</p>
        </div>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => setSystemStatus("online")}
          className="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
        >
          {t("ignore")}
        </motion.button>
      </motion.div>
    );
  },
);
