import React, { useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Layers, Database, Zap, RefreshCw } from "lucide-react";
import { Product } from '@/types/index';
import { SummaryCard } from '@/components/features/Dashboard/DashboardComponents';
import { calculateCompleteness } from '@/utils/productUtils';

interface DashboardStatsProps {
  allProducts: Product[];
  showSummary: boolean;
  t: (key: string, fallback?: string) => string;
}

export const DashboardStats: React.FC<DashboardStatsProps> = React.memo(
  ({ allProducts, showSummary, t }) => {
    const summaryStats = useMemo(() => {
      const len = allProducts.length;
      if (!len) return { mfgCount: 0, avgComp: 0 };
      const manufacturers = new Set<string>();
      let totalScore = 0;

      for (let i = 0; i < len; i++) {
        const p = allProducts[i];
        manufacturers.add(p.manufacturer);
        totalScore += calculateCompleteness(p);
      }
      return {
        mfgCount: manufacturers.size,
        avgComp: Math.round(totalScore / len),
      };
    }, [allProducts]);

    return (
      <div className="flex flex-col gap-2 shrink-0">
        <AnimatePresence mode="wait">
          {showSummary && (
            <motion.div
              key="dashboard-summary-cards"
              variants={{
                hidden: { height: 0, opacity: 0, y: -10 },
                show: {
                  height: "auto",
                  opacity: 1,
                  y: 0,
                  transition: {
                    staggerChildren: 0.05,
                    duration: 0.4,
                    ease: [0.16, 1, 0.3, 1],
                  },
                },
              }}
              initial="hidden"
              animate="show"
              exit={{
                height: 0,
                opacity: 0,
                y: -10,
                transition: { duration: 0.2 },
              }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 overflow-hidden"
            >
              <motion.div
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  show: { opacity: 1, y: 0 },
                }}
              >
                <SummaryCard
                  title={t("totalGrades")}
                  value={allProducts.length}
                  subtitle={t("growthLastMonth")}
                  icon={Layers}
                  color="primary"
                />
              </motion.div>
              <motion.div
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  show: { opacity: 1, y: 0 },
                }}
              >
                <SummaryCard
                  title={t("activeManufacturers")}
                  value={summaryStats.mfgCount}
                  subtitle={t("globalCoverage")}
                  icon={Database}
                  color="indigo"
                />
              </motion.div>
              <motion.div
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  show: { opacity: 1, y: 0 },
                }}
              >
                <SummaryCard
                  title={t("avgCompleteness")}
                  value={`${summaryStats.avgComp}%`}
                  subtitle={t("continuousOptimization")}
                  icon={Zap}
                  color="amber"
                />
              </motion.div>
              <motion.div
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  show: { opacity: 1, y: 0 },
                }}
              >
                <SummaryCard
                  title={t("syncCountToday")}
                  value={42}
                  subtitle={t("realtimeCloudSync")}
                  icon={RefreshCw}
                  color="emerald"
                />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  },
);
