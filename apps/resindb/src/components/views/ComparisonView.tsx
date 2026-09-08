import React, { useMemo, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  X,
  Radar,
  Factory,
  Layers,
  Info,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Target,
} from "lucide-react";
import { Product } from '@/types/index';
import { UniversalStorageBridge } from "@/lib/adapters/UniversalStorageBridge";
import { PROPERTY_GROUPS } from '@/config/constants';
import { RADAR_KEYS, isLowBest } from '@/utils/productUtils';
import { useLanguage } from "@/contexts/LanguageContext";
import { useTheme } from "@/contexts/ThemeContext";
import * as echarts from "@/lib/echarts";
import { summarizeFinite } from '@/lib/numericAggregation';

const KEY_SPECS = [
  "CAS Number",
  "CAS号",
  "Chemical Name",
  "化学名称",
  "典型应用",
  "应用",
  "Applications",
];

interface ComparisonViewProps {
  isOpen: boolean;
  products: Product[];
  allProducts?: Product[];
  onClose: () => void;
  onRemoveProduct: (id: string) => void;
  onAddProduct?: (id: string) => void;
}

export const ComparisonView: React.FC<ComparisonViewProps> = React.memo(({
  isOpen,
  products,
  allProducts = [],
  onClose,
  onRemoveProduct,
  onAddProduct,
}) => {
  const { t, tProp } = useLanguage();
  const { theme } = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [baselineId, setBaselineId] = useState<string | null>(null);

  const [cachedProducts, setCachedProducts] = useState<Product[]>([]);
  useEffect(() => {
    if (products.length > 0) {
      setCachedProducts(products);
    }
  }, [products]);
  const displayProducts = products.length > 0 ? products : cachedProducts;

  // Pre-calculate best values for each property
  const bestValuesMap = useMemo(() => {
    const map: Record<string, number> = {};
    const allPropKeys = new Set<string>();
    displayProducts.forEach((p) =>
      Object.keys(p.properties).forEach((k) => allPropKeys.add(k)),
    );

    allPropKeys.forEach((key) => {
      const summary = summarizeFinite(displayProducts, (product) => {
        const value = product.properties[key]?.value;
        return typeof value === "number" ? value : parseFloat(String(value));
      });

      if (summary && summary.count > 1) {
        map[key] = isLowBest(key) ? summary.minimum : summary.maximum;
      }
    });
    return map;
  }, [displayProducts]);

  const baselineProduct = useMemo(
    () => displayProducts.find((p) => p.id === baselineId),
    [displayProducts, baselineId],
  );

  // Find experimental and standard products for side-by-side diagnostic benchmark
  const diagnosticReport = useMemo(() => {
    const expProducts = displayProducts.filter(p => p.isExperimental);
    // Standard product is baselineProduct if selected (and not experimental),
    // otherwise the first non-experimental product
    const stdProduct = baselineProduct && !baselineProduct.isExperimental
      ? baselineProduct
      : displayProducts.find(p => !p.isExperimental);

    if (expProducts.length === 0 || !stdProduct) return null;

    // We do reporting for the first experimental product
    const expProduct = expProducts[0];

    const targetProps = ["密度", "熔体质量流动速率", "拉伸屈服应力", "弯曲模量"];
    const deviations: {
      propKey: string;
      expName: string;
      stdName: string;
      expVal: number | string;
      stdVal: number | string;
      diffPercent: number | null;
      status: "consistent" | "warning" | "danger" | "unknown";
      unit: string;
    }[] = [];

    let totalScoreDeduction = 0;
    let scoredPropsCount = 0;

    targetProps.forEach(propKey => {
      const expProp = expProduct.properties[propKey] || expProduct.properties[Object.keys(expProduct.properties).find(k => k.includes(propKey)) || ""];
      const stdProp = stdProduct.properties[propKey] || stdProduct.properties[Object.keys(stdProduct.properties).find(k => k.includes(propKey)) || ""];

      const expVal = expProp ? Number(expProp.value) : NaN;
      const stdVal = stdProp ? Number(stdProp.value) : NaN;
      const unit = expProp?.unit || stdProp?.unit || "";

      if (!isNaN(expVal) && !isNaN(stdVal) && stdVal !== 0) {
        const diff = ((expVal - stdVal) / stdVal) * 100;
        const absDiff = Math.abs(diff);

        let status: "consistent" | "warning" | "danger" = "consistent";
        if (absDiff > 15) {
          status = "danger";
        } else if (absDiff > 5) {
          status = "warning";
        }

        deviations.push({
          propKey,
          expName: expProduct.gradeName,
          stdName: stdProduct.gradeName,
          expVal: expProp.value,
          stdVal: stdProp.value,
          diffPercent: diff,
          status,
          unit,
        });

        totalScoreDeduction += absDiff * 1.5;
        scoredPropsCount++;
      } else if (expProp || stdProp) {
        deviations.push({
          propKey,
          expName: expProduct.gradeName,
          stdName: stdProduct.gradeName,
          expVal: expProp?.value ?? "-",
          stdVal: stdProp?.value ?? "-",
          diffPercent: null,
          status: "unknown",
          unit,
        });
      }
    });

    const complianceScore = scoredPropsCount > 0
      ? Math.max(10, Math.min(100, Math.round(100 - totalScoreDeduction)))
      : null;

    // Generate diagnostic comments
    const suggestions: string[] = [];
    deviations.forEach(d => {
      if (d.diffPercent !== null) {
        const diff = d.diffPercent;
        if (d.propKey === "密度") {
          if (diff > 0.5) {
            suggestions.push(t("diag_density_high"));
          } else if (diff < -0.5) {
            suggestions.push(t("diag_density_low"));
          }
        }
        if (d.propKey === "熔体质量流动速率") {
          if (diff > 15) {
            suggestions.push(t("diag_mfr_high"));
          } else if (diff < -15) {
            suggestions.push(t("diag_mfr_low"));
          }
        }
        if (d.propKey === "拉伸屈服应力") {
          if (diff < -5) {
            suggestions.push(t("diag_tensile_low"));
          }
        }
        if (d.propKey === "弯曲模量") {
          if (diff < -8) {
            suggestions.push(t("diag_flexural_low"));
          }
        }
      }
    });

    if (suggestions.length === 0 && scoredPropsCount > 0) {
      suggestions.push(t("diag_perfect_fit"));
    }

    return {
      expProduct,
      stdProduct,
      deviations,
      complianceScore,
      suggestions,
    };
  }, [displayProducts, baselineProduct, t]);

  // Recommended standard products for quick alignment when only experimental are selected
  const recommendedStandards = useMemo(() => {
    const expProducts = displayProducts.filter(p => p.isExperimental);
    if (expProducts.length === 0) return [];
    
    // Check if we already have a standard reference in comparison list to avoid double recommendation
    const hasStandard = displayProducts.some(p => !p.isExperimental);
    if (hasStandard) return [];

    const expProduct = expProducts[0];
    const openRecords = UniversalStorageBridge.getOpenMarketRecords();
    const openProducts = openRecords.map(r => UniversalStorageBridge.recordToProduct(r));
    
    // Filter out already selected products
    const unselected = openProducts.filter(op => !displayProducts.some(dp => dp.id === op.id));
    
    // Match by category or grade keywords
    const expCatIds = expProduct.categoryIds || [];
    const matched = unselected.filter(op => {
      const overlap = op.categoryIds?.some(cid => expCatIds.includes(cid));
      if (overlap) return true;
      const gradeWords = expProduct.gradeName.toUpperCase().replace(/[^A-Z0-9]/g, " ").split(" ").filter(w => w.length > 1);
      return gradeWords.some(w => op.gradeName.toUpperCase().includes(w));
    });

    return matched.length > 0 ? matched : unselected.slice(0, 2);
  }, [displayProducts]);

  // Tech Blue Palette
  const colors = useMemo(
    () => ["#0284c7", "#06b6d4", "#14b8a6", "#6366f1", "#f59e0b"],
    [],
  );

  // Radar Chart Data Prep (ECharts format)
  const radarKeys = useMemo(() => {
    let availableProps = RADAR_KEYS.filter((key) =>
      displayProducts.some((p) => p.properties[key] !== undefined),
    );

    if (availableProps.length < 3) {
      const numericProps = new Set<string>();
      displayProducts.forEach((p) => {
        Object.keys(p.properties).forEach((k) => {
          const val = p.properties[k]?.value;
          if (typeof val === "number" || !isNaN(parseFloat(String(val)))) {
            numericProps.add(k);
          }
        });
      });
      availableProps = Array.from(numericProps).slice(0, 6);
    }

    return availableProps.length >= 3 ? availableProps : RADAR_KEYS;
  }, [displayProducts]);

  useEffect(() => {
    if (!chartRef.current || displayProducts.length === 0 || !isOpen) return;

    // Initialize Chart
    const chart =
      echarts.getInstanceByDom(chartRef.current) ||
      echarts.init(chartRef.current);
    chartInstance.current = chart;

    const indicator = radarKeys.map((key) => ({
      name: tProp(key),
    }));

    const seriesData = displayProducts.map((p, idx) => ({
      value: radarKeys.map((key) => {
        const val = Number(p.properties[key]?.value);
        return isNaN(val) ? 0 : val;
      }),
      name: p.gradeName,
      areaStyle: {
        opacity: 0.15,
      },
      lineStyle: {
        width: 3,
      },
      itemStyle: {
        color: colors[idx % colors.length],
      },
      symbol: "circle",
      symbolSize: 8,
    }));

    const option = {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        backgroundColor: theme === "dark" ? "#1e293b" : "#ffffff",
        borderColor: theme === "dark" ? "#334155" : "#e2e8f0",
        textStyle: { color: theme === "dark" ? "#f1f5f9" : "#0f172a" },
        padding: [10, 15],
        borderRadius: 12,
        shadowBlur: 10,
        shadowColor: "rgba(0,0,0,0.1)",
      },
      legend: {
        bottom: 0,
        data: displayProducts.map((p) => p.gradeName),
        textStyle: {
          color: theme === "dark" ? "#94a3b8" : "#475569",
          fontSize: 10,
          fontWeight: "bold",
        },
        itemGap: 20,
      },
      radar: {
        indicator: indicator,
        shape: "circle",
        splitNumber: 4,
        axisName: {
          color: theme === "dark" ? "#cbd5e1" : "#1e293b",
          fontWeight: "bold",
          fontSize: 10,
          formatter: (name: string) =>
            name.length > 8 ? name.slice(0, 8) + "..." : name,
        },
        splitLine: {
          lineStyle: {
            color:
              theme === "dark"
                ? "rgba(255, 255, 255, 0.05)"
                : "rgba(0, 0, 0, 0.05)",
          },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color:
              theme === "dark"
                ? ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.04)"]
                : ["rgba(0,0,0,0.01)", "rgba(0,0,0,0.02)"],
          },
        },
        axisLine: {
          lineStyle: {
            color:
              theme === "dark"
                ? "rgba(255, 255, 255, 0.1)"
                : "rgba(0, 0, 0, 0.1)",
          },
        },
      },
      series: [
        {
          type: "radar",
          data: seriesData,
          emphasis: {
            lineStyle: {
              width: 4,
            },
          },
        },
      ],
    };

    chart.setOption(option, true); // Use true to not merge with previous options

    const ro = new ResizeObserver(() => {
      chart.resize();
    });
    ro.observe(chartRef.current);

    return () => {
      ro.disconnect();
      chart.dispose();
      chartInstance.current = null;
    };
  }, [displayProducts, theme, tProp, isOpen, colors, radarKeys]);

  // Aggregate all unique properties from selected products
  const allProperties = useMemo(() => {
    const props = new Set<string>();
    displayProducts.forEach((p) =>
      Object.keys(p.properties).forEach((k) => props.add(k)),
    );
    return Array.from(props);
  }, [displayProducts]);

  // Group properties based on constants
  const groupedProps = useMemo(() => {
    const grouped: Record<string, string[]> = {};
    Object.keys(PROPERTY_GROUPS).forEach((g) => (grouped[g] = []));
    grouped["Other"] = [];

    allProperties.forEach((prop) => {
      if (KEY_SPECS.includes(prop)) return; // Skip key specs as they are handled separately
      let found = false;
      for (const [group, keys] of Object.entries(PROPERTY_GROUPS)) {
        if (keys.some((k) => prop.includes(k) || k === prop)) {
          grouped[group].push(prop);
          found = true;
          break;
        }
      }
      if (!found) grouped["Other"].push(prop);
    });

    return Object.entries(grouped).filter(([_, props]) => props.length > 0);
  }, [allProperties]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="comparison-overlay-container"
          className="fixed inset-0 z-[110] pointer-events-none flex flex-col"
        >
          <motion.div
            key="comparison-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/20 backdrop-blur-sm pointer-events-auto"
            onClick={onClose}
          />
          <motion.div
            key="comparison-content"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute inset-0 z-[120] bg-slate-50 dark:bg-slate-950 flex flex-col pointer-events-auto"
          >
            {/* Header */}
            <div className="px-4 md:px-6 py-3 md:py-4 bg-white dark:bg-slate-950 border-b border-slate-300 dark:border-slate-700 flex justify-between items-center shrink-0 relative overflow-hidden">
              <div className="flex items-center gap-3 md:gap-4 relative z-10">
                <div className="p-1.5 md:p-2 bg-primary-600 text-white border border-primary-700">
                  <Layers size={20} />
                </div>
                <div className="min-w-0">
                  <h2 className="text-xs md:text-sm font-serif text-slate-800 dark:text-white tracking-tight leading-none mb-1 truncate">
                    Material Fingerprint
                  </h2>
                  <p className="text-[8px] md:text-[10px] font-mono text-slate-500 items-center gap-2 uppercase tracking-widest hidden sm:flex">
                    Benchmarking{" "}
                    <span className="text-primary-500 font-bold">
                      {products.length}
                    </span>{" "}
                    grades{" "}
                    <span className="w-1 h-1 bg-slate-300 rounded-full" />{" "}
                    multi-dimensional analysis
                  </p>
                  <p className="text-[8px] font-mono text-slate-500 uppercase tracking-widest sm:hidden">
                    Comparing {products.length} grades
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                aria-label="Close Comparison"
                className="p-1.5 md:p-2 bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400 transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 z-10"
              >
                <X size={18} />
              </motion.button>
            </div>

            <div className="flex-1 overflow-auto md:overflow-hidden flex flex-col md:flex-row">
              {/* Radar Chart Section */}
              <div className="h-auto md:h-full md:w-2/5 bg-slate-50 dark:bg-slate-900/50 border-b md:border-b-0 md:border-r border-slate-300 dark:border-slate-700 p-4 md:p-6 flex flex-col relative overflow-y-auto custom-scrollbar shrink-0">
                <h3 className="text-[9px] font-mono text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2 relative z-10">
                  <Radar size={12} className="text-primary-500" /> Property Overlap Analysis
                </h3>
                <div className="h-[260px] md:h-[280px] w-full shrink-0 relative bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 group/radar">
                  {displayProducts.length > 0 ? (
                    <div ref={chartRef} className="w-full h-full" />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 gap-4">
                      <div className="w-16 h-16 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center">
                        <Radar
                          size={32}
                          className="text-slate-300 dark:text-slate-600"
                        />
                      </div>
                      <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500 dark:text-slate-400">
                        No products selected
                      </p>
                    </div>
                  )}
                </div>

                {diagnosticReport ? (
                  <div className="space-y-4 relative z-10 shrink-0 mt-4 text-left">
                    <div className="p-4 bg-emerald-500/5 dark:bg-emerald-500/10 border border-emerald-250 dark:border-emerald-800/50 rounded-xl space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-emerald-850 dark:text-emerald-400 flex items-center gap-1.5">
                          {t("materialDiagReport")}
                        </span>
                        {diagnosticReport.complianceScore !== null && (
                          <div className="text-right">
                            <span className="text-[8px] font-mono text-slate-400 block uppercase leading-none">
                              {t("baselineFit")}
                            </span>
                            <span className={`text-[13px] font-mono font-bold ${diagnosticReport.complianceScore > 85 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                              {diagnosticReport.complianceScore}%
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed font-mono">
                        {t("auditPrefix")}
                        <strong className="text-slate-700 dark:text-slate-200">{diagnosticReport.expProduct.gradeName}</strong>
                        {t("auditMiddle")}
                        <strong className="text-slate-700 dark:text-slate-200">{diagnosticReport.stdProduct.gradeName}</strong>
                        {t("auditSuffix")}
                      </div>

                      {/* Deviation metrics */}
                      <div className="space-y-2 pt-1 border-t border-dashed border-slate-200 dark:border-slate-800">
                        {diagnosticReport.deviations.map((dev) => (
                          <div key={dev.propKey} className="flex justify-between items-center text-[10px] font-mono py-0.5">
                            <span className="text-slate-500 dark:text-slate-400">{tProp(dev.propKey)}:</span>
                            <div className="flex items-center gap-2">
                              {dev.diffPercent !== null ? (
                                <>
                                  <span className="text-slate-400 text-[9px]">({dev.stdVal} → {dev.expVal} {dev.unit})</span>
                                  <span className={`font-bold px-1 rounded text-[9px] ${
                                    dev.status === "consistent" ? "text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30" : 
                                    dev.status === "warning" ? "text-amber-600 bg-amber-100 dark:bg-amber-900/30" : 
                                    "text-rose-600 bg-rose-100 dark:bg-rose-900/40"
                                  }`}>
                                    {dev.diffPercent > 0 ? `+${dev.diffPercent.toFixed(1)}%` : `${dev.diffPercent.toFixed(1)}%`}
                                  </span>
                                </>
                              ) : (
                                <span className="text-slate-400">({dev.stdVal} | {dev.expVal}) {t("noComparison")}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Automated diagnostic comments */}
                      <div className="pt-2.5 border-t border-dashed border-slate-200 dark:border-slate-800 space-y-1">
                        <span className="text-[9px] font-mono font-bold text-slate-400 block uppercase">
                          {t("diagSuggestions")}
                        </span>
                        <div className="space-y-1.5 text-[10px] text-slate-650 dark:text-slate-350 leading-relaxed">
                          {diagnosticReport.suggestions.map((s, sIdx) => (
                            <p key={sIdx} className="flex items-start gap-1">
                              <span className="text-emerald-500 select-none">•</span>
                              <span>{s}</span>
                            </p>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                     {recommendedStandards.length > 0 && (
                      <div className="mt-4 p-4 bg-sky-50 dark:bg-sky-950/20 border border-sky-200 dark:border-sky-800/45 rounded-xl space-y-3 relative z-10 text-left">
                        <div className="flex items-center gap-2">
                          <span className="p-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-sky-500 font-mono text-[10px] font-bold shrink-0 leading-none">
                            {t("alignmentOption")}
                          </span>
                          <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                            {t("expSampleDetected")}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono leading-relaxed">
                          {t("alignDesc")}
                        </p>
                        <div className="space-y-2 pt-1">
                          {recommendedStandards.map(rec => (
                            <div key={rec.id} className="flex items-center justify-between gap-2 p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg">
                              <div className="min-w-0 flex-1">
                                <span className="text-[10px] font-mono font-bold text-slate-800 dark:text-slate-100 block truncate">
                                  {rec.gradeName}
                                </span>
                                <span className="text-[9px] font-mono text-slate-400 block truncate">
                                  {rec.manufacturer}
                                </span>
                              </div>
                              <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => {
                                  if (onAddProduct) {
                                    onAddProduct(rec.id);
                                    setBaselineId(rec.id);
                                  }
                                }}
                                className="px-2.5 py-1.5 text-[9px] font-mono font-bold bg-sky-600 hover:bg-sky-500 text-white border border-sky-700 rounded-md shadow-sm select-none transition-all cursor-pointer whitespace-nowrap"
                              >
                                {t("alignInstantly")}
                              </motion.button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-4 p-4 bg-primary-50 dark:bg-primary-900/10 border border-primary-200 dark:border-primary-800/30 text-[10px] font-mono text-slate-650 dark:text-slate-400 leading-relaxed flex gap-3 relative z-10">
                      <div className="p-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shrink-0 h-fit">
                        <Info size={12} className="text-primary-500" />
                      </div>
                      <p>
                        <span className="font-bold text-primary-600 dark:text-primary-400 uppercase">
                          Expert Insight:
                        </span>{" "}
                        Areas of intersection indicate competitive equivalence.
                        Outer spikes represent superior performance in specific
                        domains. <strong>
                          {t("importTip")}
                        </strong>
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Comparison Table Section */}
              <div className="flex-1 overflow-auto custom-scrollbar bg-white dark:bg-slate-950 relative">
                <table className="w-full text-sm text-left border-separate border-spacing-0">
                  <thead className="text-[10px] font-mono text-slate-500 uppercase bg-slate-50 dark:bg-slate-900 sticky top-0 z-30">
                    <tr>
                      <th className="px-4 md:px-6 py-2 md:py-3 border-b border-r border-slate-300 dark:border-slate-700 min-w-[140px] md:min-w-[200px] sticky left-0 bg-slate-50 dark:bg-slate-900 z-40 uppercase tracking-widest">
                        {t("propertyName")}
                      </th>
                      {displayProducts.map((p, idx) => (
                        <th
                          key={p.id}
                          className="px-4 md:px-6 py-3 md:py-4 border-b border-r border-slate-300 dark:border-slate-700 min-w-[200px] md:min-w-[250px] relative group overflow-hidden"
                        >
                          <div
                            className="absolute top-0 left-0 w-full h-0.5"
                            style={{
                              backgroundColor: colors[idx % colors.length],
                            }}
                          />
                          <div className="flex justify-between items-start relative z-10">
                            <div className="min-w-0 flex-1">
                              <div
                                className="font-serif font-bold text-slate-800 dark:text-white text-base md:text-lg mb-1 truncate tracking-tight"
                                style={{ color: colors[idx % colors.length] }}
                                title={p.gradeName}
                              >
                                {p.gradeName}
                              </div>
                              <div
                                className="flex items-center gap-1.5 text-[8px] md:text-[9px] font-mono text-slate-500 bg-slate-100 dark:bg-slate-800 px-1.5 md:px-2 py-0.5 border border-slate-200 dark:border-slate-700 w-fit mb-1 md:mb-1.5 truncate max-w-full uppercase tracking-widest"
                                title={p.manufacturer}
                              >
                                <Factory size={10} className="shrink-0" />{" "}
                                <span className="truncate">
                                  {p.manufacturer}
                                </span>
                              </div>
                              {p.isExperimental ? (
                                <div className="flex items-center gap-1 text-[8px] font-mono font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/45 border border-emerald-250 dark:border-emerald-800/60 px-1.5 py-0.5 uppercase tracking-wider mb-2 w-fit">
                                  <span>{t("expLabData")}</span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-1 text-[8px] font-mono font-bold text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/45 border border-sky-250 dark:border-sky-800/60 px-1.5 py-0.5 uppercase tracking-wider mb-2 w-fit">
                                  <span>{t("marketStdData")}</span>
                                </div>
                              )}
                              <div className="flex items-center gap-1.5 md:gap-2">
                                <motion.button
                                  whileHover={{ scale: 1.05 }}
                                  whileTap={{ scale: 0.95 }}
                                  onClick={() =>
                                    setBaselineId(
                                      baselineId === p.id ? null : p.id,
                                    )
                                  }
                                  aria-label={
                                    baselineId === p.id
                                      ? "Clear baseline"
                                      : `Set ${p.gradeName} as baseline`
                                  }
                                  className={`flex items-center gap-1 md:gap-2 text-[8px] md:text-[9px] font-mono uppercase tracking-widest px-2 md:px-3 py-1 md:py-1.5 border transition-all ${baselineId === p.id ? "bg-emerald-600 text-white border-emerald-600 shadow-lg shadow-emerald-500/20" : "bg-white dark:bg-slate-800 text-slate-500 hover:text-primary-500 border-slate-300 dark:border-slate-700 shadow-sm"}`}
                                >
                                  <Target
                                    size={12}
                                    className={
                                      baselineId === p.id ? "animate-pulse" : ""
                                    }
                                  />
                                  <span className="whitespace-nowrap">
                                    {baselineId === p.id
                                      ? "Baseline"
                                      : "Set Baseline"}
                                  </span>
                                </motion.button>
                                <motion.button
                                  whileHover={{
                                    scale: 1.1,
                                    backgroundColor: "rgba(254, 226, 226, 1)",
                                  }}
                                  whileTap={{ scale: 0.9 }}
                                  onClick={() => onRemoveProduct(p.id)}
                                  className="p-1 md:p-1.5 bg-rose-50 dark:bg-rose-900/20 text-rose-600 border border-rose-200 dark:border-rose-800 hover:bg-rose-100 transition-colors rounded-lg shadow-sm"
                                  title="Remove from comparison"
                                >
                                  <X size={12} />
                                </motion.button>
                              </div>
                            </div>
                          </div>
                        </th>
                      ))}
                      {allProducts && displayProducts.length < 5 && (
                        <th className="px-4 md:px-6 py-3 md:py-4 border-b border-r border-slate-300 dark:border-slate-700 min-w-[200px] md:min-w-[250px] bg-slate-50/50 dark:bg-slate-900/30 sticky top-0 relative">
                          <div className="flex flex-col h-full justify-between gap-2">
                            <div>
                              <span className="text-[10px] font-mono leading-none tracking-wider font-bold text-primary-600 dark:text-primary-400 block uppercase mb-1">
                                {t("loadBenchmark")}
                              </span>
                              <span className="text-[9px] text-slate-500 dark:text-slate-400 font-mono block">
                                {t("compareSpecsDesc")}
                              </span>
                            </div>
                            <div className="relative pt-1.5">
                              <select
                                onChange={(e) => {
                                  const val = e.target.value;
                                  if (val && onAddProduct) {
                                    onAddProduct(val);
                                    // Set as baseline automatically if there's only 1 experimental item
                                    if (displayProducts.length === 1 && displayProducts[0].isExperimental) {
                                      setBaselineId(val);
                                    }
                                    e.target.value = "";
                                  }
                                }}
                                className="w-full px-2.5 py-1.5 text-[10px] font-mono font-medium border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 rounded focus:ring-1 focus:ring-primary-500 outline-none cursor-pointer"
                                defaultValue=""
                              >
                                <option value="" disabled>
                                  {t("selectBenchmark")}
                                </option>
                                {(() => {
                                  const categoryWords = displayProducts.length > 0 
                                    ? displayProducts[0].gradeName.toUpperCase().replace(/[^A-Z]/g, " ").split(" ").filter(w => w.length > 1)
                                    : [];
                                  
                                  const matchesCategory = (name: string) => {
                                    return categoryWords.some(w => name.toUpperCase().includes(w));
                                  };

                                  const filtered = allProducts.filter(p => !displayProducts.some(dp => dp.id === p.id));
                                  const sorted = [...filtered].sort((a, b) => {
                                    const aMatch = matchesCategory(a.gradeName) ? 1 : 0;
                                    const bMatch = matchesCategory(b.gradeName) ? 1 : 0;
                                    if (aMatch !== bMatch) return bMatch - aMatch;
                                    return (a.isExperimental ? 1 : 0) - (b.isExperimental ? 1 : 0);
                                  });

                                  return sorted.map(p => (
                                    <option key={p.id} value={p.id}>
                                      [{p.isExperimental ? t("experimentalShort") : t("standardShort")}] {p.gradeName} - {p.manufacturer}
                                    </option>
                                  ));
                                })()}
                              </select>
                            </div>
                          </div>
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-300 dark:divide-slate-700">
                    {/* Key Specifications Section */}
                    {KEY_SPECS.some((key) =>
                      displayProducts.some((p) => p.properties[key]),
                    ) && (
                      <tr className="bg-slate-50 dark:bg-slate-900">
                        <td
                          colSpan={displayProducts.length + (allProducts && displayProducts.length < 5 ? 2 : 1)}
                          className="px-6 py-2 text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 sticky left-0 z-20 bg-slate-50 dark:bg-slate-900 border-y border-slate-300 dark:border-slate-700"
                        >
                          {t("keySpecsTitle")}
                        </td>
                      </tr>
                    )}
                    {KEY_SPECS.filter((key) =>
                      displayProducts.some((p) => p.properties[key]),
                    ).map((key) => (
                      <tr
                        key={key}
                        className="hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors group"
                      >
                        <td className="px-6 py-3 font-mono font-bold text-slate-600 dark:text-slate-400 border-r border-slate-300 dark:border-slate-700 sticky left-0 bg-white dark:bg-slate-950 group-hover:bg-slate-50 dark:group-hover:bg-slate-900 transition-colors z-20 text-[10px] uppercase tracking-widest">
                          {tProp(key)}
                        </td>
                        {displayProducts.map((p) => (
                          <td
                            key={`${p.id}-${key}`}
                            className="px-6 py-3 border-r border-slate-300 dark:border-slate-700"
                          >
                            <span className="text-[11px] font-mono text-slate-700 dark:text-slate-300 leading-relaxed">
                              {p.properties[key]?.value || "-"}
                            </span>
                          </td>
                        ))}
                        {allProducts && displayProducts.length < 5 && (
                          <td className="px-6 py-3 border-r border-slate-300 dark:border-slate-700 bg-slate-50/10 dark:bg-slate-900/10" />
                        )}
                      </tr>
                    ))}

                    {groupedProps.map(([group, props]) => (
                      <React.Fragment key={group}>
                        <tr className="bg-slate-50 dark:bg-slate-900">
                          <td
                            colSpan={displayProducts.length + (allProducts && displayProducts.length < 5 ? 2 : 1)}
                            className="px-6 py-2 text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 sticky left-0 z-20 bg-slate-50 dark:bg-slate-900 border-y border-slate-300 dark:border-slate-700"
                          >
                            {t(`group_${group}` as Parameters<typeof t>[0])}{" "}
                            {t("properties")}
                          </td>
                        </tr>
                        {props.map((propKey, pIdx) => (
                          <motion.tr
                            key={propKey}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: pIdx * 0.01 }}
                            className="hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors group"
                          >
                            <td
                              className="px-6 py-3 font-mono text-slate-600 dark:text-slate-400 border-r border-slate-300 dark:border-slate-700 sticky left-0 bg-white dark:bg-slate-950 group-hover:bg-slate-50 dark:group-hover:bg-slate-900 transition-colors z-20 text-[10px] truncate max-w-[200px]"
                              title={tProp(propKey)}
                            >
                              {tProp(propKey)}
                            </td>
                            {displayProducts.map((p) => {
                              const prop = p.properties[propKey];
                              const numVal = Number(prop?.value);
                              const isBest =
                                !isNaN(numVal) &&
                                bestValuesMap[propKey] === numVal;
                              const lowBest = isLowBest(propKey);

                              // Baseline comparison logic
                              let diffDisplay = null;
                              if (
                                baselineId &&
                                baselineId !== p.id &&
                                !isNaN(numVal)
                              ) {
                                const baselineProp =
                                  baselineProduct?.properties[propKey];
                                const baselineVal = Number(baselineProp?.value);
                                if (!isNaN(baselineVal) && baselineVal !== 0) {
                                  const diff =
                                    ((numVal - baselineVal) / baselineVal) *
                                    100;
                                  const isZero = Math.abs(diff) < 0.01;
                                  const isGood = lowBest ? diff < 0 : diff > 0;

                                  diffDisplay = (
                                    <div
                                      className={`flex items-center gap-0.5 text-[9px] font-mono font-bold mt-1 ${isZero ? "text-slate-400" : isGood ? "text-emerald-500" : "text-rose-500"}`}
                                    >
                                      {isZero ? (
                                        <Minus size={8} />
                                      ) : diff > 0 ? (
                                        <ArrowUpRight size={8} />
                                      ) : (
                                        <ArrowDownRight size={8} />
                                      )}
                                      {Math.abs(diff).toFixed(1)}%
                                    </div>
                                  );
                                }
                              }

                              return (
                                <td
                                  key={`${p.id}-${propKey}`}
                                  className={`px-6 py-3 border-r border-slate-300 dark:border-slate-700 ${isBest && !baselineId ? "bg-sky-50 dark:bg-sky-900/10" : ""} ${baselineId === p.id ? "bg-emerald-50 dark:bg-emerald-900/10" : ""}`}
                                >
                                  <div className="flex flex-col">
                                    <div className="flex items-baseline gap-1">
                                      <span
                                        className={`text-[11px] font-mono font-bold ${isBest && !baselineId ? "text-sky-700 dark:text-sky-400" : "text-slate-700 dark:text-slate-300"}`}
                                      >
                                        {prop?.value ?? "-"}
                                      </span>
                                      {prop?.unit && (
                                        <span className="text-[9px] font-mono text-slate-400">
                                          {prop.unit}
                                        </span>
                                      )}
                                    </div>
                                    {diffDisplay}
                                  </div>
                                </td>
                              );
                            })}
                            {allProducts && displayProducts.length < 5 && (
                              <td className="px-6 py-3 border-r border-slate-300 dark:border-slate-700 bg-slate-50/10 dark:bg-slate-900/10" />
                            )}
                          </motion.tr>
                        ))}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
