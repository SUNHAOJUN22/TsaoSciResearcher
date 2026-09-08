import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Search, SlidersHorizontal, Cpu, ArrowUpRight, RefreshCw, BarChart2, Zap } from 'lucide-react';
import { Product } from '@/types/index';
import { useLanguage } from '@/contexts/LanguageContext';

interface ChemicalSimilaritySearchProps {
  allProducts: Product[];
  onViewProduct?: (product: Product) => void;
}

export const ChemicalSimilaritySearch: React.FC<ChemicalSimilaritySearchProps> = ({
  allProducts,
  onViewProduct
}) => {
  const { language } = useLanguage();

  // Selected reference product
  const [targetId, setTargetId] = useState<string>(allProducts[0]?.id || '');
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpenDropdown, setIsOpenDropdown] = useState(false);

  // Vector Distance Metric
  const [metric, setMetric] = useState<'cosine' | 'euclidean'>('cosine');

  // Dynamic discovery of numeric properties
  const allNumericProperties = useMemo(() => {
    const keysMap = new Map<string, { labelZh: string; labelEn: string; unit: string }>();

    // Common standard properties mappings
    const defaultMappings: Record<string, { zh: string; en: string }> = {
      density: { zh: '密度', en: 'Density' },
      mfr: { zh: '熔体流动速率 (MFR)', en: 'Melt Flow Rate' },
      tensileYield: { zh: '拉伸屈服强度', en: 'Tensile Yield Strength' },
      flexuralModulus: { zh: '弯曲模量', en: 'Flexural Modulus' },
      izodImpact: { zh: '悬臂梁冲击强度', en: 'Izod Impact Strength' }
    };

    allProducts.forEach(p => {
      Object.entries(p.properties || {}).forEach(([key, propVal]) => {
        const val = propVal?.value;
        const num = typeof val === 'number' ? val : parseFloat(String(val));
        if (!isNaN(num)) {
          if (!keysMap.has(key)) {
            const mapping = defaultMappings[key] || { zh: key, en: key };
            keysMap.set(key, {
              labelZh: mapping.zh,
              labelEn: mapping.en,
              unit: propVal.unit || ''
            });
          }
        }
      });
    });

    return Array.from(keysMap.entries()).map(([key, info]) => ({
      key,
      ...info
    }));
  }, [allProducts]);

  // Selected features for vector query (Default all)
  const [selectedFeatures, setSelectedFeatures] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    initial['density'] = true;
    initial['mfr'] = true;
    initial['tensileYield'] = true;
    initial['flexuralModulus'] = true;
    initial['izodImpact'] = true;
    return initial;
  });

  // Feature weights (Scale 1 to 5)
  const [featureWeights, setFeatureWeights] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    initial['density'] = 1;
    initial['mfr'] = 2; // high flow rate is often critical
    initial['tensileYield'] = 1;
    initial['flexuralModulus'] = 1;
    initial['izodImpact'] = 2; // impact is critical for modified resins
    return initial;
  });

  // Handle toggling feature on/off
  const toggleFeature = (key: string) => {
    setSelectedFeatures(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // Adjust weight
  const handleWeightChange = (key: string, val: number) => {
    setFeatureWeights(prev => ({
      ...prev,
      [key]: val
    }));
  };

  // Target product object
  const targetProduct = useMemo(() => {
    return allProducts.find(p => p.id === targetId) || null;
  }, [targetId, allProducts]);

  // Dropdown filtered candidates
  const filteredSearchList = useMemo(() => {
    if (!searchTerm.trim()) return allProducts.slice(0, 10);
    const lowerQuery = searchTerm.toLowerCase();
    return allProducts.filter(p => 
      p.gradeName.toLowerCase().includes(lowerQuery) || 
      p.manufacturer.toLowerCase().includes(lowerQuery) ||
      (p.categoryIds && p.categoryIds.some(cat => cat.toLowerCase().includes(lowerQuery)))
    );
  }, [allProducts, searchTerm]);

  // Similarity Calculation Engine
  const similarityResults = useMemo(() => {
    if (!targetProduct || allProducts.length <= 1) return [];

    const activeKeys = allNumericProperties
      .map(f => f.key)
      .filter(k => selectedFeatures[k] === true);

    if (activeKeys.length === 0) return [];

    // 1. Compute bounds (min/max) for normalization
    const mins: Record<string, number> = {};
    const maxes: Record<string, number> = {};
    activeKeys.forEach(k => {
      mins[k] = Infinity;
      maxes[k] = -Infinity;
    });

    allProducts.forEach(p => {
      activeKeys.forEach(k => {
        const raw = p.properties?.[k]?.value;
        const val = typeof raw === 'number' ? raw : parseFloat(String(raw));
        if (!isNaN(val)) {
          if (val < mins[k]) mins[k] = val;
          if (val > maxes[k]) maxes[k] = val;
        }
      });
    });

    // 2. Build normalized vector for reference product
    const targetVector: Record<string, number> = {};
    activeKeys.forEach(k => {
      const raw = targetProduct.properties?.[k]?.value;
      const val = typeof raw === 'number' ? raw : parseFloat(String(raw));
      const range = (maxes[k] || 0) - (mins[k] || 0);
      if (!isNaN(val)) {
        targetVector[k] = range > 0 ? (val - mins[k]) / range : 0.5;
      } else {
        targetVector[k] = 0.5; // fallback
      }
    });

    // 3. Compute vector comparisons
    const matches = allProducts
      .filter(p => p.id !== targetProduct.id)
      .map(p => {
        const candidateVector: Record<string, number> = {};
        let missingKeys = 0;

        activeKeys.forEach(k => {
          const raw = p.properties?.[k]?.value;
          const val = typeof raw === 'number' ? raw : parseFloat(String(raw));
          const range = (maxes[k] || 0) - (mins[k] || 0);
          if (!isNaN(val)) {
            candidateVector[k] = range > 0 ? (val - mins[k]) / range : 0.5;
          } else {
            // Apply standard mean imputation or penalty
            candidateVector[k] = 0.5;
            missingKeys++;
          }
        });

        let similarityScore: number;
        const details: Record<string, { targetVal: number; targetNorm: number; candidateVal: number; candidateNorm: number }> = {};

        activeKeys.forEach(k => {
          const targetRaw = targetProduct.properties?.[k]?.value;
          const targetVal = typeof targetRaw === 'number' ? targetRaw : parseFloat(String(targetRaw));
          const candRaw = p.properties?.[k]?.value;
          const candidateVal = typeof candRaw === 'number' ? candRaw : parseFloat(String(candRaw));

          details[k] = {
            targetVal: isNaN(targetVal) ? 0 : targetVal,
            targetNorm: targetVector[k],
            candidateVal: isNaN(candidateVal) ? 0 : candidateVal,
            candidateNorm: candidateVector[k]
          };
        });

        if (metric === 'cosine') {
          // Weighted Cosine Similarity
          let dotProduct = 0;
          let targetNormSq = 0;
          let candNormSq = 0;

          activeKeys.forEach(k => {
            const w = featureWeights[k] || 1;
            const t = targetVector[k];
            const c = candidateVector[k];
            dotProduct += w * t * c;
            targetNormSq += w * t * t;
            candNormSq += w * c * c;
          });

          const denom = Math.sqrt(targetNormSq) * Math.sqrt(candNormSq);
          similarityScore = denom > 0 ? (dotProduct / denom) * 100 : 0;
        } else {
          // Weighted Euclidean Distance normalized to a 0-100 score
          let sumSq = 0;
          activeKeys.forEach(k => {
            const w = featureWeights[k] || 1;
            const diff = targetVector[k] - candidateVector[k];
            sumSq += w * diff * diff;
          });

          const maxDistSq = activeKeys.reduce((acc, k) => acc + (featureWeights[k] || 1), 0);
          const rawDist = Math.sqrt(sumSq);
          const maxDist = Math.sqrt(maxDistSq);
          similarityScore = maxDist > 0 ? (1 - rawDist / maxDist) * 100 : 0;
        }

        // Apply a penalty for missing properties in composition formula comparison
        if (missingKeys > 0) {
          similarityScore = Math.max(0, similarityScore - (missingKeys * 5));
        }

        return {
          product: p,
          score: Math.round(similarityScore * 10) / 10,
          details
        };
      });

    // Sort by descending score
    return matches.sort((a, b) => b.score - a.score).slice(0, 5);
  }, [targetProduct, allProducts, allNumericProperties, selectedFeatures, featureWeights, metric]);

  const translate = (zh: string, en: string) => {
    return language === 'zh' ? zh : en;
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-2xl p-5 md:p-6 shadow-sm flex flex-col space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800/60 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1 px-2 bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 font-black rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1">
              <Zap size={11} className="animate-pulse" /> Material Informatics
            </span>
            <span className="text-xs font-bold text-slate-400">Vector Projection</span>
          </div>
          <h2 className="text-lg font-black text-slate-850 dark:text-white flex items-center gap-2">
            <Cpu size={18} className="text-primary-500" />
            {translate('材料化学相似度搜索 (Vector Distance Matrix)', 'Chemical Similarity Search')}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {translate('计算配方组分及物理性能特征的高维向量空间距离，智能寻找相似可替代树脂原料。', 'Compute multi-dimensional vector distances over composition and physical metrics to source resin substitutes.')}
          </p>
        </div>

        {/* Algorithm Settings Selector */}
        <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-950 p-1.5 rounded-xl border border-slate-200/40 dark:border-slate-800">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => setMetric('cosine')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              metric === 'cosine'
                ? 'bg-white dark:bg-slate-850 text-primary-600 dark:text-primary-450 border border-slate-200/60 dark:border-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {translate('余弦相似度', 'Cosine Sim')}
          </motion.button>
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => setMetric('euclidean')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              metric === 'euclidean'
                ? 'bg-white dark:bg-slate-850 text-indigo-600 dark:text-indigo-400 border border-slate-200/60 dark:border-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {translate('欧氏距离', 'Euclidean Dist')}
          </motion.button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left Control Column */}
        <div className="xl:col-span-5 space-y-5">
          {/* Reference Product Dropdown */}
          <div className="space-y-2 relative">
            <label className="text-xs font-extrabold text-slate-400 uppercase tracking-wider block">
              {translate('1. 选择参考树脂品级', '1. Select Reference Resin')}
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <div
                  onClick={() => setIsOpenDropdown(!isOpenDropdown)}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-805 rounded-xl text-sm font-bold text-slate-800 dark:text-slate-200 select-none cursor-pointer flex justify-between items-center hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
                >
                  <span className="truncate">
                    {targetProduct ? `${targetProduct.gradeName} (${targetProduct.manufacturer})` : translate('未选择品级', 'No resin selected')}
                  </span>
                  <Search size={14} className="text-slate-400" />
                </div>

                <AnimatePresence>
                  {isOpenDropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.15 }}
                      className="absolute left-0 right-0 mt-2 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl z-50 overflow-hidden flex flex-col max-h-72"
                    >
                      <div className="p-3 border-b border-slate-100 dark:border-slate-850 shrink-0">
                        <input
                          autoFocus
                          type="text"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          placeholder={translate('拼音、品级、厂家过滤...', 'Filter grade, manufacturer...')}
                          className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold outline-none focus:ring-2 focus:ring-primary-500/20"
                        />
                      </div>
                      <div className="overflow-y-auto flex-1 custom-scrollbar">
                        {filteredSearchList.length > 0 ? (
                          filteredSearchList.map(p => (
                            <div
                              key={p.id}
                              onClick={() => {
                                setTargetId(p.id);
                                setIsOpenDropdown(false);
                                setSearchTerm('');
                              }}
                              className={`p-3 text-xs font-bold transition-all cursor-pointer border-b border-slate-50 dark:border-slate-900/40 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-900/60 ${
                                p.id === targetId ? 'text-primary-600 dark:text-primary-400 bg-primary-50/20 dark:bg-primary-950/10' : 'text-slate-700 dark:text-slate-300'
                              }`}
                            >
                              <div className="flex justify-between items-center">
                                <span className="font-extrabold">{p.gradeName}</span>
                                <span className="text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-850 px-1.5 py-0.5 rounded">
                                  {p.manufacturer}
                                </span>
                              </div>
                              <p className="text-[10px] text-slate-400 mt-1 line-clamp-1 truncate font-normal">
                                {p.manufacturer}
                              </p>
                            </div>
                          ))
                        ) : (
                          <div className="p-4 text-center text-xs text-slate-400 italic">
                            {translate('无匹配树脂', 'No products found')}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>

          {/* Configurable Vector Space Properties */}
          <div className="space-y-3 bg-slate-50/50 dark:bg-slate-950/20 border border-slate-100 dark:border-slate-850 rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <SlidersHorizontal size={13} />
                {translate('2. 配方向量特征与比重 (Weights)', '2. Select Vector Weights')}
              </label>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={() => {
                  const resetFeatures: Record<string, boolean> = {};
                  const resetWeights: Record<string, number> = {};
                  allNumericProperties.forEach(p => {
                    resetFeatures[p.key] = true;
                    resetWeights[p.key] = 1;
                  });
                  setSelectedFeatures(resetFeatures);
                  setFeatureWeights(resetWeights);
                }}
                className="text-[10px] font-black text-primary-600 dark:text-primary-400 uppercase tracking-tight flex items-center gap-1 hover:underline"
              >
                <RefreshCw size={10} /> Reset
              </motion.button>
            </div>

            <div className="space-y-3 pt-2 max-h-72 overflow-y-auto pr-1 py-1 custom-scrollbar">
              {allNumericProperties.map(f => {
                const isActive = selectedFeatures[f.key] === true;
                const weight = featureWeights[f.key] || 1;
                return (
                  <div
                    key={f.key}
                    className={`p-3 rounded-xl border transition-all ${
                      isActive
                        ? 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm'
                        : 'bg-slate-50/50 dark:bg-slate-900/20 border-transparent opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={isActive}
                          onChange={() => toggleFeature(f.key)}
                          className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                          {translate(f.labelZh, f.labelEn)}
                        </span>
                        {f.unit && (
                          <span className="text-[9px] font-mono font-medium text-slate-400">
                            ({f.unit})
                          </span>
                        )}
                      </label>
                      {isActive && (
                        <span className="text-[10px] font-black text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                          {weight}x 重
                        </span>
                      )}
                    </div>

                    {isActive && (
                      <div className="mt-2.5 flex items-center gap-3">
                        <span className="text-[9px] font-bold text-slate-400 shrink-0">Weight:</span>
                        <input
                          type="range"
                          min="1"
                          max="5"
                          step="1"
                          value={weight}
                          onChange={(e) => handleWeightChange(f.key, parseInt(e.target.value))}
                          className="flex-1 h-1 bg-slate-100 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary-500"
                        />
                        <div className="flex gap-0.5">
                          {[1, 2, 3, 4, 5].map((i) => (
                            <span
                              key={i}
                              className={`w-1.5 h-1.5 rounded-full ${
                                i <= weight ? 'bg-primary-500' : 'bg-slate-200 dark:bg-slate-705'
                              }`}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Result Column */}
        <div className="xl:col-span-7 flex flex-col space-y-4">
          <label className="text-xs font-extrabold text-slate-400 uppercase tracking-wider block">
            {translate('3. 雷达高维映射与搜索匹配结果 (Matches)', '3. Top Similar Resin Candidates')}
          </label>

          <div className="flex-1 space-y-4">
            {similarityResults.length > 0 ? (
              <div className="space-y-3.5">
                {similarityResults.map((result, idx) => {
                  const mId = result.product.id;
                  const scoreColor = 
                    result.score >= 90 ? 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/20 border-emerald-100' :
                    result.score >= 75 ? 'text-primary-600 bg-primary-50 dark:bg-primary-950/20 border-primary-100' :
                    'text-amber-500 bg-amber-50 dark:bg-amber-950/20 border-amber-100';

                  return (
                    <div
                      key={mId}
                      className="group p-4 bg-slate-50/40 dark:bg-slate-900/30 hover:bg-white dark:hover:bg-slate-900 border border-slate-150/60 dark:border-slate-850 hover:border-slate-250 hover:shadow-md hover:shadow-slate-100/50 dark:hover:shadow-none rounded-2xl transition-all flex flex-col space-y-3.5"
                    >
                      {/* Top Row Info */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded uppercase font-mono">
                              RANK #{idx + 1}
                            </span>
                            <span className="text-xs font-black text-rose-500 font-mono">
                              {result.product.categoryIds?.[0] || 'Resin'}
                            </span>
                          </div>
                          <h4 className="text-sm font-black text-slate-850 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                            {result.product.gradeName}
                          </h4>
                          <span className="text-[11px] font-bold text-slate-400 block">
                            {result.product.manufacturer}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <div className={`p-2 px-3 border rounded-xl text-center flex flex-col justify-center items-center ${scoreColor}`}>
                            <span className="text-[9px] font-extrabold uppercase tracking-tight block">Match score</span>
                            <span className="text-base font-black font-mono leading-none mt-0.5">{result.score}%</span>
                          </div>

                          {onViewProduct && (
                            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                              onClick={() => onViewProduct(result.product)}
                              title="Compare details and specifications"
                              className="p-2 bg-slate-100 dark:bg-slate-850 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-200 rounded-xl transition-all active:scale-95 border border-slate-200/20"
                            >
                              <ArrowUpRight size={14} />
                            </motion.button>
                          )}
                        </div>
                      </div>

                      {/* Attribute bar projection comparing candidates */}
                      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80">
                        {Object.entries(result.details).slice(0, 5).map(([key, item]) => {
                          const numericKey = allNumericProperties.find(np => np.key === key);
                          if (!numericKey) return null;

                          // Show comparison index
                          return (
                            <div key={key} className="space-y-1.5 p-2 bg-white dark:bg-slate-950 rounded-xl border border-slate-100 dark:border-slate-850">
                              <div className="flex items-center justify-between gap-1">
                                <span className="text-[9px] font-bold text-slate-400 truncate tracking-tight uppercase" title={translate(numericKey.labelZh, numericKey.labelEn)}>
                                  {translate(numericKey.labelZh, numericKey.labelEn).split('(')[0].trim()}
                                </span>
                              </div>
                              
                              <div className="space-y-1">
                                {/* candidate value */}
                                <div className="flex items-baseline justify-between gap-1 text-[10px] font-mono">
                                  <span className="text-slate-550 dark:text-slate-300 font-extrabold truncate max-w-[40px]">
                                    {item.candidateVal}
                                  </span>
                                  <span className="text-[9px] text-slate-400">
                                    {numericKey.unit}
                                  </span>
                                </div>

                                {/* relative match bars */}
                                <div className="w-full h-1 bg-slate-100 dark:bg-slate-850 rounded-full overflow-hidden relative">
                                  {/* reference target value marker */}
                                  <div
                                    className="absolute top-0 bottom-0 w-0.5 bg-rose-500/80 z-10"
                                    style={{ left: `${Math.min(100, item.targetNorm * 100)}%` }}
                                    title={`Reference Target Value indicator (${item.targetVal})`}
                                  />
                                  {/* candidate property filler */}
                                  <div
                                    className="h-full bg-primary-500/80"
                                    style={{ width: `${Math.min(100, item.candidateNorm * 100)}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <p className="text-[11px] text-slate-550 dark:text-slate-400 leading-normal bg-slate-100/50 dark:bg-slate-850/30 p-2.5 rounded-xl border border-slate-200/10">
                        {result.product.manufacturer || translate('无', 'N/A')} · {result.product.gradeName} 
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 bg-slate-50 dark:bg-slate-950/20 border border-dashed border-slate-250 dark:border-slate-800 rounded-3xl text-center space-y-3 flex flex-col items-center justify-center h-full min-h-[300px]">
                <BarChart2 size={32} className="text-slate-450 dark:text-slate-600 animate-pulse" />
                <div className="max-w-[280px]">
                  <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                    {translate('未激活配方向量空间维度', 'Empty Property Vectors')}
                  </h4>
                  <p className="text-xs text-slate-450 mt-1 leading-relaxed">
                    {translate('请在左边配置面板至少勾选一个有效的化学指标以投射向量相似矩阵。', 'Please activate at least 1 feature mapping vector in settings to calculate projections.')}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
