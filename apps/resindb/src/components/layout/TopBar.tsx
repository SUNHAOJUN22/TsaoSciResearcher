import React, { useEffect } from "react";
import {
  Calculator,
  Filter,
  Upload,
  Keyboard,
  HelpCircle,
  MessageSquare,
  Plus,
  History,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { motion } from "motion/react";
import { useAuth } from "@/contexts/AuthContext";
import { useUI } from "@/contexts/UIContext";
import { useData } from "@/contexts/DataContext";
import { useModals } from "@/contexts/ModalContext";

// Sub-components
import { ColumnVisibilityMenu } from '@/components/features/DataGrid/ColumnVisibilityMenu';
import { UserAccountMenu } from '@/components/features/Navigation/UserAccountMenu';
import { SavedViewsMenu } from '@/components/features/Dashboard/SavedViewsMenu';
import { QuickActionMenu } from '@/components/features/Navigation/QuickActionMenu';
import { NotificationMenu } from '@/components/features/Navigation/NotificationMenu';
import { SearchControl } from '@/components/features/Navigation/SearchControl';
import { SystemStatusIndicator } from '@/components/ui/SystemStatusIndicator';

import { SavedView } from '@/types/index';

interface TopBarProps {
  isExporting: boolean;
  savedViews: SavedView[];
  onSaveView: (name: string) => void;
  onApplyView: (view: SavedView) => void;
  onDeleteView: (id: string) => void;
  lastSyncTime: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  isExporting,
  savedViews,
  onSaveView,
  onApplyView,
  onDeleteView,
  lastSyncTime,
}) => {
  const { t, language } = useLanguage();
  const { currentUser, logout } = useAuth();
  const {
    systemStatus,
    showFilters,
    setShowFilters,
    setHistoryOpen,
  } = useUI();
  const {
    columns,
    toggleColumn,
    toggleAllColumns,
    advancedFilterGroup,
  } = useData();
  const { openModal } = useModals();

  useEffect(() => {
    const focusSearch = () => {
      document.getElementById("global-search-input")?.focus();
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "f") {
        e.preventDefault();
        focusSearch();
      }
      if (
        e.key === "/" &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA" &&
        !e.metaKey &&
        !e.ctrlKey
      ) {
        e.preventDefault();
        focusSearch();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  useEffect(() => {
    const handleFocusSearch = () => {
      document.getElementById("global-search-input")?.focus();
    };
    window.addEventListener("focus-search", handleFocusSearch);
    return () => window.removeEventListener("focus-search", handleFocusSearch);
  }, []);

  const activeFilterCount = advancedFilterGroup.conditions.length;

  return (
    <div className="w-full flex flex-col px-4 xl:px-8 h-16 justify-center bg-white/98 dark:bg-slate-950/98 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-800/80 relative z-[100] shadow-sm overflow-x-auto overflow-y-hidden scrollbar-none py-1">
      <div className="flex flex-row items-center justify-start gap-3 w-full min-w-max">
        <div className="flex items-center gap-1.5 md:gap-3 flex-nowrap justify-start flex-1 min-w-max ml-auto">
          <div className="flex items-center gap-1.5 md:gap-2 relative flex-nowrap justify-start">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => openModal("formulaEditor")}
              className={`h-10 px-3 md:px-4 hidden md:flex items-center gap-2 border transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg shadow-sm bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800/80 text-primary-600 hover:border-primary-400 group relative overflow-hidden`}
              title={language === 'zh' ? "性能指数引擎" : "Performance Index Engine"}
            >
              <Calculator
                size={14}
                className="shrink-0 group-hover:scale-110 transition-transform"
              />
              <span className="hidden lg:inline text-xs font-mono tracking-widest uppercase whitespace-nowrap">
                {language === 'zh' ? "指标公式" : "Formula"}
              </span>
              <div className="absolute inset-0 bg-primary-500/5 translate-y-full group-hover:translate-y-0 transition-transform" />
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setHistoryOpen(true)}
              className="h-10 px-3 md:px-4 hidden md:flex items-center gap-2 border transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg shadow-sm bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800/80 text-amber-600 hover:border-amber-400 group relative overflow-hidden"
              title={language === 'zh' ? "显示版本历史" : "Show Version History"}
            >
              <History size={14} className="shrink-0 group-hover:-rotate-45 transition-transform" />
              <span className="hidden xl:inline text-xs font-mono tracking-widest uppercase whitespace-nowrap">
                {language === 'zh' ? "变更历史" : "History"}
              </span>
            </motion.button>

            <SavedViewsMenu
              savedViews={savedViews}
              onSaveView={onSaveView}
              onApplyView={onApplyView}
              onDeleteView={onDeleteView}
            />

            <QuickActionMenu
              onOpenImport={() => openModal("import")}
              onOpenSmartExport={() => openModal("smartExport")}
              isExporting={isExporting}
              onOpenAdmin={() => openModal("admin")}
              onOpenQualityAudit={() => openModal("dataQualityAudit")}
            />

            <ColumnVisibilityMenu
              columns={columns}
              onToggleColumn={toggleColumn}
              onToggleAllColumns={toggleAllColumns}
            />

            <div className="flex items-center gap-3 shrink-0">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowFilters(!showFilters)}
                className={`h-10 flex items-center gap-2 px-3 md:px-5 border transition-all group shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg shadow-sm backdrop-blur-md ${showFilters ? "bg-primary-50/80 border-primary-200/50 text-primary-600 dark:bg-primary-900/30 dark:border-primary-700/50 dark:text-primary-400" : "bg-white/60 dark:bg-slate-900/40 border-slate-200/50 dark:border-slate-800/50 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"}`}
              >
                <Filter size={16} className="shrink-0" />
                <span className="text-xs font-mono tracking-widest uppercase whitespace-nowrap hidden lg:inline">
                  {t("advancedFilters")}
                </span>
                {activeFilterCount > 0 && (
                  <span className="px-1.5 py-0.5 bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 text-[9px] font-black rounded-lg shrink-0">
                    {activeFilterCount}
                  </span>
                )}
              </motion.button>

              <SearchControl onOpenCommandPalette={() => openModal("commandPalette")} />

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => openModal("addProduct")}
                className="h-10 px-4 flex items-center gap-2 border border-emerald-200 dark:border-emerald-800/50 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50 shrink-0 rounded-lg shadow-sm"
              >
                <Plus size={14} className="shrink-0" />
                <span className="text-xs font-mono tracking-widest uppercase whitespace-nowrap hidden md:inline">
                  {t("addProduct")}
                </span>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => openModal("import")}
                className="relative h-10 px-3 md:px-6 bg-primary-600 hover:bg-primary-500 text-white flex items-center gap-2 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 shrink-0 border border-transparent rounded-lg shadow-sm overflow-hidden"
              >
                <div className="absolute inset-0 bg-white/20 translate-y-[-100%] group-hover:translate-y-[100%] transition-transform duration-700 ease-in-out" />
                <Upload size={14} className="shrink-0 relative z-10" />
                <span className="text-xs font-mono tracking-widest uppercase whitespace-nowrap hidden lg:inline relative z-10">
                  {t("importData")}
                </span>
              </motion.button>
            </div>

            <div className="flex items-center gap-2 ml-2 flex-nowrap justify-end shrink-0">
              <SystemStatusIndicator
                systemStatus={systemStatus}
                lastSyncTime={lastSyncTime}
                onOpenSystemHealth={() => openModal("systemHealth")}
              />

              <NotificationMenu t={t} />

               <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => openModal("shortcuts")}
                className="flex p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 transition-all relative group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg"
                title={t("keyboardShortcuts")}
              >
                <Keyboard size={18} />
                <span className="absolute -bottom-10 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-slate-900 text-white text-[10px] font-mono tracking-widest rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none shadow-xl uppercase whitespace-nowrap">
                  {t("keyboardShortcuts")}
                </span>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => openModal("help")}
                className="flex p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 transition-all relative group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg"
                title={t("helpCenter")}
              >
                <HelpCircle size={18} />
                <span className="absolute -bottom-10 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-slate-900 text-white text-[10px] font-mono tracking-widest rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none shadow-xl uppercase whitespace-nowrap">
                  {t("helpCenter")}
                </span>
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => openModal("feedback")}
                className="flex p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 transition-all relative group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg"
                title={t("sendFeedback")}
              >
                <MessageSquare size={18} />
                <span className="absolute -bottom-10 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-slate-900 text-white text-[10px] font-mono tracking-widest rounded opacity-0 group-hover:opacity-100 transition-all pointer-events-none shadow-xl uppercase whitespace-nowrap">
                  {t("sendFeedback")}
                </span>
              </motion.button>
            </div>

            <UserAccountMenu
              user={currentUser}
              onLogout={logout}
              onOpenProfile={() => openModal("profile")}
              onOpenAdmin={() => openModal("admin")}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
