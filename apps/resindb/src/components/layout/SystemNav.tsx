import React from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Microscope,
  Database,
  LayoutDashboard,
  Zap,
  PieChart,
  ShieldCheck,
  TableProperties,
  Network,
  Cpu
} from "lucide-react";
import { AppView } from '@/types/index';
import { ModalType } from '@/contexts/ModalContext';

export const SystemNav: React.FC<{
  activeView: AppView;
  setActiveView: (view: AppView) => void;
  showAppMenu: boolean;
  setShowAppMenu: (val: boolean) => void;
  showSidebar: boolean;
  setShowSidebar: React.Dispatch<React.SetStateAction<boolean>>;
  systemStatus: "online" | "syncing" | "error";
  openModal: (modal: ModalType) => void;
  t: (key: string, fallback?: string) => string;
}> = ({
  activeView,
  setActiveView,
  showAppMenu,
  setShowAppMenu,
  showSidebar,
  setShowSidebar,
  systemStatus,
  openModal,
  t,
}) => {
  const isSidebarVisibleView = activeView === "dashboard" || activeView === "analytics";

  return (
    <nav className="hidden md:flex w-14 md:w-16 bg-slate-50 dark:bg-slate-950 flex-col items-center py-4 gap-4 z-[70] shrink-0 border-r border-slate-200/80 dark:border-slate-800/80 relative">
      <div className="relative group/logo">
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center shadow-sm shadow-primary-900/20 mb-2 overflow-hidden relative group cursor-pointer ring-1 ring-primary-700/50"
          onClick={() => {
            setActiveView("dashboard");
            setShowAppMenu(!showAppMenu);
          }}
        >
          <Microscope
            size={20}
            className="text-white group-hover:rotate-12 transition-transform"
          />
        </motion.div>
        <div className="absolute left-[calc(100%+0.5rem)] top-1/2 -translate-y-1/2 px-3 py-1.5 bg-slate-800 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-bold rounded shadow-lg opacity-0 invisible group-hover/logo:opacity-100 group-hover/logo:visible transition-all z-50 whitespace-nowrap pointer-events-none tracking-tight">
          {t("materialDataWarehouse")}
        </div>
        <AnimatePresence>
          {showAppMenu && (
            <>
              <div
                key="app-menu-backdrop"
                className="fixed inset-0 z-40"
                onClick={() => setShowAppMenu(false)}
              ></div>
              <motion.div
                key="app-menu-content"
                initial={{ opacity: 0, scale: 0.98, x: -4 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.98, x: -4 }}
                transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
                className="absolute left-[calc(100%+0.75rem)] top-0 w-64 bg-white dark:bg-slate-900 rounded-lg shadow-[0_8px_30px_rgb(0,0,0,0.12)] border border-slate-200/80 dark:border-slate-800/80 overflow-hidden z-50 flex flex-col"
              >
                <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-800/10">
                  <h2 className="text-[13px] font-semibold tracking-tight text-slate-800 dark:text-slate-100 flex items-center gap-2">
                    <Database size={14} className="text-primary-500" />
                    {t("materialDataWarehouse")}
                  </h2>
                  <p className="text-[10px] font-mono text-slate-500 mt-1 uppercase tracking-widest">
                    PRI Research • Core Engine
                  </p>
                </div>
                <div className="p-1 flex flex-col gap-0.5">
                  <motion.button
                    whileHover={{
                      scale: 1.02,
                      x: 4,
                      backgroundColor: "rgba(241, 245, 249, 1)",
                    }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setActiveView("dashboard");
                      setShowAppMenu(false);
                    }}
                    className="w-full text-left px-3 py-2.5 text-[13px] text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white rounded transition-all flex items-center gap-2 group/btn focus:outline-none"
                  >
                    <LayoutDashboard
                      size={14}
                      className="text-slate-400 group-hover/btn:text-primary-500 transition-colors"
                    />
                    <span className="font-medium tracking-tight">
                      {t("dataWarehouse", "主数据大视野")}
                    </span>
                  </motion.button>
                  <motion.button
                    whileHover={{
                      scale: 1.02,
                      x: 4,
                      backgroundColor: "rgba(241, 245, 249, 1)",
                    }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      openModal("systemHealth");
                      setShowAppMenu(false);
                    }}
                    className="w-full text-left px-3 py-2.5 text-[13px] text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white rounded transition-all flex items-center gap-2 group/btn focus:outline-none"
                  >
                    <Zap
                      size={14}
                      className="text-slate-400 group-hover/btn:text-amber-500 transition-colors"
                    />
                    <span className="font-medium tracking-tight">
                      {t("systemStatus", "系统健康与环境")}
                    </span>
                  </motion.button>
                </div>
                <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                    v3.2.0-stable
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-slate-400/80 dark:text-slate-500">
                      12ms • RTT
                    </span>
                    <span className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-600 dark:text-emerald-500">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/80 animate-pulse hidden sm:block"></span>
                      {systemStatus === "online" ? "SYS.READY" : "SYNCING"}
                    </span>
                  </div>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
      <div className="flex-1 flex flex-col gap-3">
        {[
          {
            id: "dashboard",
            icon: LayoutDashboard,
            label: t("dataWarehouse"),
          },
          {
            id: "analytics",
            icon: PieChart,
            label: t("scientificVisualization"),
          },
          {
            id: "pivot",
            icon: TableProperties,
            label: t("dataPivot", "数据透视"),
          },
          {
            id: "dependencies",
            icon: Network,
            label: t("dependencyMap", "依赖网络谱图"),
          },
          {
            id: "beta-sandbox",
            icon: Cpu,
            label: t("betaSandboxNavLabel"),
          },
        ].map((btn) => (
          <motion.button
            key={btn.id}
            whileHover={{
              scale: 1.05,
              backgroundColor:
                activeView === btn.id ? undefined : "rgba(241, 245, 249, 1)",
            }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setActiveView(btn.id as AppView)}
            className={`w-10 h-10 rounded-lg transition-all duration-300 relative group flex items-center justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 ${activeView === btn.id ? "text-primary-600 dark:text-primary-400 bg-primary-100 dark:bg-primary-900/30 shadow-sm" : "text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50"}`}
            title={btn.label}
          >
            <btn.icon size={20} className="relative z-10" />
            {activeView === btn.id && (
              <motion.div
                layoutId="navIndicator"
                className="absolute -left-3 top-1/2 -translate-y-1/2 w-1.5 h-6 bg-primary-500 rounded-r-lg shadow-[2px_0_10px_rgba(99,102,241,0.5)]"
              />
            )}
          </motion.button>
        ))}
      </div>
      <div className="flex flex-col gap-3 mb-2">
        {isSidebarVisibleView && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowSidebar(!showSidebar)}
            className={`w-10 h-10 flex items-center justify-center transition-all focus:outline-none focus-visible:ring-2 rounded-lg group ${showSidebar ? "bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-200/50 dark:border-primary-800/50" : "text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50 border border-transparent hover:border-slate-200 dark:hover:border-slate-800"}`}
            title={showSidebar ? t("hideSidebar", "隐藏侧边栏") : t("showSidebar", "显示侧边栏")}
          >
            <motion.div
              animate={{ rotate: showSidebar ? 0 : 180 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
            >
              <ShieldCheck
                size={20}
                className={showSidebar ? "" : "opacity-40"}
                style={{ visibility: "hidden", position: "absolute" }}
              />
              {/* Using a different icon for the sidebar toggle */}
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="group-hover:scale-110 transition-transform"
              >
                <rect width="18" height="18" x="3" y="3" rx="2" />
                <path d="M9 3v18" />
                {showSidebar ? (
                  <path d="m14 9-3 3 3 3" />
                ) : (
                  <path d="m11 9 3 3-3 3" />
                )}
              </svg>
            </motion.div>
          </motion.button>
        )}

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => openModal("admin")}
          className="w-10 h-10 flex items-center justify-center text-slate-400 dark:text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 group"
          title={t("adminPanel")}
        >
          <ShieldCheck
            size={20}
            className="group-hover:scale-110 transition-transform"
          />
        </motion.button>
      <div className="relative group/dev mt-2 flex items-center justify-center"><div className="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-800 border-2 border-primary-500/50 hover:border-primary-500 overflow-hidden shadow-sm flex items-center justify-center cursor-help transition-colors"><img src={"data:image/svg+xml;utf8,<svg viewBox='0 0 100 100' fill='none' xmlns='http://www.w3.org/2000/svg'><circle cx='50' cy='50' r='8' fill='%234f46e5'/><ellipse cx='50' cy='50' rx='40' ry='12' stroke='%236366f1' stroke-width='2.5' transform='rotate(0 50 50)'/><ellipse cx='50' cy='50' rx='40' ry='12' stroke='%233b82f6' stroke-width='2.5' transform='rotate(60 50 50)'/><ellipse cx='50' cy='50' rx='40' ry='12' stroke='%238b5cf6' stroke-width='2.5' transform='rotate(120 50 50)'/><circle cx='90' cy='50' r='4' fill='%236366f1' /><circle cx='70' cy='84' r='4' fill='%233b82f6' /><circle cx='30' cy='16' r='4' fill='%238b5cf6' /></svg>"} alt="Developer haojunsun" className="w-full h-full object-cover" /></div><div className="absolute left-[calc(100%+0.5rem)] bottom-0 px-3 py-1.5 bg-slate-800 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-bold rounded shadow-lg opacity-0 invisible group-hover/dev:opacity-100 group-hover/dev:visible transition-all z-50 whitespace-nowrap pointer-events-none tracking-tight"><span className="opacity-70 font-mono text-[10px] mr-1 uppercase">Developer</span><span className="text-primary-400 dark:text-primary-600">haojunsun</span></div></div></div></nav>);};
