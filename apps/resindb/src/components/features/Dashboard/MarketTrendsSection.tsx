import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area
} from "recharts";
import { Product } from '@/types/index';
import { motion } from "motion/react";
import { TrendingUp, BarChart3, PieChart as PieChartIcon } from "lucide-react";

interface MarketTrendsSectionProps {
  products: Product[];
  t: (key: string, fallback?: string) => string;
}

export const MarketTrendsSection: React.FC<MarketTrendsSectionProps> = ({ products, t }) => {
  // 1. Manufacturer Distribution
  const mfgData = useMemo(() => {
    const counts: Record<string, number> = {};
    products.forEach(p => {
      counts[p.manufacturer] = (counts[p.manufacturer] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5); // Top 5
  }, [products]);

  // 2. Completeness Trends (Mocking some timeline if date is same, or aggregate by month)
  const timelineData = useMemo(() => {
    const months: Record<string, number> = {};
    products.forEach(p => {
      const month = p.createdAt?.substring(0, 7) || '2026-04';
      months[month] = (months[month] || 0) + 1;
    });
    return Object.entries(months)
      .map(([name, grades]) => ({ name, grades }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [products]);

  // 3. Property Distribution (e.g., MFR values range)
  const mfrDistribution = useMemo(() => {
    const bins: Record<string, number> = {
      '0-5': 0,
      '5-10': 0,
      '10-20': 0,
      '20-50': 0,
      '50+': 0
    };
    products.forEach(p => {
      const mfr = parseFloat(String(p.properties['mfr']?.value || 0));
      if (mfr <= 5) bins['0-5']++;
      else if (mfr <= 10) bins['5-10']++;
      else if (mfr <= 20) bins['10-20']++;
      else if (mfr <= 50) bins['20-50']++;
      else bins['50+']++;
    });
    return Object.entries(bins).map(([range, count]) => ({ range, count }));
  }, [products]);

  const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b'];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      {/* Manufacturer Share */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-slate-200/60 dark:border-slate-800/60 shadow-sm flex flex-col gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl">
            <PieChartIcon size={18} />
          </div>
          <h3 className="text-sm font-serif font-black tracking-tight text-slate-800 dark:text-slate-100">
            {t("manufacturerDistribution", "Manufacturer Share")}
          </h3>
        </div>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mfgData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {mfgData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ borderRadius: '1rem', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-2 gap-2 mt-auto">
          {mfgData.map((item, i) => (
            <div key={item.name} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
              <span className="text-[10px] font-mono text-slate-500 truncate">{item.name}</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Registration Velocity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-slate-200/60 dark:border-slate-800/60 shadow-sm flex flex-col gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-xl">
            <TrendingUp size={18} />
          </div>
          <h3 className="text-sm font-serif font-black tracking-tight text-slate-800 dark:text-slate-100">
            {t("registrationVelocity", "Portfolio Growth")}
          </h3>
        </div>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timelineData}>
              <defs>
                <linearGradient id="colorGrades" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="name" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: '#94a3b8' }} 
              />
              <Tooltip 
                contentStyle={{ borderRadius: '1rem', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
              />
              <Area 
                type="monotone" 
                dataKey="grades" 
                stroke="#10b981" 
                fillOpacity={1} 
                fill="url(#colorGrades)" 
                strokeWidth={3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* MFR Distribution */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-slate-200/60 dark:border-slate-800/60 shadow-sm flex flex-col gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-xl">
            <BarChart3 size={18} />
          </div>
          <h3 className="text-sm font-serif font-black tracking-tight text-slate-800 dark:text-slate-100">
            {t("mfrSpread", "MFR Range Analysis")}
          </h3>
        </div>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mfrDistribution}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis 
                dataKey="range" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 10, fill: '#94a3b8' }} 
              />
              <Tooltip 
                cursor={{ fill: 'rgba(245, 158, 11, 0.05)' }}
                contentStyle={{ borderRadius: '1rem', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
              />
              <Bar dataKey="count" fill="#f59e0b" radius={[6, 6, 0, 0]} barSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
};
