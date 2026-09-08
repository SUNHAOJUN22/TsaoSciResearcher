import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Search,
  Command,
  LayoutDashboard,
  PieChart,
  ShieldCheck,
  User,
  Moon,
  HelpCircle,
  MessageSquare,
  ArrowRight,
  Zap,
  Database,
  Factory,
} from "lucide-react";
import { AppView, Product, Manufacturer } from '@/types/index';
import { motion, AnimatePresence } from "motion/react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useData } from "@/contexts/DataContext";
import { useUI } from "@/contexts/UIContext";
import { History } from "lucide-react";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: AppView) => void;
  onToggleTheme: () => void;
  onOpenProfile: () => void;
  onOpenHelp: () => void;
  onOpenFeedback: () => void;
  onOpenAdmin: () => void;
  products: Product[];
  manufacturers: Manufacturer[];
  onViewProduct: (p: Product) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = React.memo(({
  isOpen,
  onClose,
  onNavigate,
  onToggleTheme,
  onOpenProfile,
  onOpenHelp,
  onOpenFeedback,
  onOpenAdmin,
  products,
  manufacturers,
  onViewProduct,
}) => {
  const { t } = useLanguage();
  const { recentSearches, setSearchQuery, setAdvancedFilterGroup, setSelectedCategoryIds } = useData();
  const { clickFeedbackEnabled, setClickFeedbackEnabled } = useUI();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredResults = useMemo(() => {
    const q = query.toLowerCase().trim();
    const commands = [
      {
        id: "dashboard",
        label: t("navDashboard"),
        icon: LayoutDashboard,
        category: t("categoryNav"),
        action: () => onNavigate("dashboard"),
      },
      {
        id: "analytics",
        label: t("navAnalytics"),
        icon: PieChart,
        category: t("categoryNav"),
        action: () => onNavigate("analytics"),
      },
      {
        id: "profile",
        label: t("profile"),
        icon: User,
        category: t("categoryUser"),
        action: onOpenProfile,
      },
      {
        id: "admin",
        label: t("adminPanel"),
        icon: ShieldCheck,
        category: t("categorySystem"),
        action: onOpenAdmin,
      },
      {
        id: "theme",
        label: t("toggleTheme"),
        icon: Moon,
        category: t("categoryPrefs"),
        action: onToggleTheme,
      },
      {
        id: "clickFeedback",
        label: clickFeedbackEnabled ? t("disableClickFeedback") : t("enableClickFeedback"),
        icon: Zap,
        category: t("categoryPrefs"),
        action: () => setClickFeedbackEnabled(!clickFeedbackEnabled),
      },
      {
        id: "help",
        label: t("helpCenter"),
        icon: HelpCircle,
        category: t("categorySupport"),
        action: onOpenHelp,
      },
      {
        id: "feedback",
        label: t("sendFeedback"),
        icon: MessageSquare,
        category: t("categorySupport"),
        action: onOpenFeedback,
      },
    ];

    // 1. Search Commands
    const cmdResults = commands
      .filter(
        (cmd) =>
          cmd.label.toLowerCase().includes(q) ||
          cmd.category.toLowerCase().includes(q),
      )
      .map((c) => ({ ...c, type: "command" }));

    // 2. Search Products (Grades)
    const productResults = products
      .filter(
        (p) =>
          p.gradeName.toLowerCase().includes(q) ||
          p.manufacturer.toLowerCase().includes(q),
      )
      .slice(0, 5)
      .map((p) => ({
        id: p.id,
        label: p.gradeName,
        icon: Database,
        category: t("categoryProducts"),
        action: () => onViewProduct(p),
        type: "product",
        meta: p.manufacturer,
      }));

    // 3. Search Manufacturers
    const manufacturerResults = manufacturers
      .filter((m) => m.name.toLowerCase().includes(q))
      .slice(0, 3)
      .map((m) => ({
        id: m.id,
        label: m.name,
        icon: Factory,
        category: t("categoryManufacturers"),
        action: () => {
          onNavigate("dashboard");
        },
        type: "manufacturer",
        meta: m.country || "",
      }));

    // 4. Recent Searches
    const recentResults = recentSearches
      .filter((r) => r.label.toLowerCase().includes(q))
      .map((r) => ({
        id: `recent-${r.id}`,
        label: r.label,
        icon: History,
        category: t("recentSearches") || "近期搜索 / 预设过滤",
        action: () => {
          setSearchQuery(r.query);
          setAdvancedFilterGroup(r.filters);
          setSelectedCategoryIds(new Set(r.selectedCategoryIds || []));
          onNavigate("dashboard");
        },
        type: "recent",
        meta: new Date(r.timestamp).toLocaleTimeString(),
      }));

    if (!q) {
      return [...recentResults, ...commands.map((c) => ({ ...c, type: "command" }))];
    }

    return [...cmdResults, ...recentResults, ...productResults, ...manufacturerResults];
  }, [
    query,
    products,
    manufacturers,
    recentSearches,
    onNavigate,
    onViewProduct,
    setSearchQuery,
    setAdvancedFilterGroup,
    setSelectedCategoryIds,
    onOpenProfile,
    onOpenAdmin,
    onToggleTheme,
    onOpenHelp,
    onOpenFeedback,
    t,
    clickFeedbackEnabled,
    setClickFeedbackEnabled,
  ]);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredResults.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex(
          (prev) =>
            (prev - 1 + filteredResults.length) % filteredResults.length,
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredResults[selectedIndex]) {
          filteredResults[selectedIndex].action();
          onClose();
        }
      } else if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredResults, selectedIndex, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="command-palette-root"
          className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] px-4 pointer-events-none"
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm pointer-events-auto"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="w-full max-w-2xl bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-3xl shadow-2xl overflow-hidden pointer-events-auto relative z-10"
          >
            <div className="flex items-center gap-4 px-6 py-4 border-b border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 relative overflow-hidden">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-200 dark:border-primary-800 rounded-xl shadow-inner">
                <Command size={20} />
              </div>
              <input
                ref={inputRef}
                type="text"
                placeholder="输入命令或搜索功能..."
                className="flex-1 bg-transparent border-none outline-none text-base font-mono font-bold text-slate-800 dark:text-white placeholder:text-slate-500 relative z-10"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
              />
              <div className="flex items-center gap-2 px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-[9px] font-mono text-slate-500 uppercase tracking-widest relative z-10 shadow-sm">
                ESC
              </div>
            </div>

            <div className="max-h-[60vh] overflow-y-auto p-2 custom-scrollbar bg-white dark:bg-slate-950">
              {filteredResults.length === 0 ? (
                <div className="py-12 text-center">
                  <div className="w-16 h-16 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center mx-auto mb-4">
                    <Search
                      size={24}
                      className="text-slate-300 dark:text-slate-600"
                    />
                  </div>
                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                    {t("noResultsFoundPalette")}
                  </p>
                </div>
              ) : (
                <div className="space-y-4 p-2">
                  {Object.entries(
                    filteredResults.reduce(
                      (acc, res) => {
                        if (!acc[res.category]) acc[res.category] = [];
                        acc[res.category].push(res);
                        return acc;
                      },
                      {} as Record<string, typeof filteredResults>,
                    ),
                  ).map(([category, items]) => (
                    <div key={category} className="space-y-1">
                      <h4 className="px-3 text-[9px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2">
                        {category}
                      </h4>
                      <div className="space-y-1">
                        {items.map((res) => {
                          const globalIndex = filteredResults.indexOf(res);
                          const isSelected = globalIndex === selectedIndex;
                          return (
                            <motion.button
                              key={res.id}
                              onClick={() => {
                                res.action();
                                onClose();
                              }}
                              onMouseEnter={() => setSelectedIndex(globalIndex)}
                              whileHover={{
                                scale: 1.01,
                                backgroundColor: isSelected
                                  ? undefined
                                  : "rgba(241, 245, 249, 0.5)",
                              }}
                              whileTap={{ scale: 0.98 }}
                              className={`w-full flex items-center justify-between px-4 py-3 border rounded-xl transition-all ${isSelected ? "bg-primary-600 text-white border-primary-600 shadow-xl shadow-primary-600/20" : "text-slate-600 dark:text-slate-400 bg-transparent border-transparent hover:bg-slate-50 dark:hover:bg-slate-900 hover:border-slate-200 dark:hover:border-slate-800"}`}
                            >
                              <div className="flex items-center gap-4 flex-1 min-w-0">
                                <div
                                  className={`p-1.5 border rounded-lg transition-colors ${isSelected ? "bg-white/20 border-white/30" : "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700"}`}
                                >
                                  <res.icon size={16} />
                                </div>
                                <div className="text-left min-w-0">
                                  <span className="block text-xs font-mono font-bold tracking-tight leading-none mb-1 truncate">
                                    {res.label}
                                  </span>
                                  <span
                                    className={`text-[9px] font-mono uppercase tracking-widest ${isSelected ? "text-white/60" : "text-slate-400"}`}
                                  >
                                    {res.type === "product"
                                      ? (res as { meta?: string }).meta
                                      : res.type === "manufacturer"
                                        ? (res as { meta?: string }).meta
                                        : res.type === "recent"
                                          ? (res as { meta?: string }).meta
                                          : t("executeAction")}
                                  </span>
                                </div>
                              </div>
                              {isSelected && (
                                <motion.div
                                  layoutId="arrow"
                                  initial={{ x: -10, opacity: 0 }}
                                  animate={{ x: 0, opacity: 1 }}
                                  className="flex items-center gap-2"
                                >
                                  <span className="text-[9px] font-mono uppercase tracking-widest">
                                    ENTER
                                  </span>
                                  <ArrowRight size={14} />
                                </motion.div>
                              )}
                            </motion.button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-300 dark:border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1">
                    <div className="px-1 py-0.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded shadow-sm text-[8px] font-mono text-slate-500">
                      ↑
                    </div>
                    <div className="px-1 py-0.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded shadow-sm text-[8px] font-mono text-slate-500">
                      ↓
                    </div>
                  </div>
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">
                    选择
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="px-1 py-0.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded shadow-sm text-[8px] font-mono text-slate-500">
                    ENTER
                  </div>
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">
                    确认
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-primary-500">
                <Zap size={12} className="animate-pulse" />
                <span className="text-[9px] font-mono uppercase tracking-widest">
                  ResinDB Command Center
                </span>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
