import React, { useMemo, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  X,
  ChevronRight,
  Layers,
  Factory,
  LayoutGrid,
  Globe,
  Info,
  BookOpen,
  ExternalLink,
  FileText,
  ShieldCheck,
  Link2,
  Activity,
  Flame,
  Zap,
  TestTube,
  Box,
  FlaskConical,
  Hash,
  Radar,
  Sparkles,
  Download,
  Loader2,
  History,
  User,
  Brain,
  AlertTriangle,
} from "lucide-react";
import { Product, Category, PropertyValue } from '@/types/index';
import {
  CATEGORY_TREE,
  MANUFACTURERS,
  REFERENCES,
  PROPERTY_GROUPS,
} from '@/config/constants';
import { RADAR_KEYS, RADAR_DEFAULT_MAX } from '@/utils/productUtils';
import { useLanguage } from "@/contexts/LanguageContext";
import { logger } from "@/lib/logger";
import * as echarts from "@/lib/echarts";
import Markdown from "react-markdown";
import { findSimilarProducts, parseFiniteNumericValue } from "@/services/mathUtils";
import { SimilarProductsRadar } from '@/components/charts/SimilarProductsRadar';
import { DegradationSimulator } from '@/components/charts/DegradationSimulator';

interface ProductDetailDrawerProps {
  isOpen: boolean;
  product: Product | null;
  allProducts?: Product[];
  onClose: () => void;
  onCategoryClick: (id: string) => void;
  onProductClick?: (product: Product) => void;
  onAddToast?: (type: "success" | "info" | "error", message: string) => void;
}

type DetailTab = "overview" | "history" | "similar" | "ai";

import { PdfReportTemplate } from '@/components/features/Export/PdfReportTemplate';

