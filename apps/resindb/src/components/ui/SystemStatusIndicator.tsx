import React from "react";
import { RefreshCw } from "lucide-react";
import { motion } from "motion/react";

interface SystemStatusIndicatorProps {
  systemStatus: "online" | "syncing" | "error";
  lastSyncTime: string;
  onOpenSystemHealth: () => void;
}

export const SystemStatusIndicator: React.FC<SystemStatusIndicatorProps> = ({
  systemStatus,
  lastSyncTime,
  onOpenSystemHealth,
}) => {
  return (
    <motion.div
      whileHover={{
        scale: 1.05,
        backgroundColor: "rgba(255, 255, 255, 1)",
        boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
      }}
      whileTap={{ scale: 0.98 }}
      className="flex items-center gap-2 px-3 py-1.5 bg-white/50 dark:bg-slate-900/50 backdrop-blur-md border border-slate-200/50 dark:border-slate-800/50 cursor-pointer transition-all group rounded-lg shadow-sm"
      onClick={onOpenSystemHealth}
    >
      <div className="relative flex items-center justify-center">
        <div
          className={`w-2 h-2 rounded-full shrink-0 ${systemStatus === "online" ? "bg-emerald-500" : systemStatus === "syncing" ? "bg-amber-500" : "bg-rose-500"}`}
        ></div>
        <div
          className={`absolute w-3 h-3 rounded-full animate-ping opacity-40 ${systemStatus === "online" ? "bg-emerald-500" : systemStatus === "syncing" ? "bg-amber-500" : "bg-rose-500"}`}
        ></div>
      </div>
      <div className="w-px h-3 bg-slate-200 dark:bg-slate-700 mx-1"></div>
      <span
        className="text-[9px] font-mono text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-colors"
        title={`Last Sync: ${lastSyncTime}`}
      >
        v3.2.0
      </span>
      <motion.button
        whileHover={{ scale: 1.1, rotate: 180 }}
        whileTap={{ scale: 0.9 }}
        className="ml-1 p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-400 hover:text-slate-600 transition-colors"
        title="Check for updates"
      >
        <RefreshCw size={10} />
      </motion.button>
    </motion.div>
  );
};
