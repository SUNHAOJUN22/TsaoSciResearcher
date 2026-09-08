import React, {
  useState,
  useMemo,
  useCallback,
  Suspense,
  lazy,
  memo,
  useEffect,
} from "react";

// --- ResizeObserver Error Suppression ---
// We suppress the Vite error overlay for ResizeObserver loop errors.
// This is handled via a useEffect hook inside AppContent to prevent memory leaks and duplicate listeners.

import { ScienceWorkspacePanel } from '@/components/ScienceWorkspacePanel';

import { CATEGORY_TREE } from '@/config/constants';
import { RESIN_DATA_STATUS } from '@/data/resinData';
import { safeStorage } from "@/lib/utils";
import {
  Manufacturer,
} from "../types";
import { TreeSidebar } from '@/components/layout/TreeSidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthScreen } from '@/components/features/Auth/AuthScreen';
import { motion, AnimatePresence, LayoutGroup } from "motion/react";


import { LanguageProvider, useLanguage } from "@/contexts/LanguageContext";
import { ThemeProvider, useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { useToasts } from "@/contexts/ToastContext";
import { useUI } from "@/contexts/UIContext";
import { useData } from "@/contexts/DataContext";
import { useModals } from "@/contexts/ModalContext";

// New Components
import { ToastContainer } from '@/components/ui/ToastContainer';
import { BatchActionBar } from '@/components/features/DataGrid/BatchActionBar';
import { useShortcuts } from '@/hooks/app/useShortcuts';
import { useSavedViews } from '@/hooks/app/useSavedViews';
import { useExportData } from '@/hooks/app/useExportData';
import { useClickFeedback } from '@/hooks/useClickFeedback';

// Lazy loaded modals and heavy components
const FilterPanel = lazy(() =>
  import("@/components/features/Filters/FilterPanel").then((m) => ({ default: m.FilterPanel })),
);
const ImportModal = lazy(() =>
  import("@/components/modals/ImportModal").then((m) => ({ default: m.ImportModal })),
);
import { ProfileModal } from "@/components/modals/ProfileModal";
const AdminModal = lazy(() =>
  import("@/components/modals/AdminModal").then((m) => ({ default: m.AdminModal })),
);
const ProductDetailDrawer = lazy(() =>
  import("@/components/features/Product/ProductDetailDrawer").then((m) => ({ default: m.ProductDetailDrawer })),
);
const ComparisonView = lazy(() =>
  import("@/components/views/ComparisonView").then((m) => ({ default: m.ComparisonView })),
);
const PivotView = lazy(() =>
  import("@/components/views/PivotView").then((m) => ({ default: m.PivotView })),
);
const AnalyticsView = lazy(() =>
  import("@/components/views/AnalyticsView").then((m) => ({ default: m.AnalyticsView })),
);
const BetaSandboxView = lazy(() =>
  import("@/components/views/BetaSandboxView").then((m) => ({ default: m.BetaSandboxView })),
);
const DependencyMapD3 = lazy(() => import("@/components/charts/DependencyMapD3"));
const BatchEditModal = lazy(() =>
  import("@/components/modals/BatchEditModal").then((m) => ({ default: m.BatchEditModal })),
);
const BulkTaggingModal = lazy(() =>
  import("@/components/modals/BulkTaggingModal").then((m) => ({ default: m.BulkTaggingModal })),
);
const BulkReorderModal = lazy(() =>
  import("@/components/modals/BulkReorderModal").then((m) => ({ default: m.BulkReorderModal })),
);
const SystemHealthModal = lazy(() =>
  import("@/components/modals/SystemHealthModal").then((m) => ({ default: m.SystemHealthModal })),
);
const ShortcutsModal = lazy(() =>
  import("@/components/modals/ShortcutsModal").then((m) => ({ default: m.ShortcutsModal })),
);
const CommandPalette = lazy(() =>
  import("@/components/features/Navigation/CommandPalette").then((m) => ({ default: m.CommandPalette })),
);
const OnboardingTour = lazy(() =>
  import("@/components/features/Onboarding/OnboardingTour").then((m) => ({ default: m.OnboardingTour })),
);
const FeedbackModal = lazy(() =>
  import("@/components/modals/FeedbackModal").then((m) => ({ default: m.FeedbackModal })),
);
const HelpModal = lazy(() => import("@/components/modals/HelpModal"));
const FormulaEditorModal = lazy(() =>
  import("@/components/modals/FormulaEditorModal").then((m) => ({
    default: m.FormulaEditorModal,
  })),
);
const HistoryDrawer = lazy(() =>
  import("@/components/features/Navigation/HistoryDrawer").then((m) => ({ default: m.HistoryDrawer }))
);
const DatabaseSyncModal = lazy(() =>
  import("@/components/modals/DatabaseSyncModal").then((m) => ({ default: m.DatabaseSyncModal }))
);
const QaReportModal = lazy(() =>
  import("@/components/modals/QaReportModal").then((m) => ({ default: m.QaReportModal }))
);
const DataQualityAuditModal = lazy(() =>
  import("@/components/modals/DataQualityAuditModal").then((m) => ({ default: m.DataQualityAuditModal }))
);
const SmartExportModal = lazy(() =>
  import("@/components/modals/SmartExportModal").then((m) => ({ default: m.SmartExportModal }))
);

import { Loader2 } from "lucide-react";

import { DashboardView } from "@/components/views/DashboardView";

import { ToastProvider } from "@/contexts/ToastContext";
import { ModalProvider } from "@/contexts/ModalContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { UIProvider } from "@/contexts/UIContext";
import { DataProvider } from "@/contexts/DataContext";

// --- Main App Component ---

import { FloatingParticles } from '@/components/ui/FloatingParticles';
import { AiCopilot } from '@/components/features/Ai/AiCopilot';

import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import { SystemNav } from '@/components/layout/SystemNav';
import { AddProductModal } from "@/components/modals/AddProductModal";
import { SmartAnalysisModal } from "@/components/modals/SmartAnalysisModal";

// Memoized components to prevent unnecessary flickering and re-renders
const MemoizedTopBar = memo(TopBar);
const MemoizedTreeSidebar = memo(TreeSidebar);
const MemoizedDashboardView = memo(DashboardView);
const MemoizedAnalyticsView = memo(AnalyticsView);
const MemoizedBetaSandboxView = memo(BetaSandboxView);

const AppContent = memo(() => {
  const { t } = useLanguage();
  const { toggleTheme } = useTheme();
  const { currentUser, login, updateUserProfile } = useAuth();
  const { toasts, removeToast, addToast } = useToasts();
  const {
    activeView,
    setActiveView,
    showSidebar,
    setShowSidebar,
    showFilters,
    setShowFilters,
    systemStatus,
    isHistoryOpen,
    setHistoryOpen,
  } = useUI();
  const {
    allProducts,
    isLoading,
    filteredData,
    searchQuery,
    setSearchQuery,
    selectedCategoryIds,
    setSelectedCategoryIds,
    advancedFilterGroup,
    setAdvancedFilterGroup,
    columns,
    setColumns,
    categoryCounts,
    selectedIds,
    setSelectedIds,
    handleDelete,
    handleUpdate,
    handleCreate,
    handleBatchUpdate,
    handleBatchTagging,
    handleBatchReorder,
    handleImportData,
    minCompleteness,
    setMinCompleteness,
    formulas,
    addFormula,
    updateFormula,
    removeFormula,
    history,
    restoreSnapshot,
    syncEvents,
  } = useData();

  const {
    openModals,
    viewingProduct,
    analyzingProduct,
    openModal,
    closeModal,
    closeAllModals,
    setViewingProduct,
    closeDetail,
    isModalOpen,
  } = useModals();

  const { triggerFeedback } = useClickFeedback();

  const [showTour, setShowTour] = useState(() => {
    try {
      return !safeStorage.local.getItem("resindb-tour-completed");
    } catch {
      return false;
    }
  });
  const [showAppMenu, setShowAppMenu] = useState(false);

  // Still use saved views hook but it can be refactored into context later
  const {
    savedViews,
    saveView,
    applyView,
    deleteView,
  } = useSavedViews(
    searchQuery,
    advancedFilterGroup,
    columns,
    setSearchQuery,
    setAdvancedFilterGroup,
    setColumns,
    addToast,
    t
  );

  const lastSyncTime = syncEvents[0]
    ? new Date(syncEvents[0].timestamp).toLocaleTimeString()
    : t("notSynced", "Not synced");

  const applicationActions = {
    handleDelete,
    handleUpdate,
    handleCreate,
    handleBatchUpdate,
    handleImportData,
    handleUpdateUserProfile: updateUserProfile
  };

  // Re-use some hooks from original implementation
  const { isExporting, handleExport } = useExportData(filteredData, addToast, t);

  const handleExportPdf = useCallback(async () => {
      
      try {
         // Create a simple @media print styled report.
         document.body.classList.add("printing-mode");
         window.print();
      } finally {
         document.body.classList.remove("printing-mode");
      }
  }, []);

  useShortcuts({
    closeAllModals,
    openModal,
    setShowSidebar,
    selectedIds,
    handleExport,
  });

  // --- Global Click tactile & audio feedback handler ---
  useEffect(() => {
    const handleGlobalClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Check semantic interactive elements first
      const interactive = target.closest(
        'button, [role="button"], a, input[type="submit"], input[type="button"], input[type="checkbox"], input[type="radio"], select, option'
      );
      if (interactive) {
        triggerFeedback();
        return;
      }
      // Fallback: check if element or ancestors have pointer cursor
      let el: HTMLElement | null = target;
      for (let i = 0; i < 3 && el; i++) {
        try {
          if (window.getComputedStyle(el).cursor === 'pointer') {
            triggerFeedback();
            return;
          }
        } catch { break; }
        el = el.parentElement;
      }
    };
    document.addEventListener("click", handleGlobalClick, { capture: true, passive: true });
    return () => {
      document.removeEventListener("click", handleGlobalClick, { capture: true });
    };
  }, [triggerFeedback]);

  // --- Suppression of ResizeObserver loop errors ---
  useEffect(() => {
    const handleResizeObserverError = (e: ErrorEvent) => {
      if (
        e.message === "ResizeObserver loop limit exceeded" ||
        e.message ===
          "ResizeObserver loop completed with undelivered notifications."
      ) {
        const overlay = document.querySelector("vite-error-overlay");
        if (overlay) overlay.remove();
      }
    };
    window.addEventListener("error", handleResizeObserverError);
    return () => {
      window.removeEventListener("error", handleResizeObserverError);
    };
  }, []);

  // --- Centralized Scroll Lock for Modals & Overlays ---
  useEffect(() => {
    const isAnyModalOpen =
      (openModals && openModals.size > 0) ||
      viewingProduct !== null ||
      analyzingProduct !== null ||
      showFilters ||
      isHistoryOpen;

    if (isAnyModalOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }

    return () => {
      document.body.style.overflow = "";
    };
  }, [openModals, viewingProduct, analyzingProduct, showFilters, isHistoryOpen]);

  const toggleCategory = useCallback(
    (id: string) => {
      setSelectedCategoryIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    [setSelectedCategoryIds],
  );

  const manufacturers = useMemo(() => {
    const uniqueNames = Array.from(
      new Set(allProducts.map((p) => p.manufacturer)),
    );
    return uniqueNames.map((name) => ({ id: `m-${name}`, name }));
  }, [allProducts]);

  if (!currentUser) return <AuthScreen onLogin={login} />;

  if (activeView === "dashboard" && allProducts.length === 0 && isLoading) {
    return (
      <div className="h-[100dvh] w-full flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
        <FloatingParticles />
        <div className="relative z-10 flex flex-col items-center">
          <div className="w-24 h-24 mb-6 relative">
            <div className="absolute inset-0 rounded-full border-4 border-primary-500/20 animate-pulse" />
            <div className="absolute inset-0 rounded-full border-t-4 border-primary-500 animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-primary-500" />
            </div>
          </div>
          <h2 className="text-xl font-black tracking-tight mb-2 uppercase italic">{t("initializing", "Initializing ResinDB")}</h2>
          <p className="text-slate-500 dark:text-slate-400 font-mono text-xs animate-pulse">
            {t("warmingUp", "Warming up hyper-threaded data index...")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] w-full bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 transition-colors duration-300">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <FloatingParticles />
      {RESIN_DATA_STATUS.usingFallback && (
        <div
          role="alert"
          data-testid="external-data-warning"
          className="fixed bottom-4 left-1/2 z-[260] max-w-[min(92vw,760px)] -translate-x-1/2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 shadow-xl dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
        >
          <strong>{t("externalDataFallback", "外部树脂数据部分加载失败")}</strong>
          <span className="ml-2">
            {RESIN_DATA_STATUS.failures.map((failure) => failure.asset).join(", ")}
          </span>
        </div>
      )}

      <div className="print:hidden">
        <SystemNav
          activeView={activeView}
          setActiveView={setActiveView}
          showAppMenu={showAppMenu}
          setShowAppMenu={setShowAppMenu}
          showSidebar={showSidebar}
          setShowSidebar={setShowSidebar}
          systemStatus={systemStatus}
          openModal={openModal}
          t={t}
        />
      </div>

      <LayoutGroup>
        <div className="flex-1 flex flex-col min-w-0 h-full relative overflow-hidden bg-slate-50 dark:bg-slate-950">
          <div className="shrink-0 z-[60] relative print:hidden">
            <ScienceWorkspacePanel />
            <MemoizedTopBar
              isExporting={isExporting}
              savedViews={savedViews}
              onSaveView={saveView}
              onApplyView={applyView}
              onDeleteView={deleteView}
              lastSyncTime={lastSyncTime}
            />
          </div>

          <div className="flex-1 flex overflow-hidden relative bg-white dark:bg-slate-950">
            <motion.div
              animate={{
                width:
                  showSidebar &&
                  (activeView === "dashboard" || activeView === "analytics")
                    ? window.innerWidth >= 1024
                      ? 256
                      : 224
                    : 0,
                opacity:
                  showSidebar &&
                  (activeView === "dashboard" || activeView === "analytics")
                    ? 1
                    : 0,
              }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 32,
                restDelta: 0.001,
              }}
              className="shrink-0 border-r border-slate-200/50 dark:border-slate-800/50 bg-white/90 dark:bg-slate-900/90 backdrop-blur-3xl flex flex-col z-[60] relative h-full overflow-hidden will-change-[width,opacity] transform-gpu print:hidden"
            >
              <div className="w-64 h-full">
                <MemoizedTreeSidebar
                  categories={CATEGORY_TREE}
                  selectedCategoryIds={selectedCategoryIds}
                  onToggleCategory={toggleCategory}
                  onClearCategories={() => setSelectedCategoryIds(new Set())}
                  totalCount={allProducts.length}
                  counts={categoryCounts}
                  minCompleteness={minCompleteness}
                  onMinCompletenessChange={setMinCompleteness}
                  isLoading={isLoading}
                  className="h-full border-none shadow-none"
                />
              </div>
            </motion.div>

            <AnimatePresence>
              {showSidebar &&
                (activeView === "dashboard" || activeView === "analytics") && (
                  <motion.div
                    key="sidebar-overlay-mobile"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setShowSidebar(false)}
                    className="md:hidden fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-[55]"
                  />
                )}
            </AnimatePresence>

            <div className="flex-1 flex flex-col min-h-0 min-w-0 relative bg-white dark:bg-slate-950 overflow-hidden transform-gpu">
              <div className="absolute inset-0 z-0">
                <motion.div
                  initial={false}
                  animate={{ opacity: activeView === "dashboard" ? 1 : 0, zIndex: activeView === "dashboard" ? 10 : 0 }}
                  className={`absolute inset-0 ${activeView === "dashboard" ? "pointer-events-auto" : "pointer-events-none"}`}
                >
                  <Suspense
                    fallback={
                      <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 dark:bg-slate-950/50">
                        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
                      </div>
                    }
                  >
                    <MemoizedDashboardView />
                  </Suspense>
                </motion.div>

                <motion.div
                  initial={false}
                  animate={{ opacity: activeView === "analytics" ? 1 : 0, zIndex: activeView === "analytics" ? 10 : 0 }}
                  className={`absolute inset-0 ${activeView === "analytics" ? "pointer-events-auto" : "pointer-events-none"}`}
                >
                  <Suspense
                    fallback={
                      <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 dark:bg-slate-950/50">
                        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
                      </div>
                    }
                  >
                    <MemoizedAnalyticsView />
                  </Suspense>
                </motion.div>

                <motion.div
                  initial={false}
                  animate={{ opacity: activeView === "pivot" ? 1 : 0, zIndex: activeView === "pivot" ? 10 : 0 }}
                  className={`absolute inset-0 ${activeView === "pivot" ? "pointer-events-auto" : "pointer-events-none"}`}
                >
                  <Suspense
                    fallback={
                      <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 dark:bg-slate-950/50">
                        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
                      </div>
                    }
                  >
                    <PivotView data={filteredData} columns={columns} formulas={formulas} />
                  </Suspense>
                </motion.div>

                <motion.div
                  initial={false}
                  animate={{ opacity: activeView === "dependencies" ? 1 : 0, zIndex: activeView === "dependencies" ? 10 : 0 }}
                  className={`absolute inset-0 ${activeView === "dependencies" ? "pointer-events-auto" : "pointer-events-none"}`}
                >
                  <Suspense
                    fallback={
                      <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 dark:bg-slate-950/50">
                        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
                      </div>
                    }
                  >
                    <DependencyMapD3 />
                  </Suspense>
                </motion.div>

                <motion.div
                  initial={false}
                  animate={{ opacity: activeView === "beta-sandbox" ? 1 : 0, zIndex: activeView === "beta-sandbox" ? 10 : 0 }}
                  className={`absolute inset-0 ${activeView === "beta-sandbox" ? "pointer-events-auto" : "pointer-events-none"}`}
                >
                  <Suspense
                    fallback={
                      <div className="absolute inset-0 flex items-center justify-center bg-slate-50/50 dark:bg-slate-950/50">
                        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
                      </div>
                    }
                  >
                    <MemoizedBetaSandboxView />
                  </Suspense>
                </motion.div>
              </div>
            </div>
          </div>

          <AnimatePresence mode="popLayout">
            {selectedIds.size > 0 && (
              <BatchActionBar
                key="batch-bar"
                selectedIds={selectedIds}
                setSelectedIds={setSelectedIds}
                setIsComparisonOpen={(val) =>
                  val ? openModal("comparison") : closeModal("comparison")
                }
                setIsBatchEditOpen={(val) =>
                  val ? openModal("batchEdit") : closeModal("batchEdit")
                }
                setIsBulkTaggingOpen={(val) =>
                  val ? openModal("bulkTagging") : closeModal("bulkTagging")
                }
                setIsBulkReorderOpen={(val) =>
                  val ? openModal("bulkReorder") : closeModal("bulkReorder")
                }
                handleExport={handleExport}
                onOpenQaReport={() => openModal("qaReport")}
                handleDelete={(ids) => handleDelete(ids)}
                addToast={addToast}
                allProducts={allProducts}
                history={history}
                restoreSnapshot={restoreSnapshot}
              />
            )}
          </AnimatePresence>
        </div>
      </LayoutGroup>

      <Suspense fallback={null}>
        <MobileBottomNav
          activeView={activeView}
          setActiveView={setActiveView}
          onOpenAdmin={() => openModal("admin")}
          t={t}
        />
        <ImportModal
          isOpen={isModalOpen("import")}
          onClose={() => closeModal("import")}
          allProducts={allProducts}
          onImport={(data) => {
            handleImportData(data);
            closeModal("import");
          }}
        />
        <ProfileModal
          isOpen={isModalOpen("profile")}
          onClose={() => closeModal("profile")}
          user={currentUser}
          onSave={(data) => {
            updateUserProfile(data);
            closeModal("profile");
          }}
          onAddToast={addToast}
        />
        <AdminModal isOpen={isModalOpen("admin")} onClose={() => closeModal("admin")} />
        <SystemHealthModal
          isOpen={isModalOpen("systemHealth")}
          onClose={() => closeModal("systemHealth")}
          status={systemStatus}
          addToast={addToast}
        />
        <FeedbackModal
          isOpen={isModalOpen("feedback")}
          onClose={() => closeModal("feedback")}
        />
        <HelpModal isOpen={isModalOpen("help")} onClose={() => closeModal("help")} />
        <ShortcutsModal
          isOpen={isModalOpen("shortcuts")}
          onClose={() => closeModal("shortcuts")}
        />
        <CommandPalette
          isOpen={isModalOpen("commandPalette")}
          onClose={() => closeModal("commandPalette")}
          onNavigate={(view) => {
            setActiveView(view);
            closeModal("commandPalette");
          }}
          onToggleTheme={toggleTheme}
          onOpenProfile={() => openModal("profile")}
          onOpenHelp={() => openModal("help")}
          onOpenFeedback={() => openModal("feedback")}
          onOpenAdmin={() => openModal("admin")}
          products={allProducts}
          manufacturers={manufacturers as Manufacturer[]}
          onViewProduct={setViewingProduct}
        />
        <ProductDetailDrawer
          isOpen={!!viewingProduct}
          product={viewingProduct!}
          allProducts={allProducts}
          onClose={closeDetail}
          onCategoryClick={(id) => setSelectedCategoryIds(new Set([id]))}
          onProductClick={setViewingProduct}
          onAddToast={addToast}
        />
        <AddProductModal
          isOpen={isModalOpen("addProduct")}
          onClose={() => closeModal("addProduct")}
          onSave={handleCreate}
          allProducts={allProducts}
        />
        <SmartAnalysisModal
          isOpen={isModalOpen("smartAnalysis")}
          onClose={() => closeModal("smartAnalysis")}
          product={analyzingProduct}
        />
        <DatabaseSyncModal
          isOpen={isModalOpen("databaseSync")}
          onClose={() => closeModal("databaseSync")}
        />
        <DataQualityAuditModal
          isOpen={isModalOpen("dataQualityAudit")}
          onClose={() => closeModal("dataQualityAudit")}
        />
        <SmartExportModal
          isOpen={isModalOpen("smartExport")}
          onClose={() => closeModal("smartExport")}
          filteredData={filteredData}
          handleExport={handleExport}
          handleExportPdf={handleExportPdf}
        />
        <QaReportModal
          isOpen={isModalOpen("qaReport")}
          onClose={() => closeModal("qaReport")}
          products={allProducts.filter((p) => selectedIds.has(p.id))}
        />
        <ComparisonView
          isOpen={isModalOpen("comparison")}
          products={allProducts.filter((p) => selectedIds.has(p.id))}
          allProducts={allProducts}
          onClose={() => closeModal("comparison")}
          onRemoveProduct={(id) => {
            const next = new Set(selectedIds);
            next.delete(id);
            setSelectedIds(next);
            if (next.size < 1) closeModal("comparison");
          }}
          onAddProduct={(id) => {
            const next = new Set(selectedIds);
            next.add(id);
            setSelectedIds(next);
          }}
        />
        <AnimatePresence mode="popLayout">
          {showFilters && (
            <motion.div
              key="filter-panel-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowFilters(false)}
              className="fixed inset-0 bg-slate-950/40 backdrop-blur-sm z-[140]"
            />
          )}
          {showFilters && (
            <FilterPanel
              key="filter-panel-main"
              isOpen={true}
              onClose={() => setShowFilters(false)}
              columns={columns}
              filterGroup={advancedFilterGroup}
              onFilterChange={setAdvancedFilterGroup}
              onClearFilters={() =>
                setAdvancedFilterGroup({
                  id: "root",
                  type: "group",
                  logic: "AND",
                  conditions: [],
                })
              }
            />
          )}
        </AnimatePresence>
        <BatchEditModal
          isOpen={isModalOpen("batchEdit")}
          onClose={() => closeModal("batchEdit")}
          onSave={handleBatchUpdate}
          selectedProducts={allProducts.filter((p) => selectedIds.has(p.id))}
        />
        <BulkTaggingModal
          isOpen={isModalOpen("bulkTagging")}
          onClose={() => closeModal("bulkTagging")}
          onSave={handleBatchTagging}
          selectedProducts={allProducts.filter((p) => selectedIds.has(p.id))}
        />
        <BulkReorderModal
          isOpen={isModalOpen("bulkReorder")}
          onClose={() => closeModal("bulkReorder")}
          onSave={handleBatchReorder}
          selectedProducts={allProducts.filter((p) => selectedIds.has(p.id))}
        />
        <FormulaEditorModal
          isOpen={isModalOpen("formulaEditor")}
          onClose={() => closeModal("formulaEditor")}
          formulas={formulas}
          onAdd={addFormula}
          onUpdate={updateFormula}
          onRemove={removeFormula}
          allProducts={allProducts}
        />
        <AiCopilot
          data={filteredData}
          activeChart={activeView === "analytics" ? "Visualizer" : undefined}
          actions={applicationActions}
        />
        <HistoryDrawer 
          isOpen={isHistoryOpen} 
          onClose={() => setHistoryOpen(false)} 
        />
        <AnimatePresence>
          {showTour && (
            <OnboardingTour
              key="onboarding-tour-root"
              onComplete={() => {
                setShowTour(false);
                safeStorage.local.setItem("resindb-tour-completed", "true");
              }}
            />
          )}
        </AnimatePresence>
      </Suspense>
    </div>
  );
});

const App: React.FC = () => (
  <LanguageProvider>
    <ToastProvider>
      <AuthProvider>
        <UIProvider>
          <DataProvider>
            <ModalProvider>
              <ThemeProvider>
                <AppContent />
              </ThemeProvider>
            </ModalProvider>
          </DataProvider>
        </UIProvider>
      </AuthProvider>
    </ToastProvider>
  </LanguageProvider>
);

export default App;
