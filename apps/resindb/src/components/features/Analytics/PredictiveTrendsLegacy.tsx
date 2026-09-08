import { motion } from 'motion/react';
import React, { useMemo, useState } from 'react';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Bar,
  ReferenceLine
} from 'recharts';
import { TrendingUp, Activity, DollarSign, Package } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

export const PredictiveTrends: React.FC = () => {
  const { language } = useLanguage();

  // Generate synthetic historical and forecast data for demand and pricing
  const trendData = useMemo(() => {
    const data = [];
    const currentYear = new Date().getFullYear();
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    // Base values
    let basePrice = 2500; // USD per ton
    let baseDemand = 10000; // tons
    
    // Generate data for past 12 months + forecast next 6 months
    for (let i = -12; i <= 6; i++) {
        const date = new Date(currentYear, new Date().getMonth() + i, 1);
        const monthStr = `${months[date.getMonth()]} ${date.getFullYear().toString().substring(2)}`;
        
        const isForecast = i > 0;
        
        // Use Math.sin for deterministic pseudo-randomness within useMemo
        const pseudoRandom1 = (Math.sin(i * 12.345) + 1) / 2; // 0 to 1
        const pseudoRandom2 = (Math.cos(i * 67.890) + 1) / 2; // 0 to 1
        
        // Random walk for price and demand with slight upward trend
        basePrice = basePrice + (pseudoRandom1 * 100 - 45) + (isForecast ? 20 : 0);
        baseDemand = baseDemand + (pseudoRandom2 * 500 - 200) + (isForecast ? 100 : 0);
        
        // Ensure values remain somewhat realistic
        if (basePrice < 1000) basePrice = 1000;
        if (baseDemand < 5000) baseDemand = 5000;
        
        data.push({
            month: monthStr,
            price: Math.round(basePrice),
            demand: Math.round(baseDemand),
            isForecast,
            // Calculate a confidence interval for forecasts
            lowerBoundPrice: isForecast ? Math.round(basePrice * 0.9) : null,
            upperBoundPrice: isForecast ? Math.round(basePrice * 1.1) : null,
            lowerBoundDemand: isForecast ? Math.round(baseDemand * 0.85) : null,
            upperBoundDemand: isForecast ? Math.round(baseDemand * 1.15) : null,
        });
    }
    
    return data;
  }, []);

  const [activeChart, setActiveChart] = useState<'demand' | 'pricing' | 'combined'>('combined');

  return (
    <div className="p-6 h-full flex flex-col space-y-6 overflow-y-auto">
      {/* Header Overview */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 gap-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800 dark:text-slate-100">
            <TrendingUp size={24} className="text-indigo-500" />
            {language === 'zh' ? '预测趋势与分析' : 'Predictive Trends'}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {language === 'zh' 
              ? '基于历史数据的树脂需求和价格预测分析' 
              : 'Forecasted resin demand and pricing based on historical data patterns.'}
          </p>
        </div>
        
        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
            onClick={() => setActiveChart('combined')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeChart === 'combined' ? 'bg-white dark:bg-slate-700 shadow-sm text-indigo-600 dark:text-indigo-400' : 'text-slate-600 dark:text-slate-400'}`}
          >
            {language === 'zh' ? '综合趋势' : 'Combined'}
          </motion.button>
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
            onClick={() => setActiveChart('demand')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeChart === 'demand' ? 'bg-white dark:bg-slate-700 shadow-sm text-indigo-600 dark:text-indigo-400' : 'text-slate-600 dark:text-slate-400'}`}
          >
             {language === 'zh' ? '需求量' : 'Demand'}
          </motion.button>
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
            onClick={() => setActiveChart('pricing')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeChart === 'pricing' ? 'bg-white dark:bg-slate-700 shadow-sm text-indigo-600 dark:text-indigo-400' : 'text-slate-600 dark:text-slate-400'}`}
          >
             {language === 'zh' ? '价格' : 'Pricing'}
          </motion.button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
         <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col shadow-sm">
            <div className="text-sm text-slate-500 flex items-center gap-2 mb-2 font-medium">
               <DollarSign size={16} className="text-emerald-500"/>
               {language === 'zh' ? '当前平均价格' : 'Current Avg Price'}
            </div>
            <div className="text-2xl font-bold text-slate-800 dark:text-slate-100">
               ${trendData[12].price.toLocaleString()} <span className="text-sm font-normal text-slate-500">/ ton</span>
            </div>
         </div>
         <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col shadow-sm">
            <div className="text-sm text-slate-500 flex items-center gap-2 mb-2 font-medium">
               <Package size={16} className="text-blue-500"/>
               {language === 'zh' ? '当前预估需求' : 'Current Est. Demand'}
            </div>
            <div className="text-2xl font-bold text-slate-800 dark:text-slate-100">
               {trendData[12].demand.toLocaleString()} <span className="text-sm font-normal text-slate-500">tons</span>
            </div>
         </div>
         <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col shadow-sm">
            <div className="text-sm text-slate-500 flex items-center gap-2 mb-2 font-medium">
               <Activity size={16} className="text-indigo-500"/>
               {language === 'zh' ? '6月趋势预测' : '6-Mo Trend Forecast'}
            </div>
            <div className="text-2xl font-bold text-emerald-600">
               +{( ((trendData[18].price - trendData[12].price) / trendData[12].price) * 100).toFixed(1)}% <span className="text-sm font-normal text-slate-500">Price</span>
            </div>
         </div>
      </div>

      {/* Main Chart Container */}
      <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm min-h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={trendData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }} tickMargin={10} axisLine={false} tickLine={false} />
            
            {/* Left Y Axis - Demand */}
            {(activeChart === 'combined' || activeChart === 'demand') && (
              <YAxis 
                yAxisId="left" 
                tick={{ fill: '#64748b', fontSize: 12 }} 
                axisLine={false} 
                tickLine={false} 
                tickFormatter={(value) => `${(value / 1000).toFixed(1)}k`}
                domain={['auto', 'auto']}
              />
            )}
            
            {/* Right Y Axis - Pricing */}
            {(activeChart === 'combined' || activeChart === 'pricing') && (
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                tick={{ fill: '#64748b', fontSize: 12 }} 
                axisLine={false} 
                tickLine={false}
                tickFormatter={(value) => `$${value}`}
                domain={['auto', 'auto']}
              />
            )}
            
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }}
              itemStyle={{ color: '#f8fafc' }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            
            {/* Reference Line for Current Month (Forecast start) */}
            <ReferenceLine x={trendData[12].month} stroke="#94a3b8" strokeDasharray="3 3" label={{ position: 'top', value: 'Forecast', fill: '#94a3b8', fontSize: 12 }} />

            {/* Demand Areas & Bars */}
            {(activeChart === 'combined' || activeChart === 'demand') && (
               <>
                 {/* Demand Forecast Bounds */}
                 <Area yAxisId="left" type="monotone" dataKey="upperBoundDemand" stroke="none" fill="#3b82f6" fillOpacity={0.1} activeDot={false} name="Demand Upper Bound" />
                 <Area yAxisId="left" type="monotone" dataKey="lowerBoundDemand" stroke="none" fill="#eff6ff" fillOpacity={0.5} activeDot={false} name="Demand Lower Bound" />
                 
                 {/* Main Demand Line/Bar */}
                 <Bar yAxisId="left" dataKey="demand" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={20} name={language === 'zh' ? "需求量 (吨)" : "Demand (tons)"} />
               </>
            )}

            {/* Pricing Lines */}
            {(activeChart === 'combined' || activeChart === 'pricing') && (
                <>
                  {/* Price Forecast Bounds */}
                  <Area yAxisId="right" type="monotone" dataKey="upperBoundPrice" stroke="none" fill="#10b981" fillOpacity={0.1} activeDot={false} name="Price Upper Bound" />
                  <Area yAxisId="right" type="monotone" dataKey="lowerBoundPrice" stroke="none" fill="#f0fdf4" fillOpacity={0.5} activeDot={false} name="Price Lower Bound" />
                  
                  {/* Main Pricing Line */}
                  <Line yAxisId="right" type="monotone" dataKey="price" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 6 }} name={language === 'zh' ? "价格 ($/吨)" : "Price ($/ton)"} />
                </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
