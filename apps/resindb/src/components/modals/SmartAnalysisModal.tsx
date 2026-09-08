import { logger } from '@/lib/logger';
import React, { useState, useEffect, useCallback } from "react";
import {
  X,
  Sparkles,
  BrainCircuit,
  TrendingUp,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { Product } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence } from "motion/react";
import { aiService } from "@/services/aiService";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface SmartAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  product: Product | null;
}

export const SmartAnalysisModal: React.FC<SmartAnalysisModalProps> = ({
  isOpen,
  onClose,
  product,
}) => {
  const { t, language } = useLanguage();
  const [analysis, setAnalysis] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);

  const handleAnalyze = useCallback(async () => {
    if (!product) return;
    setIsGenerating(prev => {
      if (prev) return prev;
      return true;
    });
    try {
      const result = await aiService.analyzeProduct(product);
      setAnalysis(result);
    } catch (error) {
      logger.error("AI Analysis failed:", error);
      setAnalysis("Error generating analysis. Please check your connection and try again.");
    } finally {
      setIsGenerating(false);
    }
  }, [product]);

  useEffect(() => {
    if (isOpen && product && !analysis && !isGenerating) {
      handleAnalyze();
    } else if (!isOpen) {
      setAnalysis("");
    }
  }, [isOpen, product, analysis, isGenerating, handleAnalyze]);

  return (
    <AnimatePresence>
      {isOpen && product && (
        <motion.div
          key="smart-analysis-modal-root"
          className="fixed inset-0 z-[110] flex items-center justify-center p-4"
        >
          <motion.div
            key="smart-analysis-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-md"
            onClick={onClose}
          ></motion.div>
          
          <motion.div
            key="smart-analysis-content"
            initial={{ opacity: 0, scale: 0.95, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 30 }}
            transition={{ type: "spring", duration: 0.5, bounce: 0.2 }}
            className="relative w-full max-w-3xl h-[85vh] bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col shadow-[0_0_50px_-12px_rgba(79,70,229,0.3)] rounded-[2.5rem] overflow-hidden"
          >
            {/* Glossy Header */}
            <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-950 relative overflow-hidden shrink-0 shadow-lg">
              <div className="absolute inset-0 bg-gradient-to-tr from-indigo-900/40 via-transparent to-purple-950/40 opacity-50" />
              <div className="flex items-center gap-4 relative z-10">
                <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-2xl shadow-xl animate-pulse ring-4 ring-indigo-500/20">
                  <Sparkles size={20} />
                </div>
                <div>
                  <h3 className="text-base font-serif font-black text-white tracking-tight leading-none mb-1.5 flex items-center gap-2">
                    {t("smartAnalysis", "AI Smart Insights")}
                    <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded-full border border-white/10 font-mono text-purple-200 uppercase tracking-tighter">
                      AI PRO
                    </span>
                  </h3>
                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-[0.2em] truncate">
                    Material Strategy • {product.gradeName}
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1, backgroundColor: "rgba(225, 29, 72, 1)" }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2.5 bg-white/5 backdrop-blur-xl border border-white/10 text-slate-400 rounded-2xl z-10 hover:text-white transition-colors"
              >
                <X size={18} />
              </motion.button>
            </div>

            {/* Scrollable Insights Container */}
            <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-slate-50/50 dark:bg-slate-950 relative">
              {isGenerating ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
                  <div className="relative">
                    <motion.div 
                      animate={{ rotate: 360 }}
                      transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                      className="w-24 h-24 rounded-full border-4 border-indigo-500/20 shadow-[0_0_20px_rgba(99,102,241,0.2)]"
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <BrainCircuit size={40} className="text-indigo-500 animate-pulse" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-lg font-serif font-bold text-slate-900 dark:text-white">{language === "en" ? "Synthesizing Material Wisdom" : "正在提取材料智慧"}</h4>
                    <p className="text-xs font-mono text-slate-500 uppercase tracking-widest max-w-xs leading-relaxed">
                      {language === "en" ? "AI is currently cross-referencing technical specifications with market trends and competitor portfolios..." : "AI 正在将技术规格参数与市场趋势及竞品数据进行交叉对比与分析..."}
                    </p>
                  </div>
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map(i => (
                      <motion.div
                        key={i}
                        animate={{ scale: [1, 1.5, 1], opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
                        className="w-2 h-2 bg-indigo-500 rounded-full"
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="max-w-none"
                >
                  <motion.div 
                    initial="hidden"
                    animate="visible"
                    variants={{
                      hidden: { opacity: 0 },
                      visible: {
                        opacity: 1,
                        transition: {
                          staggerChildren: 0.1
                        }
                      }
                    }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8"
                  >
                    <motion.div variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>
                      <InsightCard icon={<TrendingUp size={16} />} label={language === "en" ? "Market Potential" : "市场潜力"} value={language === "en" ? "High Growth" : "高成长"} color="blue" />
                    </motion.div>
                    <motion.div variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>
                      <InsightCard icon={<ShieldCheck size={16} />} label={language === "en" ? "Quality Score" : "质量得分"} value={language === "en" ? "Premium Grade" : "尊享级"} color="emerald" />
                    </motion.div>
                    <motion.div variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>
                      <InsightCard icon={<Zap size={16} />} label={language === "en" ? "Innovation Level" : "创新等级"} value={language === "en" ? "Specialized" : "专精级"} color="purple" />
                    </motion.div>
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="prose prose-slate dark:prose-invert prose-xs md:prose-sm max-w-none prose-headings:font-serif prose-headings:font-black prose-headings:tracking-tight prose-p:font-sans prose-p:leading-relaxed prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-strong:text-indigo-600 dark:prose-strong:text-indigo-400"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {analysis}
                    </ReactMarkdown>
                  </motion.div>
                </motion.div>
              )}
            </div>

            {/* AI Footer Actions */}
            <div className="px-6 py-4 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center shrink-0">
               <div className="flex items-center gap-2">
                 <div className="flex -space-x-2">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="w-6 h-6 rounded-full border-2 border-white dark:border-slate-900 bg-slate-200 dark:bg-slate-800 flex items-center justify-center text-[8px] font-black text-slate-500">
                        {String.fromCharCode(64 + i)}
                      </div>
                    ))}
                 </div>
                 <span className="text-[10px] font-mono text-slate-400">{language === "en" ? "Trusted by Strategy Teams" : "备受策略团队信赖"}</span>
               </div>
               <div className="flex gap-3">
                 <motion.button
                   whileHover={{ scale: 1.05 }}
                   whileTap={{ scale: 0.95 }}
                   onClick={handleAnalyze}
                   className="flex items-center gap-2 px-5 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-2xl text-[10px] font-mono font-bold uppercase tracking-widest hover:bg-slate-200 transition-colors"
                 >
                   {language === "en" ? "Refine Perspective" : "重塑分析视角"}
                 </motion.button>
                 <motion.button
                   whileHover={{ scale: 1.05 }}
                   whileTap={{ scale: 0.95 }}
                   onClick={onClose}
                   className="px-8 py-2 bg-slate-950 dark:bg-white text-white dark:text-slate-900 rounded-2xl text-[10px] font-mono font-bold uppercase tracking-widest shadow-xl shadow-slate-900/10"
                 >
                   {language === "en" ? "Close Insights" : "关闭洞察"}
                 </motion.button>
               </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const InsightCard: React.FC<{ icon: React.ReactNode, label: string, value: string, color: 'blue' | 'emerald' | 'purple' }> = ({ icon, label, value, color }) => {
  const colors = {
    blue: "bg-blue-50 dark:bg-blue-900/20 text-blue-600 border-blue-100 dark:border-blue-800",
    emerald: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 border-emerald-100 dark:border-emerald-800",
    purple: "bg-purple-50 dark:bg-purple-900/20 text-purple-600 border-purple-100 dark:border-purple-800"
  };
  
  return (
    <div className={`p-4 rounded-[1.5rem] border ${colors[color]} flex flex-col gap-2`}>
      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest opacity-60">
        {icon} {label}
      </div>
      <div className="text-sm font-serif font-black tracking-tight">{value}</div>
    </div>
  );
};
