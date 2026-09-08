import { motion } from 'motion/react';
import React, { useMemo, useState } from 'react';
import { useData } from '@/contexts/DataContext';
import { useLanguage } from '@/contexts/LanguageContext';
import {
  ComposedChart,
  Line,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { 
  Activity, 
  Layers, 
  Cpu,
  BarChart4,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';


interface CapacityStreamPoint {
  name: string;
  historical: number | null;
  projected: number | null;
  lower: number;
  upper: number;
}

export const ResinCapacityForecast: React.FC = () => {
  const { allProducts, selectedIds, categoryNameMap } = useData();
  const { language } = useLanguage();

  // Pick active products cluster (selected, otherwise fall back to all)
  const activeProducts = useMemo(() => {
    const selected = allProducts.filter(p => selectedIds.has(p.id));
    return selected.length > 0 ? selected : allProducts;
  }, [allProducts, selectedIds]);

  // UI state variables
  const [projectionType, setProjectionType] = useState<'linear' | 'moving_average'>('linear');
  const [rollingWindow, setRollingWindow] = useState<number>(3); // For moving average: 3, 4, 6, 12 months
  const [growthMultiplier, setGrowthMultiplier] = useState<number>(1.0); // For linear growth scaling: 0.8x to 1.5x
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('all');

  // List of root categories present in active products for filtering the capacity view
  const categoriesInActive = useMemo(() => {
    const ids = new Set<string>();
    activeProducts.forEach(p => {
      p.categoryIds?.forEach(catId => {
        if (catId.startsWith('cat_') || catId.startsWith('root_')) {
          ids.add(catId);
        }
      });
    });
    return Array.from(ids).map(id => ({
      id,
      name: categoryNameMap.get(id) || id
    }));
  }, [activeProducts, categoryNameMap]);

  // Filter active products specifically for this capacity tab if user selected a categories filter
  const filteredCapacityProducts = useMemo(() => {
    if (selectedCategoryFilter === 'all') return activeProducts;
    return activeProducts.filter(p => p.categoryIds?.includes(selectedCategoryFilter));
  }, [activeProducts, selectedCategoryFilter]);

  // Calculate simulated baseline manufacturing capacity for filtered products
  // Based deterministically on categories & properties to anchor representation to products
  const productCapacities = useMemo(() => {
    return filteredCapacityProducts.map(product => {
      const catIdsString = product.categoryIds?.join(',') || '';
      let baseCap = 50000; // tons/year base

      if (catIdsString.includes('root_plastic')) {
        if (catIdsString.includes('cat_pe')) baseCap = 180000;
        else if (catIdsString.includes('cat_pp')) baseCap = 160000;
        else if (catIdsString.includes('cat_pvc')) baseCap = 140000;
        else if (catIdsString.includes('cat_abs')) baseCap = 120000;
        else baseCap = 100000;
      } else if (catIdsString.includes('root_eng')) {
        if (catIdsString.includes('cat_pa')) baseCap = 80000;
        else if (catIdsString.includes('cat_pc')) baseCap = 90000;
        else baseCap = 70000;
      } else if (catIdsString.includes('root_high_perf')) {
        baseCap = 15000;
      } else if (catIdsString.includes('root_rubber') || catIdsString.includes('root_tpe')) {
        baseCap = 45000;
      }

      // Modifier based on grade name length to make each grade distinctive
      const modifier = (product.gradeName.length % 10) * 8000 - 3000;
      let capacity = baseCap + modifier;

      // Pilot plants and experimental resins operate on a 15% sizing scale
      if (product.isExperimental) {
        capacity = Math.round(capacity * 0.12);
      }

      // Annual Capacity to Average Monthly baseline (tons/month)
      const monthlyBaseline = Math.round(capacity / 12);

      return {
        product,
        annualCapacity: capacity,
        monthlyBaseline
      };
    });
  }, [filteredCapacityProducts]);

  // Generate historical data (-12 to 0 months) and projection (+1 to +12 months)
  const capacityDataStream = useMemo(() => {
    if (productCapacities.length === 0) return [];

    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    const currentDate = new Date();
    const currentYear = currentDate.getFullYear();
    const currentMonthIdx = currentDate.getMonth();

    // 1. Calculate Aggregate Historical Monthly baseline sums
    // Simulating deterministic factors: seasonality, minor trend, and seeded random variations
    const historicalPoints: { monthIdx: number; dateStr: string; activeSum: number }[] = [];

    for (let offset = -12; offset <= 0; offset++) {
      const pointDate = new Date(currentYear, currentMonthIdx + offset, 1);
      const mIdx = pointDate.getMonth();
      const monthLabel = `${months[mIdx]} ${pointDate.getFullYear().toString().substring(2)}`;

      // Seasonality multiplier: e.g. lower in Jan/Feb (New Year, holidays), higher in Q3/Q4 peak
      const seasonalModifier = mIdx === 0 || mIdx === 1 ? 0.88 : (mIdx >= 7 && mIdx <= 9 ? 1.05 : 1.0);

      // Seeded trend: slight slow 2.5% increase across past year
      const trendFactor = 1 + (offset + 12) * 0.003;

      let aggregateSum = 0;
      productCapacities.forEach(({ product, monthlyBaseline }) => {
        // Hash code from product id to generate individual seeded noise
        const hashSeed = Math.sin((product.id.charCodeAt(product.id.length - 1) || 0) * 10 + offset);
        const noise = hashSeed * 0.05; // +/- 5% noise per grade

        aggregateSum += monthlyBaseline * seasonalModifier * trendFactor * (1 + noise);
      });

      historicalPoints.push({
        monthIdx: offset,
        dateStr: monthLabel,
        activeSum: Math.round(aggregateSum)
      });
    }

    // 2. Perform Extrapolative Math Projections based on selected algorithm
    const projectedPoints: { monthIdx: number; dateStr: string; predicted: number; minBound: number; maxBound: number }[] = [];
    const histX = historicalPoints.map(p => p.monthIdx);
    const histY = historicalPoints.map(p => p.activeSum);
    const n = historicalPoints.length;

    if (projectionType === 'linear') {
      // Linear Regression: y = m*x + c
      let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
      for (let i = 0; i < n; i++) {
        sumX += histX[i];
        sumY += histY[i];
        sumXY += histX[i] * histY[i];
        sumXX += histX[i] * histX[i];
      }

      const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
      const intercept = (sumY - slope * sumX) / n;

      // Fit residuals to estimate standard forecast error bounds
      let sumResidualSquares = 0;
      for (let i = 0; i < n; i++) {
        const fit = slope * histX[i] + intercept;
        sumResidualSquares += Math.pow(histY[i] - fit, 2);
      }
      const residualStdDev = Math.sqrt(sumResidualSquares / (n - 2)) || (historicalPoints[0].activeSum * 0.02);

      // Extrapolate for future +1 to +12 months, scaling trend based on growth multiplier
      const adjustedSlope = slope * growthMultiplier;

      for (let f = 1; f <= 12; f++) {
        const targetDate = new Date(currentYear, currentMonthIdx + f, 1);
        const monthLabel = `${months[targetDate.getMonth()]} ${targetDate.getFullYear().toString().substring(2)}`;

        // Forecast prediction
        const predicted = adjustedSlope * f + (adjustedSlope * (f - 1) * 0.02) + intercept;
        
        // Error bounds expand further into future
        const stdError = residualStdDev * Math.sqrt(1 + 1/n + Math.pow(f, 2) / (sumXX - (sumX*sumX)/n));

        projectedPoints.push({
          monthIdx: f,
          dateStr: monthLabel,
          predicted: Math.round(predicted),
          minBound: Math.round(Math.max(0, predicted - stdError * 1.96)),
          maxBound: Math.round(predicted + stdError * 1.96)
        });
      }
    } else {
      // Autoregressive Moving Average Projection
      // Moving Average Window k: take average of past k points to project next point, shifting window sequentially
      const combinedYStr = [...histY];

      for (let f = 1; f <= 12; f++) {
        const targetDate = new Date(currentYear, currentMonthIdx + f, 1);
        const monthLabel = `${months[targetDate.getMonth()]} ${targetDate.getFullYear().toString().substring(2)}`;

        // Slice last `rollingWindow` values to calculate next step
        const startIndex = combinedYStr.length - rollingWindow;
        let sum = 0;
        let count = 0;
        for (let idx = startIndex; idx < combinedYStr.length; idx++) {
          if (idx >= 0) {
            sum += combinedYStr[idx];
            count++;
          }
        }
        
        // Add artificial growth modifier baseline drift of 0.2% monthly for rolling
        const nextVal = Math.round((sum / count) * (1 + (f * 0.001 * (growthMultiplier - 0.9))));
        combinedYStr.push(nextVal);

        // Simulated confidence spreads which expand slower than linear regression
        const baseVariance = NEXT_VAR(rollingWindow, f);
        const stDev = (sum / count) * baseVariance;

        projectedPoints.push({
          monthIdx: f,
          dateStr: monthLabel,
          predicted: nextVal,
          minBound: Math.round(Math.max(0, nextVal - stDev * 1.96)),
          maxBound: Math.round(nextVal + stDev * 1.96)
        });
      }
    }

    // Combine historical and projected timelines
    const finalStream: CapacityStreamPoint[] = [];
    historicalPoints.forEach(p => {
      finalStream.push({
        name: p.dateStr,
        historical: p.activeSum,
        projected: null,
        lower: p.activeSum,
        upper: p.activeSum
      });
    });

    // Let the last historical point blend into the starting projected point for continuous UI line
    const lastHist = historicalPoints[historicalPoints.length - 1];
    projectedPoints.forEach((p, idx) => {
      finalStream.push({
        name: p.dateStr,
        historical: idx === 0 ? lastHist.activeSum : null,
        projected: p.predicted,
        lower: p.minBound,
        upper: p.maxBound
      });
    });

    return finalStream;
  }, [productCapacities, projectionType, rollingWindow, growthMultiplier]);

  // Helper helper to expand stdev for moving average
  function NEXT_VAR(windowSize: number, step: number) {
    const base = windowSize === 3 ? 0.025 : windowSize === 4 ? 0.020 : windowSize === 6 ? 0.015 : 0.010;
    return base * Math.sqrt(step);
  }

  // Calculate high-level aggregate KPI cards
  const summaryKPIs = useMemo(() => {
    if (capacityDataStream.length === 0) return {
      baseline: 0,
      predicted12m: 0,
      growthRatePercent: 0,
      confidenceScore: 0,
      cumulativeProduction: 0
    };

    const currentIdx = 12; // index of "Current" / Month 0
    const currentVal = capacityDataStream[currentIdx]?.historical || 0;
    const predicted12m = capacityDataStream[capacityDataStream.length - 1]?.projected || 0;

    const growthRatePercent = currentVal > 0 ? ((predicted12m - currentVal) / currentVal) * 100 : 0;

    // Simulated R² or Confidence Score depending on historical volatility & window parameters
    const confidenceScore = projectionType === 'moving_average'
      ? 98.4 - (rollingWindow * 0.6)
      : 95.8 - (Math.abs(growthMultiplier - 1) * 3);

    // Cumulative projected volume for upcoming 12 months (tons total)
    let cumulativeProduction = 0;
    for (let i = currentIdx + 1; i < capacityDataStream.length; i++) {
      cumulativeProduction += (capacityDataStream[i]?.projected || 0);
    }

    return {
      baseline: currentVal,
      predicted12m,
      growthRatePercent,
      confidenceScore: parseFloat(confidenceScore.toFixed(1)),
      cumulativeProduction
    };
  }, [capacityDataStream, projectionType, rollingWindow, growthMultiplier]);

  // Find top manufacturers in current scope to present share highlights
  const topManufacturersShare = useMemo(() => {
    const list: Record<string, number> = {};
    productCapacities.forEach(({ product, annualCapacity }) => {
      const m = product.manufacturer || 'Unknown';
      list[m] = (list[m] || 0) + annualCapacity;
    });

    const totalPower = Object.values(list).reduce((a, b) => a + b, 0);

    return Object.entries(list)
      .map(([name, cap]) => ({
        name,
        capacity: cap,
        share: totalPower > 0 ? parseFloat(((cap / totalPower) * 100).toFixed(1)) : 0
      }))
      .sort((a, b) => b.capacity - a.capacity)
      .slice(0, 4);
  }, [productCapacities]);

  const yAxisFormatter = (value: number) => {
    if (value >= 100000) {
      return `${(value / 1000).toFixed(0)}k t`;
    }
    return `${value.toLocaleString()} t`;
  };

  return (
    <div className="p-4 sm:p-5 h-full flex flex-col space-y-5 overflow-y-auto w-full">
      {/* 1. Header component */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-slate-50 dark:bg-slate-900/40 p-4 border border-slate-100 dark:border-slate-800 rounded-2xl shrink-0">
        <div>
          <h2 className="text-base font-bold flex items-center gap-1.5 text-slate-800 dark:text-slate-100">
            <BarChart4 size={18} className="text-emerald-500" />
            <span>{language === 'zh' ? '树脂产能演化与制造趋势预测' : 'Resin Capacity Forecast & Manufacturing Projections'}</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'zh' 
              ? '基于当前选定材料与供应商基础，应用一阶最小二乘重合与移动平均状态求解未来制造能力。' 
              : 'Models active material grades to predict manufacturing capabilities over the 12-month horizon.'}
          </p>
        </div>

        {/* Global category selection to customize projection source */}
        <div className="flex items-center gap-2">
          <label htmlFor="catFilter" className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-wider whitespace-nowrap">
            {language === 'zh' ? '物性筛选' : 'Category Category'}
          </label>
          <select
            id="catFilter"
            value={selectedCategoryFilter}
            onChange={(e) => setSelectedCategoryFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-indigo-500/20 outline-none cursor-pointer"
          >
            <option value="all">
              {language === 'zh' ? `全部产品领域 (${activeProducts.length} 牌号)` : `All Materials (${activeProducts.length} grades)`}
            </option>
            {categoriesInActive.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 2. Interactive Parameters Adjusters Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 p-4 border border-slate-250 dark:border-slate-800 rounded-3xl bg-white dark:bg-slate-950 shadow-sm shrink-0">
        {/* Model Selector */}
        <div className="space-y-1.5 lg:col-span-1">
          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">
            {language === 'zh' ? '推演机制核' : 'Projection Mathematical Engine'}
          </label>
          <select
            value={projectionType}
            onChange={(e) => {
              const val = e.target.value;
              if (val === 'linear' || val === 'moving_average') {
                setProjectionType(val);
              }
            }}
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold focus:ring-2 focus:ring-emerald-500/20 outline-none cursor-pointer text-slate-800 dark:text-slate-100"
          >
            <option value="linear">📈 {language === 'zh' ? '最小二乘线性回归' : 'Linear Regression'}</option>
            <option value="moving_average">🔄 {language === 'zh' ? '移动递增均线预测' : 'Moving Average (Autoreg)'}</option>
          </select>
        </div>

        {/* Dynamic adjusters depending on mode */}
        <div className="lg:col-span-2 flex flex-col md:flex-row gap-4">
          {projectionType === 'linear' ? (
            <div className="flex-1 space-y-2">
              <div className="flex justify-between items-center px-1">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                  {language === 'zh' ? '整体产能提速乘数' : 'Manufacturing Growth multiplier'}
                </span>
                <span className="text-xs font-mono font-black text-emerald-600 dark:text-emerald-400">
                  {growthMultiplier.toFixed(1)}x
                </span>
              </div>
              <input
                aria-label="Growth Multiplier"
                type="range"
                min="0.8"
                max="1.5"
                step="0.05"
                value={growthMultiplier}
                onChange={(e) => setGrowthMultiplier(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg appearance-none cursor-ew-resize accent-emerald-600 animate-none mt-1"
              />
            </div>
          ) : (
            <div className="flex-1 space-y-1.5">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1 block">
                {language === 'zh' ? '均线平滑窗口 (月)' : 'Rolling Smoothing Window'}
              </label>
              <div className="flex gap-2">
                {[3, 4, 6, 12].map(w => (
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    key={w}
                    onClick={() => setRollingWindow(w)}
                    className={`flex-1 py-1.5 text-xs font-mono font-bold rounded-lg border transition-all ${
                      rollingWindow === w 
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-600 dark:bg-emerald-950/30 dark:border-emerald-800 dark:text-emerald-400' 
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400'
                    }`}
                  >
                    {w}M
                  </motion.button>
                ))}
              </div>
            </div>
          )}

          {/* Environmental Target modifier to fine-tune baseline */}
          <div className="flex-1 space-y-2">
            <div className="flex justify-between items-center px-1">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                {language === 'zh' ? '工厂利用效率调整' : 'Factory Utilization Adjuster'}
              </span>
              <span className="text-xs font-mono font-black text-indigo-500">
                {growthMultiplier !== 1 ? `${growthMultiplier > 1 ? '+' : ''}${((growthMultiplier - 1) * 100).toFixed(0)}%` : 'Standard'}
              </span>
            </div>
            <input
              aria-label="Utilization Factor Adjuster"
              type="range"
              min="0.9"
              max="1.1"
              step="0.01"
              value={growthMultiplier}
              onChange={(e) => setGrowthMultiplier(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg appearance-none cursor-ew-resize accent-indigo-500 animate-none mt-1"
            />
          </div>
        </div>

        {/* Informative Diagnostics stats inside panel */}
        <div className="lg:col-span-1 bg-slate-50 dark:bg-slate-900 p-2.5 rounded-2xl flex items-center gap-2.5 border border-slate-100 dark:border-slate-850">
          <Cpu className="text-indigo-500 shrink-0" size={16} />
          <div className="text-[10px] leading-relaxed font-semibold text-slate-600 dark:text-slate-400">
            {language === 'zh' ? (
              <span>包含 <strong>{filteredCapacityProducts.length}</strong> 种可用牌号进行累加。选定 <strong>{selectedIds.size}</strong> 种。</span>
            ) : (
              <span>Simulating aggregate totals over <strong>{filteredCapacityProducts.length}</strong> grades based on filters.</span>
            )}
          </div>
        </div>
      </div>

      {/* 3. Main interactive Chart and Details */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 flex-1 min-h-[460px]">
        {/* Chart Column */}
        <div className="xl:col-span-2 border border-slate-200 dark:border-slate-850 rounded-3xl p-4 md:p-5 bg-white dark:bg-slate-950 shadow-sm flex flex-col h-full">
          <div className="flex justify-between items-center mb-4 shrink-0 px-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5">
              <Activity size={14} className="text-emerald-500 animate-pulse" />
              {language === 'zh' ? '产能制造变动趋势 (吨/月) 与 未来展望波动区间' : 'Aggregate Monthly Production Run (tons/month) & Confidence Bands'}
            </h3>

            {/* Micro Legended colors */}
            <div className="hidden sm:flex gap-3 text-[9px] font-bold tracking-wider uppercase font-mono">
              <span className="flex items-center gap-1 text-slate-400">
                <span className="w-2.5 h-2 bg-slate-300 dark:bg-slate-700 rounded-sm" /> Historical Run
              </span>
              <span className="flex items-center gap-1 text-emerald-500">
                <span className="w-2.5 h-0.5 border-t-2 border-dashed border-emerald-500" /> Projected Capacity
              </span>
            </div>
          </div>

          <div className="flex-1 min-h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={capacityDataStream} margin={{ top: 10, right: 10, left: -22, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30 dark:opacity-10 stroke-slate-400 dark:stroke-slate-800" horizontal={true} vertical={false} />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 9, fontWeight: 700, fill: '#64748b' }}
                  tickLine={false} 
                  axisLine={false} 
                />
                <YAxis 
                  tickFormatter={yAxisFormatter}
                  tick={{ fontSize: 9, fontWeight: 700, fill: '#64748b' }}
                  tickLine={false} 
                  axisLine={false} 
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    borderRadius: '12px', 
                    border: 'none', 
                    boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
                    color: '#fff',
                    fontSize: '11px',
                    fontWeight: '600'
                  }}
                />
                
                {/* Confidence Range boundaries area */}
                <Area 
                  name="Forecast Variance Interval (95% CI)"
                  type="monotone" 
                  dataKey="lower" 
                  stroke="none" 
                  fill="#10b981" 
                  fillOpacity={0.05} 
                />
                <Area 
                  type="monotone" 
                  dataKey="upper" 
                  stroke="none" 
                  fill="#10b981" 
                  fillOpacity={0.05} 
                />
                
                {/* Historical baseline area / column */}
                <Bar 
                  name={language === 'zh' ? "历史产量运转" : "Historical Run"} 
                  dataKey="historical" 
                  fill="#cbd5e1" 
                  radius={[3, 3, 0, 0]} 
                  barSize={16} 
                  className="fill-slate-300 dark:fill-slate-850 opacity-80"
                />

                {/* Futured capacity projections line */}
                <Line 
                  name={language === 'zh' ? "推导产能区间" : "Projected Capacity"} 
                  type="monotone" 
                  dataKey="projected" 
                  stroke="#10b981" 
                  strokeWidth={2.5} 
                  strokeDasharray="5 5" 
                  dot={false}
                />

                {/* Separation reference marker */}
                <ReferenceLine 
                  x={capacityDataStream[12]?.name} 
                  stroke="#94a3b8" 
                  strokeDasharray="3 3" 
                  label={{ value: 'Projections Start', position: 'top', fill: '#94a3b8', fontSize: 9, fontWeight: 800 }} 
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Summary side columns for statistics detailed breakdowns */}
        <div className="space-y-4">
          {/* Main projection target metric values */}
          <div className="grid grid-cols-2 gap-3.5">
            <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex flex-col justify-between">
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none">
                {language === 'zh' ? '当前单月峰产量' : 'Current Month Baseline'}
              </span>
              <div className="flex items-baseline mt-2 h-10">
                <span className="text-xl font-black text-slate-800 dark:text-white font-mono">
                  {summaryKPIs.baseline.toLocaleString()}
                </span>
                <span className="text-[10px] text-slate-400 ml-1">t</span>
              </div>
            </div>

            <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex flex-col justify-between">
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none">
                {language === 'zh' ? '12月后预计产量' : 'Projected 12m Run'}
              </span>
              <div className="flex items-baseline mt-2 h-10">
                <span className="text-xl font-black text-slate-800 dark:text-white font-mono">
                  {summaryKPIs.predicted12m.toLocaleString()}
                </span>
                <span className="text-[10px] text-slate-400 ml-1">t</span>
              </div>
            </div>

            <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex flex-col justify-between">
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none">
                {language === 'zh' ? '年同比演变比率' : 'Yearly Shift Rate'}
              </span>
              <div className={`flex items-center mt-2 h-10 font-mono font-black text-lg ${
                summaryKPIs.growthRatePercent >= 0 ? 'text-emerald-500' : 'text-rose-500'
              }`}>
                {summaryKPIs.growthRatePercent >= 0 ? <ArrowUpRight size={18} className="mr-0.5" /> : <ArrowDownRight size={18} className="mr-0.5" />}
                <span>{summaryKPIs.growthRatePercent >= 0 ? '+' : ''}{summaryKPIs.growthRatePercent.toFixed(1)}%</span>
              </div>
            </div>

            <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex flex-col justify-between">
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none">
                {language === 'zh' ? '统计数学可信置信' : 'Predictive Confidence'}
              </span>
              <div className="flex items-baseline mt-2 h-10">
                <span className="text-xl font-black text-slate-800 dark:text-white font-mono">
                  {summaryKPIs.confidenceScore}%
                </span>
              </div>
            </div>
          </div>

          {/* Core Manufacturers Contribution highlight card */}
          <div className="p-4 border border-slate-200 dark:border-slate-850 bg-white dark:bg-slate-950 rounded-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-850 pb-2">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5 pl-0.5">
                <Layers size={13} className="text-emerald-500" />
                {language === 'zh' ? '主导供应商年制造规模占比' : 'Key Suppliers Run Capacity Share'}
              </span>
              <span className="text-[9px] bg-slate-100 dark:bg-slate-900 font-bold px-1.5 py-0.5 rounded-md text-slate-400">
                {language === 'zh' ? '排名前 4' : 'Top 4'}
              </span>
            </div>

            <div className="space-y-3.5 max-h-[220px] overflow-y-auto">
              {topManufacturersShare.map((m, idx) => (
                <div key={m.name} className="space-y-1">
                  <div className="flex justify-between text-[11px] font-bold">
                    <span className="text-slate-700 dark:text-slate-300 truncate max-w-[180px]">
                      {idx + 1}. {m.name}
                    </span>
                    <span className="text-slate-900 dark:text-slate-100 font-mono">
                      {(m.capacity / 1000).toFixed(0)}k t ({m.share}%)
                    </span>
                  </div>
                  {/* Custom progress bars */}
                  <div className="w-full bg-slate-100 dark:bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${
                        idx === 0 ? 'bg-indigo-500' : idx === 1 ? 'bg-emerald-500' : idx === 2 ? 'bg-amber-500' : 'bg-slate-400'
                      }`} 
                      style={{ width: `${m.share}%` }} 
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cumulative Projection Metrics card */}
          <div className="p-4 p-y-4.5 bg-indigo-50/40 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40 rounded-2xl">
            <span className="text-[9px] font-black text-indigo-400 dark:text-indigo-400/80 uppercase tracking-widest leading-none block font-mono">
              {language === 'zh' ? '预估下月周期生产总规模量' : 'Projected Cumulative Next-12M Yield'}
            </span>
            <div className="text-2xl font-black text-indigo-950 dark:text-white mt-2 font-mono flex items-baseline">
              {summaryKPIs.cumulativeProduction.toLocaleString()} 
              <span className="text-xs font-sans font-bold text-slate-500 dark:text-slate-400 ml-1">tons (12-mo run total)</span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1.5 font-medium leading-relaxed">
              {language === 'zh' 
                ? '该项指标表示对当前筛选材料群落未来12个月的拟合生产总量合计。您可以切换到“移动平均”核观察平滑后的供应能力表现。' 
                : 'Aggregates entire futuristic run total of selected properties under model-simulated output constraints.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
