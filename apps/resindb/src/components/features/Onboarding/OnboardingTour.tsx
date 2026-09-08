import React, { useState } from "react";
import {
  ChevronRight,
  ChevronLeft,
  Sparkles,
  LayoutGrid,
  Search,
  Bot,
  Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

interface TourStep {
  title: string;
  description: string;
  icon: unknown;
  color: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    title: "欢迎来到 ResinDB Pro",
    description:
      "这是您的新一代高分子材料科研数据中心。让我们花一分钟了解一下核心功能。",
    icon: Sparkles,
    color: "text-primary-500",
  },
  {
    title: "数据概览",
    description:
      "实时监控数据完整度、活跃厂商和系统健康状态。系统会为您提供数据优化建议。",
    icon: LayoutGrid,
    color: "text-indigo-500",
  },
  {
    title: "强大的搜索与过滤",
    description:
      "使用自然语言或属性语法（如 密度 > 0.9）快速定位目标牌号。支持保存常用视图。",
    icon: Search,
    color: "text-emerald-500",
  },
  {
    title: "科研实验室",
    description: "强大的可视化引擎，支持复杂的数据对比、性能预测和科研分析。",
    icon: Bot,
    color: "text-violet-500",
  },
  {
    title: "即刻开始科研之旅",
    description:
      "现在您可以开始导入数据或浏览现有的牌号库了。如有疑问，请随时查看帮助中心。",
    icon: Zap,
    color: "text-amber-500",
  },
];

export const OnboardingTour: React.FC<{ onComplete: () => void }> = ({
  onComplete,
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  const next = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  };

  const prev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const step = TOUR_STEPS[currentStep];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[300] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="bg-white dark:bg-slate-900 w-full max-w-lg rounded-[3rem] shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden"
      >
        <div className="p-10 text-center">
          <div className="flex justify-center mb-8">
            <div
              className={`p-6 rounded-[2.5rem] bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 shadow-inner ${step.color}`}
            >
              {React.createElement(step.icon as React.ElementType, {
                size: 48,
                strokeWidth: 1.5,
              })}
            </div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight mb-4">
                {step.title}
              </h3>
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400 leading-relaxed max-w-sm mx-auto">
                {step.description}
              </p>
            </motion.div>
          </AnimatePresence>

          <div className="mt-12 flex items-center justify-center gap-2">
            {TOUR_STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1.5 rounded-full transition-all duration-500 ${i === currentStep ? "w-8 bg-primary-600" : "w-1.5 bg-slate-200 dark:bg-slate-800"}`}
              />
            ))}
          </div>

          <div className="mt-12 flex items-center justify-between">
            <motion.button
              whileHover={{ scale: 1.05, x: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={onComplete}
              className="text-xs font-bold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-500/50 rounded px-1"
            >
              跳过介绍
            </motion.button>

            <div className="flex items-center gap-3">
              {currentStep > 0 && (
                <motion.button
                  whileHover={{ scale: 1.1, x: -2 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={prev}
                  className="p-3 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-2xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 shadow-sm"
                >
                  <ChevronLeft size={20} />
                </motion.button>
              )}
              <motion.button
                whileHover={{ scale: 1.05, x: 2 }}
                whileTap={{ scale: 0.95 }}
                onClick={next}
                className="px-8 py-3 bg-primary-600 hover:bg-primary-500 text-white rounded-2xl font-bold text-xs transition-all shadow-xl shadow-primary-500/20 flex items-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
              >
                {currentStep === TOUR_STEPS.length - 1 ? "开始使用" : "下一步"}
                <ChevronRight size={16} />
              </motion.button>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};
