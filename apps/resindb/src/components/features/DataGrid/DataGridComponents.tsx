import React, { useRef, useEffect } from "react";
import { Product, ColumnConfig } from '@/types/index';
import { RADAR_KEYS } from '@/utils/productUtils';
import { useLanguage } from "@/contexts/LanguageContext";
import { Search, RotateCcw } from "lucide-react";
import type { ECharts } from "@/lib/echarts";
import { motion } from "motion/react";

export const SkeletonRow: React.FC<{ columns: ColumnConfig[] }> = ({ columns }) => (
  <motion.tr
    initial={{ opacity: 0, y: 4 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }}
    className="border-b border-slate-100 dark:border-slate-800"
  >
    <td className="px-4 py-4 relative">
      <div className="w-4 h-4 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
    </td>
    <td className="px-4 py-4 relative">
      <div className="w-16 h-2 bg-slate-100 dark:bg-slate-800 rounded-full animate-pulse" />
    </td>
    {columns
      .filter((c) => c.visible)
      .map((_, i) => (
        <td key={i} className="px-4 py-4 relative">
          <div
            className="w-full h-4 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse"
            style={{ animationDelay: `${i * 100}ms` }}
          />
        </td>
      ))}
    <td className="px-4 py-4 relative">
      <div className="w-12 h-6 bg-slate-100 dark:bg-slate-800 rounded-lg ml-auto animate-pulse" />
    </td>
  </motion.tr>
);

export const EmptyState: React.FC<{ onClearFilters?: () => void }> = ({
  onClearFilters,
}) => {
  const { t } = useLanguage();
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-32 px-6 text-center"
    >
      <div className="w-24 h-24 bg-slate-50 dark:bg-slate-900 rounded-full flex items-center justify-center mb-6 border border-slate-100 dark:border-slate-800 shadow-sm relative group">
        <Search
          size={40}
          className="text-slate-300 dark:text-slate-600 group-hover:scale-110 group-hover:text-primary-400 transition-all duration-500"
        />
        <motion.div
          animate={{ scale: [1, 1.1, 1], opacity: [0.02, 0.05, 0.02] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-0 bg-primary-500 rounded-full blur-xl"
        />
      </div>
      <h3 className="text-xl font-black text-slate-800 dark:text-white tracking-tight mb-2">
        {t("noResults")}
      </h3>
      <p className="text-xs font-bold text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed uppercase tracking-widest">
        {t("noResultsDesc")}
      </p>
      <motion.button
        whileHover={{ scale: 1.05, y: -2 }}
        whileTap={{ scale: 0.95 }}
        onClick={() =>
          onClearFilters ? onClearFilters() : window.location.reload()
        }
        className="mt-8 px-6 py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl font-bold text-xs transition-all shadow-sm flex items-center gap-2 uppercase tracking-widest"
      >
        <RotateCcw size={14} /> {t("resetFilters")}
      </motion.button>
    </motion.div>
  );
};

export const QuickRadarPopup: React.FC<{
  product: Product;
  position: { x: number; y: number };
}> = ({ product, position }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const { tProp } = useLanguage();

  useEffect(() => {
    if (!chartRef.current) return;
    let active = true;
    let myChart: ECharts | null = null;

    import("@/lib/echarts").then((echartsLib) => {
      if (!active || !chartRef.current) return;

      myChart =
        echartsLib.getInstanceByDom(chartRef.current) ||
        echartsLib.init(chartRef.current);

      // Filter RADAR_KEYS to only include properties that exist on this product
      let availableProps = RADAR_KEYS.filter(
        (p) => product.properties?.[p] !== undefined,
      );

      // If less than 3 properties match, try to find any numeric properties
      if (availableProps.length < 3) {
        const numericProps = Object.keys(product.properties).filter((k) => {
          const val = product.properties?.[k]?.value;
          return typeof val === "number" || !isNaN(parseFloat(String(val)));
        });
        availableProps = numericProps.slice(0, 5); // Take up to 5 numeric properties
      }

      const props = availableProps.length >= 3 ? availableProps : RADAR_KEYS;

      const values = props.map((p) => {
        const v = product.properties?.[p]?.value;
        return typeof v === "number" ? v : parseFloat(String(v)) || 0;
      });

      myChart.setOption({
        radar: {
          indicator: props.map((p) => ({ name: tProp(p).slice(0, 8) })),
          shape: "circle",
          splitNumber: 3,
          axisName: { fontSize: 8, color: "#94a3b8" },
        },
        series: [
          {
            type: "radar",
            data: [
              {
                value: values,
                areaStyle: { color: "rgba(99, 102, 241, 0.3)" },
                lineStyle: { color: "#6366f1" },
              },
            ],
            symbol: "none",
          },
        ],
      });
    });

    return () => {
      active = false;
      if (myChart) {
        myChart.dispose();
      }
    };
  }, [product, tProp]);

  const left = Math.min(position.x + 20, window.innerWidth - 280);
  const top = Math.min(
    Math.max(position.y - 120, 20),
    window.innerHeight - 280,
  );

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: 10 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className="fixed z-[100] w-64 h-64 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 p-2 pointer-events-none transform-gpu"
      style={{ left, top }}
    >
      <div ref={chartRef} className="w-full h-full" />
    </motion.div>
  );
};