export const ProductDetailDrawer: React.FC<ProductDetailDrawerProps> = React.memo(({
  isOpen,
  product,
  allProducts = [],
  onClose,
  onCategoryClick,
  onProductClick,
  onAddToast,
}) => {
  const { t, tProp, language } = useLanguage();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const pdfTemplateRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [aiInsight, setAiInsight] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const cachedProduct = useRef<Product | null>(null);
  if (product) {
    cachedProduct.current = product;
  }
  const displayProduct = product || cachedProduct.current;

  useEffect(() => {
    // Reset AI insight when product changes
    setAiInsight(null);
    setAiError(null);
    setActiveTab("overview");
  }, [product?.id]);

  useEffect(() => {
    const fetchAiInsight = async () => {
      if (!displayProduct) return;
      setIsAiLoading(true);
      setAiError(null);
      try {
        const { getAiInsights } = await import("@/services/aiService");
        const result = await getAiInsights(
          [displayProduct],
          `Provide a technical deep-dive into this specific material. Discuss its unique property balance and suggest the most challenging automotive or electrical application it would excel in.`,
        );
        setAiInsight(result || null);
      } catch {
        setAiError("AI insights unavailable. Connection error.");
      } finally {
        setIsAiLoading(false);
      }
    };

    if (activeTab === "ai" && !aiInsight && !aiError && !isAiLoading) {
      fetchAiInsight();
    }
  }, [activeTab, displayProduct, aiInsight, aiError, isAiLoading]);

  // Build a flat map of categories for easy name lookup
  const flatCategoryMap = useMemo(() => {
    const map = new Map<string, Category>();
    const traverse = (cats: Category[]) => {
      cats.forEach((c) => {
        map.set(c.id, c);
        if (c.children) traverse(c.children);
      });
    };
    traverse(CATEGORY_TREE);
    return map;
  }, []);

  const manufacturer = useMemo(
    () => MANUFACTURERS.find((m) => m.id === displayProduct?.manufacturerId),
    [displayProduct],
  );

  const relevantRefs = useMemo(() => {
    if (!displayProduct) return [];
    const refIds = new Set(
      (Object.values(displayProduct.properties) as PropertyValue[])
        .map((p) => p.referenceId)
        .filter(Boolean),
    );
    return REFERENCES.filter((r) => refIds.has(r.id as string));
  }, [displayProduct]);

  const allPaths = useMemo(() => {
    if (!displayProduct) return [];
    const paths: { segments: string[]; leafId: string }[] = [];

    const findPaths = (
      nodes: Category[],
      targetId: string,
      currentPath: string[],
    ) => {
      for (const node of nodes) {
        const nodeName =
          language === "en" && node.nameEn ? node.nameEn : node.name;
        const newPath = [...currentPath, nodeName];
        if (node.id === targetId) {
          paths.push({ segments: newPath, leafId: node.id });
        }
        if (node.children) findPaths(node.children, targetId, newPath);
      }
    };

    displayProduct.categoryIds.forEach((id) =>
      findPaths(CATEGORY_TREE, id, []),
    );
    return paths;
  }, [displayProduct, language]);

  const groupedProperties: Record<string, [string, PropertyValue][]> =
    useMemo(() => {
      const defaultGroups: Record<string, [string, PropertyValue][]> = {};
      if (!displayProduct) return defaultGroups;

      const groups: Record<string, [string, PropertyValue][]> = {
        Other: []
      };

      // Initialize groups from PROPERTY_GROUPS
      Object.keys(PROPERTY_GROUPS).forEach(key => {
        groups[key] = [];
      });

      Object.entries(displayProduct.properties).forEach(([key, val]) => {
        let found = false;
        for (const groupName in PROPERTY_GROUPS) {
          if (
            PROPERTY_GROUPS[groupName].some((k) => key.includes(k) || k === key)
          ) {
            groups[groupName].push([key, val as PropertyValue]);
            found = true;
            break;
          }
        }
        if (!found) groups["Other"].push([key, val as PropertyValue]);
      });

      return groups;
    }, [displayProduct]);

  // Similarity Engine
  const similarProducts = useMemo(() => {
    if (!displayProduct || allProducts.length <= 1) return [];

    return findSimilarProducts(
      displayProduct,
      allProducts,
      (candidate, key) => parseFiniteNumericValue(candidate.properties[key]?.value),
    ).slice(0, 3);
  }, [displayProduct, allProducts]);

  // Mini Radar Chart Effect
  useEffect(() => {
    if (!displayProduct || !chartRef.current || !isOpen) return;

    if (!chartInstance.current) {
      chartInstance.current =
        echarts.getInstanceByDom(chartRef.current) ||
        echarts.init(chartRef.current);
    }

    // Filter RADAR_KEYS to only include properties that exist on this product
    let availableProps = RADAR_KEYS.filter(
      (p) => displayProduct.properties?.[p] !== undefined,
    );

    if (availableProps.length < 3) {
      const numericProps = Object.keys(displayProduct.properties).filter(
        (k) => {
          const val = displayProduct.properties?.[k]?.value;
          return typeof val === "number" || !isNaN(parseFloat(String(val)));
        },
      );
      availableProps = numericProps.slice(0, 5);
    }

    const props = availableProps.length >= 3 ? availableProps : RADAR_KEYS;

    const values = props.map((p) => {
      const v = displayProduct.properties?.[p]?.value;
      return typeof v === "number" ? v : parseFloat(String(v)) || 0;
    });

    const indicator = props.map((p, i) => {
      const defaultMax = RADAR_DEFAULT_MAX[p] || 100;
      return {
        name: tProp(p).slice(0, 6),
        max: Math.max(values[i] * 1.1, defaultMax),
      };
    });

    const option = {
      radar: {
        indicator: indicator,
        radius: "65%",
        center: ["50%", "50%"],
        splitNumber: 3,
        axisName: { color: "#94a3b8", fontSize: 9, fontWeight: "bold" },
        splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.2)" } },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.2)" } },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: values,
              areaStyle: { color: "rgba(16, 185, 129, 0.2)" },
              lineStyle: { color: "#10b981", width: 2 },
              symbol: "none",
            },
          ],
        },
      ],
    };

    chartInstance.current.setOption(option);

    const ro = new ResizeObserver(() => { if (chartInstance.current) chartInstance.current.resize(); });
    if (chartRef.current) ro.observe(chartRef.current);
    return () => ro.disconnect();
  }, [displayProduct, tProp, isOpen]);

  // Dispose chart only when component unmounts
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  const [isExporting, setIsExporting] = useState(false);
  const drawerContentRef = useRef<HTMLDivElement>(null);

  const handleExportPDF = async () => {
    if (!pdfTemplateRef.current || !displayProduct) return;
    setIsExporting(true);

    try {
      // Dynamic async imports explicitly block the chunking compiler from rolling it into index or vendor packages
      const [html2canvasModule, jsPDFModule] = await Promise.all([
        import("html2canvas"),
        import("jspdf"),
      ]);
      const html2canvas = html2canvasModule.default;
      const jsPDF = jsPDFModule.jsPDF;

      const canvas = await html2canvas(pdfTemplateRef.current, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: "#ffffff",
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "pt",
        format: "a4",
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
      const safeGradeName = displayProduct.gradeName.replace(/[^a-z0-9]/gi, "_").toLowerCase();
      pdf.save(`ResinDB_Report_${safeGradeName}.pdf`);
    } catch (error) {
      logger.error("Failed to generate PDF", error);
      if (onAddToast) {
        onAddToast("error", t("exportFailed") || "导出失败，请重试");
      } else {
        logger.error(
          "Export failed:",
          t("exportFailed") || "导出失败，请重试",
        );
      }
    } finally {
      setIsExporting(false);
    }
  };

  if ((!displayProduct && !isOpen) || !displayProduct) return null;

  const getGroupIcon = (name: string) => {
    switch (name) {
      case "Mechanical":
        return <Activity size={16} className="text-blue-500" />;
      case "Thermal":
        return <Flame size={16} className="text-orange-500" />;
      case "Optical/Electrical":
        return <Zap size={16} className="text-yellow-500" />;
      case "Chemical":
        return <TestTube size={16} className="text-purple-500" />;
      case "General":
        return <Box size={16} className="text-emerald-500" />;
      default:
        return <LayoutGrid size={16} className="text-slate-400" />;
    }
  };

  const getGroupName = (name: string) => {
    const key = `group_${name.replace("/", "").replace(" ", "")}`;
    return t(key as Parameters<typeof t>[0]) || name;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="product-drawer-overlay-container"
          className="fixed inset-0 z-[50] pointer-events-none flex"
        >
          <motion.div
            key="product-drawer-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/20 backdrop-blur-sm pointer-events-auto"
            onClick={onClose}
          />
          <motion.div
            key="product-drawer-panel"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute inset-y-0 right-0 w-full sm:w-[500px] md:w-[640px] xl:w-[720px] bg-white dark:bg-slate-950 flex flex-col pointer-events-auto shadow-2xl border-l border-slate-300 dark:border-slate-700"
          >
            {/* Header */}
            <div className="relative h-32 md:h-48 shrink-0 overflow-hidden group">
              <div className="absolute inset-0 bg-slate-900 dark:bg-slate-950" />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent" />

              <div className="absolute top-4 md:top-6 left-4 md:left-6 right-4 md:right-6 flex justify-between items-start z-10">
                <div className="p-1.5 md:p-2 bg-primary-600 text-white border border-primary-700 rounded-lg md:rounded-xl">
                  <Layers size={20} />
                </div>
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{
                      scale: 1.05,
                      backgroundColor: "rgba(16, 185, 129, 0.9)",
                    }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleExportPDF}
                    disabled={isExporting}
                    aria-label="Export to PDF"
                    className="flex items-center gap-2 px-3 md:px-4 py-1.5 md:py-2 bg-white/10 backdrop-blur-md border border-white/20 text-white transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-emerald-500 text-[10px] font-mono font-bold uppercase tracking-widest disabled:opacity-50"
                  >
                    {isExporting ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Download size={12} />
                    )}
                    <span className="hidden sm:inline">PDF</span>
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.1, rotate: 90 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={onClose}
                    aria-label="Close details"
                    className="p-1.5 md:p-2 bg-white/10 backdrop-blur-md border border-white/20 hover:bg-rose-600 hover:border-rose-600 text-white transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500"
                  >
                    <X size={18} />
                  </motion.button>
                </div>
              </div>

              <div className="absolute bottom-3 md:bottom-6 left-4 md:left-6 right-4 md:right-6 z-10">
                <div className="flex flex-wrap gap-1.5 md:gap-2 mb-1.5 md:mb-3">
                  {displayProduct.categoryIds.map((catId) => {
                    const cat = flatCategoryMap.get(catId);
                    const catName =
                      language === "en" && cat?.nameEn
                        ? cat.nameEn
                        : cat?.name || "Category";
                    return (
                      <motion.button
                        key={catId}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onCategoryClick?.(catId);
                        }}
                        className="px-2 py-0.5 bg-primary-600/20 hover:bg-primary-600/40 text-primary-400 text-[9px] font-mono font-bold uppercase tracking-widest border border-primary-600/30 transition-colors"
                      >
                        {catName}
                      </motion.button>
                    );
                  })}
                </div>
                <h2 className="text-2xl font-display font-bold text-white tracking-tight leading-tight mb-1">
                  {displayProduct.gradeName}
                </h2>
                <div className="flex items-center gap-3 text-slate-400">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-widest">
                    <Factory size={12} className="text-primary-500" />
                    {displayProduct.manufacturer}
                  </div>
                  <div className="w-1 h-1 bg-slate-700 rounded-full" />
                  <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-widest">
                    <Globe size={12} className="text-primary-500" />
                    {manufacturer?.country || "Global"}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar bg-white dark:bg-slate-950">
              <div className="px-3 md:px-6 bg-white dark:bg-slate-950 border-b border-slate-300 dark:border-slate-700 sticky top-0 z-20 flex items-center justify-between md:justify-start md:gap-8 shrink-0 overflow-x-auto no-scrollbar">
                {[
                  { id: "overview", label: t("overview"), icon: Info },
                  { id: "history", label: t("history"), icon: History },
                  { id: "similar", label: t("similar"), icon: Sparkles },
                  { id: "ai", label: "AI", icon: Brain },
                ].map((tab) => (
                  <motion.button
                    key={tab.id}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setActiveTab(tab.id as DetailTab)}
                    className={`flex items-center gap-1.5 md:gap-2 py-3 md:py-4 text-[9px] md:text-[10px] font-mono font-bold uppercase tracking-[0.1em] md:tracking-widest transition-all relative shrink-0 ${activeTab === tab.id ? "text-primary-600 dark:text-primary-400" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"}`}
                  >
                    <tab.icon size={12} />
                    {tab.label}
                    {activeTab === tab.id && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600"
                      />
                    )}
                  </motion.button>
                ))}
              </div>

              <div
                ref={drawerContentRef}
                className="p-4 md:p-6 space-y-6 min-h-[400px]"
              >
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                  >
                    {activeTab === "ai" && (
                      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <div className="p-5 md:p-8 rounded-2xl md:rounded-[2.5rem] bg-gradient-to-br from-primary-500/5 to-indigo-500/5 border border-primary-500/10 relative overflow-hidden">
                          <div className="absolute top-0 right-0 w-32 h-32 bg-primary-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
                          <div className="relative z-10 flex flex-col items-center text-center space-y-4">
                            <div className="p-4 bg-white dark:bg-slate-900 rounded-[2rem] shadow-xl border border-primary-500/20">
                              <Brain
                                size={40}
                                className="text-primary-500 transition-all hover:scale-110"
                              />
                            </div>
                            <div>
                              <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
                                Intelligence Report
                              </h3>
                              <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mt-1">
                                Generated by ResinAI System
                              </p>
                            </div>
                          </div>

                          <div className="mt-8 space-y-4">
                            {isAiLoading ? (
                              <div className="flex flex-col items-center gap-4 py-12">
                                <Loader2
                                  size={32}
                                  className="animate-spin text-primary-500"
                                />
                                <p className="text-xs font-black text-slate-400 uppercase tracking-widest animate-pulse">
                                  Scanning Molecular Properties...
                                </p>
                              </div>
                            ) : aiError ? (
                              <div className="p-6 bg-rose-50 dark:bg-rose-900/10 border border-rose-100 dark:border-rose-900/20 rounded-[2rem] text-center">
                                <AlertTriangle
                                  size={32}
                                  className="text-rose-500 mx-auto mb-3"
                                />
                                <p className="text-sm font-bold text-rose-600 dark:text-rose-400">
                                  {aiError}
                                </p>
                                <motion.button
                                  whileHover={{ scale: 1.05 }}
                                  whileTap={{ scale: 0.95 }}
                                  onClick={() => {
                                    setAiInsight(null);
                                    setAiError(null);
                                    setActiveTab("overview");
                                    setTimeout(() => setActiveTab("ai"), 50);
                                  }}
                                  className="mt-4 px-6 py-2 bg-rose-500 text-white rounded-xl text-xs font-black uppercase tracking-widest"
                                >
                                  Retry Analysis
                                </motion.button>
                              </div>
                            ) : (
                              <div className="p-6 bg-white dark:bg-slate-950/50 rounded-[2rem] border border-white dark:border-slate-800 shadow-sm markdown-body prose prose-slate dark:prose-invert max-w-none">
                                <Markdown
                                  components={{
                                    p: ({ children }) => (
                                      <p className="mb-4 last:mb-0 text-sm leading-relaxed">
                                        {children}
                                      </p>
                                    ),
                                    strong: ({ children }) => (
                                      <strong className="font-black text-primary-500">
                                        {children}
                                      </strong>
                                    ),
                                  }}
                                >
                                  {aiInsight || "No insight generated."}
                                </Markdown>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    {activeTab === "overview" && (
                      <div className="space-y-6">
                        {/* Manufacturer & Radar Card Row */}
                        <div className="flex flex-col sm:flex-row gap-4">
                          {manufacturer && (
                            <div className="flex-1 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 p-5 relative overflow-hidden group shadow-sm">
                              <div className="relative z-10 h-full flex flex-col justify-between">
                                <div>
                                  <div className="flex items-center gap-3 mb-3">
                                    <div className="p-2 bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-200 dark:border-primary-800/50">
                                      <Factory size={18} />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                      <h4
                                        className="text-sm font-display font-bold text-slate-900 dark:text-white truncate tracking-tight"
                                        title={manufacturer.name}
                                      >
                                        {manufacturer.name}
                                      </h4>
                                      <div className="flex items-center gap-1.5 mt-0.5">
                                        <ShieldCheck
                                          size={10}
                                          className="text-emerald-500 shrink-0"
                                        />
                                        <span className="text-[9px] font-mono font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest truncate">
                                          {t("verifiedManufacturer")}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                  <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 leading-relaxed mb-4 line-clamp-2">
                                    {manufacturer.description}
                                  </p>
                                </div>
                                {manufacturer.website && (
                                  <motion.a
                                    whileHover={{
                                      scale: 1.05,
                                      x: 4,
                                      backgroundColor: "rgba(15, 23, 42, 1)",
                                      color: "#fff",
                                    }}
                                    whileTap={{ scale: 0.95 }}
                                    href={
                                      manufacturer.website.startsWith("http")
                                        ? manufacturer.website
                                        : `https://${manufacturer.website}`
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[9px] font-mono font-bold uppercase tracking-widest transition-all w-fit rounded-lg shadow-md"
                                  >
                                    <Globe size={12} /> {t("officialWebsite")}
                                  </motion.a>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Visual Radar */}
                          <div className="w-full sm:w-48 h-48 bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 p-2 relative flex flex-col items-center justify-center shrink-0 rounded-2xl shadow-inner">
                            <div className="absolute top-3 left-3 flex items-center gap-1.5 text-[8px] font-mono font-bold text-slate-400 uppercase tracking-widest z-10">
                              <Radar size={10} className="text-emerald-500" />{" "}
                              Fingerprint
                            </div>
                            <div ref={chartRef} className="w-full h-full" />
                          </div>
                        </div>

                        {/* Multi-path Classification */}
                        <section className="space-y-2">
                          <div className="flex items-center gap-2 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                            <Link2 size={10} className="text-primary-500" />
                            {t("taxonomyPaths")}
                          </div>
                          <div className="space-y-1">
                            {allPaths.map((path, idx) => (
                              <motion.button
                                key={idx}
                                whileHover={{ x: 8, scale: 1.01 }}
                                whileTap={{ scale: 0.99 }}
                                onClick={() => onCategoryClick(path.leafId)}
                                className="w-full text-left flex items-center p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-xl shadow-sm hover:shadow-md"
                              >
                                <div className="flex flex-wrap items-center text-[10px] font-mono">
                                  {path.segments.map((segment, sIdx) => (
                                    <React.Fragment key={sIdx}>
                                      <span
                                        className={`transition-colors uppercase tracking-tight ${sIdx === path.segments.length - 1 ? "font-bold text-slate-800 dark:text-white" : "text-slate-500 dark:text-slate-400"}`}
                                      >
                                        {segment}
                                      </span>
                                      {sIdx < path.segments.length - 1 && (
                                        <ChevronRight
                                          size={10}
                                          className="mx-1 text-slate-300"
                                        />
                                      )}
                                    </React.Fragment>
                                  ))}
                                </div>
                              </motion.button>
                            ))}
                          </div>
                        </section>

                        {/* Property Groups */}
                        <div className="space-y-6">
                          {Object.entries(groupedProperties).map(
                            ([groupName, items], _groupIdx) => {
                              if (items.length === 0) return null;
                              return (
                                <section key={groupName} className="space-y-3">
                                  <div className="flex items-center gap-2 mb-2 pb-1 border-b border-slate-300 dark:border-slate-700">
                                    {getGroupIcon(groupName)}
                                    <h4 className="text-[10px] font-mono font-bold text-slate-800 dark:text-white uppercase tracking-widest">
                                      {getGroupName(groupName)}
                                    </h4>
                                  </div>
                                  <div className="grid grid-cols-1 gap-2">
                                    {items.map(([key, prop]) => (
                                      <motion.div
                                        key={key}
                                        whileHover={{ scale: 1.01, x: 2 }}
                                        whileTap={{ scale: 0.99 }}
                                        className="flex flex-col p-4 bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 transition-all group rounded-2xl shadow-sm hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-md cursor-pointer"
                                      >
                                        <div className="flex justify-between items-start mb-3">
                                          <div className="flex-1 min-w-0">
                                            <span
                                              className="text-[10px] font-mono font-bold text-slate-800 dark:text-slate-100 block mb-2 truncate uppercase tracking-tight"
                                              title={tProp(key)}
                                            >
                                              {tProp(key)}
                                            </span>

                                            {/* Context Tags */}
                                            <div className="flex flex-wrap gap-1.5">
                                              {prop.standard && (
                                                <span
                                                  className="text-[8px] font-mono font-bold text-slate-500 bg-white dark:bg-slate-950 px-2 py-0.5 border border-slate-200 dark:border-slate-800 flex items-center gap-1.5 truncate max-w-[120px] rounded-md shadow-sm"
                                                  title={prop.standard}
                                                >
                                                  <FileText
                                                    size={8}
                                                    className="shrink-0 text-slate-400"
                                                  />{" "}
                                                  <span className="truncate">
                                                    {prop.standard}
                                                  </span>
                                                </span>
                                              )}
                                              {prop.temperature && (
                                                <span className="text-[8px] font-mono font-bold text-slate-500 bg-white dark:bg-slate-950 px-2 py-0.5 border border-slate-200 dark:border-slate-800 flex items-center gap-1.5 rounded-md shadow-sm">
                                                  <Flame
                                                    size={8}
                                                    className="text-orange-400"
                                                  />{" "}
                                                  {prop.temperature}
                                                </span>
                                              )}
                                              {prop.referenceId && (
                                                <span
                                                  className="text-[8px] font-mono font-bold text-slate-500 bg-white dark:bg-slate-950 px-2 py-0.5 border border-slate-200 dark:border-slate-800 flex items-center gap-1.5 rounded-md shadow-sm"
                                                  title={t("referenceId")}
                                                >
                                                  <Hash
                                                    size={8}
                                                    className="text-blue-400"
                                                  />{" "}
                                                  {prop.referenceId}
                                                </span>
                                              )}
                                            </div>
                                          </div>

                                          {/* Value Display - Inline Units */}
                                          <div className="text-right pl-4">
                                            <div className="flex items-baseline justify-end gap-1">
                                              <span className="font-mono font-bold text-base text-slate-900 dark:text-white leading-none tracking-tighter group-hover:text-primary-600 transition-colors">
                                                {prop.value}
                                              </span>
                                              {prop.unit && (
                                                <span className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                                                  {prop.unit}
                                                </span>
                                              )}
                                            </div>
                                          </div>
                                        </div>

                                        {/* Equipment & Source Link */}
                                        {(prop.instrument ||
                                          prop.sourceUrl) && (
                                          <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
                                            {prop.instrument && (
                                              <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-500 dark:text-slate-400">
                                                <FlaskConical
                                                  size={8}
                                                  className="text-emerald-500"
                                                />
                                                <span className="font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-500 text-[8px]">
                                                  {t("sourceEquipment")}:
                                                </span>
                                                <span className="font-bold">
                                                  {prop.instrument}
                                                </span>
                                              </div>
                                            )}
                                            {prop.sourceUrl && (
                                              <a
                                                href={
                                                  prop.sourceUrl.startsWith(
                                                    "http",
                                                  )
                                                    ? prop.sourceUrl
                                                    : `https://${prop.sourceUrl}`
                                                }
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1 text-[8px] font-mono font-bold text-primary-600 dark:text-primary-400 hover:text-primary-700 uppercase tracking-widest transition-colors ml-auto"
                                              >
                                                <ExternalLink size={8} />{" "}
                                                {t("sourceUrl")}
                                              </a>
                                            )}
                                          </div>
                                        )}
                                      </motion.div>
                                    ))}
                                  </div>
                                </section>
                              );
                            },
                          )}
                        </div>

                        {/* Temporal Degradation Simulator */}
                        <DegradationSimulator product={displayProduct} />

                        {/* Similar Grades */}
                        {similarProducts.length > 0 && (
                          <section className="space-y-3 pt-4 border-t border-slate-300 dark:border-slate-700">
                            <div className="flex items-center gap-2 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                              <Sparkles
                                size={10}
                                className="text-secondary-500"
                              />
                              相似牌号推荐 (Similar Grades)
                            </div>
                            <div className="grid grid-cols-1 gap-2">
                              {similarProducts.map(
                                ({
                                  product: p,
                                  score: similarity,
                                  sharedFeatureCount,
                                  targetFeatureCount,
                                }) => (
                                  <motion.button
                                    key={p.id}
                                    whileHover={{ scale: 1.02, x: 4 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => onProductClick?.(p)}
                                    className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm transition-all hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-md cursor-pointer group"
                                  >
                                    <div className="flex items-center gap-3">
                                      <div className="w-8 h-8 rounded-xl bg-indigo-100 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/50 flex items-center justify-center">
                                        <Layers size={14} />
                                      </div>
                                      <div className="min-w-0 flex-1">
                                        <p
                                          className="text-[11px] font-mono font-bold text-slate-900 dark:text-white mb-0.5 truncate uppercase tracking-tight"
                                          title={p.gradeName}
                                        >
                                          {p.gradeName}
                                        </p>
                                        <p
                                          className="text-[9px] font-mono text-slate-500 dark:text-slate-400 font-bold flex items-center gap-1.5 truncate uppercase tracking-widest"
                                          title={p.manufacturer}
                                        >
                                          <Factory
                                            size={10}
                                            className="shrink-0 text-slate-400"
                                          />{" "}
                                          <span className="truncate">
                                            {p.manufacturer}
                                          </span>
                                        </p>
                                      </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                      <div className="text-[9px] font-mono font-bold text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-0.5 rounded-md border border-indigo-200 dark:border-indigo-800/50 uppercase tracking-widest shadow-sm">
                                        {similarity}% Match
                                      </div>
                                      <div className="mt-1 text-[8px] font-mono text-slate-400">
                                        {sharedFeatureCount}/{targetFeatureCount} shared features
                                      </div>
                                    </div>
                                  </motion.button>
                                ),
                              )}
                            </div>
                          </section>
                        )}

                        {/* References */}
                        {relevantRefs.length > 0 && (
                          <section className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                            <div className="flex items-center gap-2 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                              <BookOpen
                                size={10}
                                className="text-emerald-500"
                              />
                              {t("referenceDocs")}
                            </div>
                            <div className="grid grid-cols-1 gap-2">
                              {relevantRefs.map((ref) => (
                                <motion.button
                                  key={ref.id}
                                  whileHover={{
                                    scale: 1.02,
                                    x: 4,
                                    backgroundColor: "rgba(248, 250, 252, 1)",
                                  }}
                                  whileTap={{ scale: 0.98 }}
                                  className="w-full text-left flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm transition-all group hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                                >
                                  <div className="p-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500 group-hover:text-emerald-600 transition-colors shadow-sm">
                                    <FileText size={14} />
                                  </div>
                                  <div>
                                    <p className="text-[10px] font-mono font-bold text-slate-800 dark:text-white mb-0.5">
                                      {ref.name}
                                    </p>
                                    <p className="text-[9px] font-mono text-slate-400 font-bold uppercase tracking-widest">
                                      {ref.author} • {ref.year}
                                    </p>
                                  </div>
                                </motion.button>
                              ))}
                            </div>
                          </section>
                        )}
                      </div>
                    )}

                    {activeTab === "history" && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-[10px] font-mono font-bold text-slate-800 dark:text-white uppercase tracking-widest flex items-center gap-2">
                            <History size={14} className="text-primary-500" />
                            数据审计日志
                          </h4>
                          <span className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                            共 4 条记录
                          </span>
                        </div>
                        <div className="space-y-2">
                          {[
                            {
                              user: "resj666@gmail.com",
                              action: "更新了“密度”属性",
                              time: "2026-04-02 14:20",
                              type: "update",
                            },
                            {
                              user: "system@resindb.com",
                              action: "同步了“熔体质量流动速率”",
                              time: "2026-03-28 09:15",
                              type: "sync",
                            },
                            {
                              user: "admin@resindb.com",
                              action: "审核并通过了该牌号",
                              time: "2026-03-25 16:40",
                              type: "audit",
                            },
                            {
                              user: "resj666@gmail.com",
                              action: "创建了该牌号记录",
                              time: "2026-03-25 10:00",
                              type: "create",
                            },
                          ].map((item, i) => (
                            <div
                              key={i}
                              className="flex gap-3 p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm transition-all"
                            >
                              <div className="shrink-0">
                                <div
                                  className={`w-8 h-8 rounded-xl border flex items-center justify-center shadow-sm ${item.type === "update" ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800/50" : item.type === "sync" ? "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800/50" : item.type === "audit" ? "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800/50" : "bg-white text-slate-600 border-slate-200 dark:bg-slate-800 dark:border-slate-700"}`}
                                >
                                  <User size={14} />
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1 gap-2">
                                  <span
                                    className="text-[10px] font-mono font-bold text-slate-800 dark:text-white truncate tracking-tight"
                                    title={item.user}
                                  >
                                    {item.user}
                                  </span>
                                  <span className="text-[9px] font-mono font-bold text-slate-400 shrink-0 uppercase tracking-widest">
                                    {item.time}
                                  </span>
                                </div>
                                <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                                  {item.action}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {activeTab === "similar" && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-[10px] font-mono font-bold text-slate-800 dark:text-white uppercase tracking-widest flex items-center gap-2">
                            <Sparkles size={14} className="text-primary-500" />
                            推荐相似牌号
                          </h4>
                        </div>

                        <div className="mb-6">
                           <SimilarProductsRadar
                              targetProduct={displayProduct}
                              similarProducts={similarProducts}
                              allProducts={allProducts}
                           />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {similarProducts.map(({
                            product: p,
                            score: similarity,
                            sharedFeatureCount,
                            targetFeatureCount,
                          }) => (
                            <motion.button
                              whileHover={{
                                scale: 1.02,
                                backgroundColor: "rgba(248, 250, 252, 1)",
                              }}
                              whileTap={{ scale: 0.98 }}
                              key={p.id}
                              onClick={() => onProductClick?.(p)}
                              className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 text-left transition-all group flex flex-col h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                            >
                              <div className="flex items-start justify-between mb-2 gap-2">
                                <span className="text-[11px] font-mono font-bold text-slate-900 dark:text-white group-hover:text-primary-600 transition-colors tracking-tight line-clamp-2 uppercase">
                                  {p.gradeName}
                                </span>
                                <div className="text-right shrink-0">
                                  <span className="text-[9px] font-mono font-bold text-emerald-600 dark:text-emerald-400 bg-white dark:bg-slate-950 border border-emerald-200 dark:border-emerald-800/50 px-1.5 py-0.5 rounded-md shadow-sm uppercase tracking-widest">
                                    {similarity}%
                                  </span>
                                  <p className="mt-1 text-[8px] font-mono text-slate-400">
                                    {sharedFeatureCount}/{targetFeatureCount} dimensions
                                  </p>
                                </div>
                              </div>
                              <p className="text-[9px] font-mono text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest mb-3 flex items-center gap-1.5">
                                <Factory size={10} className="text-slate-400" />
                                {p.manufacturer}
                              </p>
                              <div className="flex flex-wrap gap-1 mt-auto">
                                {p.categoryIds.slice(0, 2).map((catId) => {
                                  const cat = flatCategoryMap.get(catId);
                                  const name =
                                    language === "en" && cat?.nameEn
                                      ? cat.nameEn
                                      : cat?.name || catId;
                                  return (
                                    <span
                                      key={catId}
                                      className="text-[8px] font-mono font-bold text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-1.5 py-0.5 rounded-md shadow-sm uppercase tracking-widest"
                                    >
                                      {name}
                                    </span>
                                  );
                                })}
                              </div>
                            </motion.button>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-300 dark:border-slate-700">
              <div className="flex justify-center items-center gap-2 text-[9px] font-mono text-slate-500 uppercase tracking-widest">
                <ShieldCheck size={12} className="text-emerald-500" />
                <span>
                  Data verified against PetroChina Standards Database.
                </span>
              </div>
            </div>

            <PdfReportTemplate ref={pdfTemplateRef} product={displayProduct} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
