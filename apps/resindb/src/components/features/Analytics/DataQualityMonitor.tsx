import { motion } from 'motion/react';
import React, { useEffect, useState, useMemo } from 'react';
import { useDataQualityWorker } from '@/hooks/workers/useDataQualityWorker';
import { Product } from '@/types/index';
import { 
  AlertTriangle, CheckCircle2, BadgeInfo,
  Sliders, Loader2, Search, Filter
} from 'lucide-react';

interface DataQualityMonitorProps {
  products: Product[];
}

export const DataQualityMonitor: React.FC<DataQualityMonitorProps> = ({ products }) => {
  const { isAnomalizing, result, error, runQualityCheck } = useDataQualityWorker();
  
  // Interactive thresholds & parameters
  const [zThreshold, setZThreshold] = useState<number>(3);
  const [iqrMultiplier, setIqrMultiplier] = useState<number>(1.5);
  const [activeTab, setActiveTab] = useState<'outliers' | 'missing' | 'stats'>('outliers');
  
  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'all' | 'extreme' | 'moderate'>('all');
  const [missingUrgencyFilter, setMissingUrgencyFilter] = useState<'all' | 'critical' | 'high' | 'normal'>('all');

  // Trigger analysis on load and whenever products, zThreshold, or iqrMultiplier change
  useEffect(() => {
    if (products?.length > 0) {
      runQualityCheck(products, {
        zThreshold,
        iqrMultiplier
      });
    }
  }, [products, zThreshold, iqrMultiplier, runQualityCheck]);

  // Handle Search & Filter on Outliers
  const filteredOutliers = useMemo(() => {
    if (!result?.outliers) return [];
    return result.outliers.filter(item => {
      const matchSearch = 
        item.gradeName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.manufacturer.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.propertyKey.toLowerCase().includes(searchQuery.toLowerCase());
      
      const absZ = Math.abs(item.stats.zScore);
      let matchSeverity = true;
      if (severityFilter === 'extreme') matchSeverity = absZ >= 4;
      if (severityFilter === 'moderate') matchSeverity = absZ >= 2 && absZ < 4;

      return matchSearch && matchSeverity;
    });
  }, [result, searchQuery, severityFilter]);

  // Handle Search & Filter on Missing Values
  const filteredMissing = useMemo(() => {
    if (!result?.missing) return [];
    return result.missing.filter(item => {
      const matchSearch = 
        item.gradeName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.manufacturer.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.propertyKey.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchUrgency = missingUrgencyFilter === 'all' || item.importance === missingUrgencyFilter;
      
      return matchSearch && matchUrgency;
    });
  }, [result, searchQuery, missingUrgencyFilter]);


  if (isAnomalizing && !result) {
    return (
      <div className="flex flex-col items-center justify-center p-12 min-h-[400px] text-center space-y-4">
        <Loader2 className="animate-spin text-indigo-600 dark:text-indigo-400" size={32} />
        <div className="space-y-1">
          <p className="text-sm font-bold text-slate-800 dark:text-white">
            Running Data Quality Profiler...
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 italic">
            Scanning multi-dimensional points and computing interquartile boundaries in the web background...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-rose-50 dark:bg-rose-950/20 border border-rose-150 dark:border-rose-900/30 rounded-3xl flex items-start gap-4">
        <AlertTriangle className="text-rose-500 mt-1 shrink-0" size={20} />
        <div>
          <h3 className="text-sm font-black text-rose-800 dark:text-rose-400 uppercase tracking-wider">Quality Monitor Error</h3>
          <p className="text-xs text-rose-600 dark:text-rose-450 mt-1">{error}</p>
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
            onClick={() => runQualityCheck(products, { zThreshold, iqrMultiplier })}
            className="mt-3 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all"
          >
            Retry Diagnostics
          </motion.button>
        </div>
      </div>
    );
  }

  const healthScore = result?.healthScore ?? 100;
  
  // Custom helper for coloring health score
  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10';
    if (score >= 75) return 'text-indigo-500 border-indigo-500/30 bg-indigo-500/10';
    if (score >= 50) return 'text-amber-500 border-amber-500/30 bg-amber-500/10';
    return 'text-rose-500 border-rose-500/30 bg-rose-500/10';
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Dynamic Threshold Configurations */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Quality Health Score Card */}
        <div className={`md:col-span-1 p-6 border rounded-3xl flex flex-col items-center justify-center text-center space-y-3 ${getScoreColor(healthScore)}`}>
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400 leading-none">
            Dataset Integrity
          </p>
          <div className="relative flex items-center justify-center">
            <span className="text-4xl font-extrabold tracking-tighter">
              {healthScore}
            </span>
            <span className="text-xs font-bold shrink-0 mt-2">%</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-tight bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
            {healthScore >= 90 ? (
              <>
                <CheckCircle2 size={12} className="text-emerald-500" /> Great Quality
              </>
            ) : healthScore >= 75 ? (
              <>
                <BadgeInfo size={12} className="text-indigo-500" /> Acceptable
              </>
            ) : (
              <>
                <AlertTriangle size={12} className="text-amber-500" /> Caution
              </>
            )}
          </div>
        </div>

        {/* Dynamic Diagnostics Knobs & Sliders */}
        <div className="md:col-span-3 p-6 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-3xl grid grid-cols-1 md:grid-cols-2 gap-6 relative">
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                <Sliders size={14} className="text-indigo-500" /> Z-Score Outlier Bound
              </span>
              <span className="font-mono text-xs font-black text-indigo-600 dark:text-indigo-400">
                ±{zThreshold.toFixed(1)} σ
              </span>
            </div>
            <p className="text-[10px] text-slate-500 leading-relaxed font-semibold">
              Observations deviating past this standard deviation from properties mean are classified as statistics outliers. Highly stable specs can be set tighter.
            </p>
            <input 
              aria-label="Z-Score Outlier Bound Selector"
              type="range"
              min="1.5"
              max="4.5"
              step="0.1"
              value={zThreshold}
              onChange={(e) => setZThreshold(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-ew-resize accent-indigo-600"
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                <Sliders size={14} className="text-indigo-500" /> IQR Outlier Multiplier
              </span>
              <span className="font-mono text-xs font-black text-indigo-600 dark:text-indigo-400">
                {iqrMultiplier.toFixed(1)}x IQR
              </span>
            </div>
            <p className="text-[10px] text-slate-500 leading-relaxed font-semibold">
              Defines the outlier hurdle boundaries beyond the 25th and 75th percentiles (Q1 - Mult*IQR, Q3 + Mult*IQR). Highly robust against skew.
            </p>
            <input 
              aria-label="IQR Outlier Multiplier Selector"
              type="range"
              min="1.0"
              max="3.0"
              step="0.1"
              value={iqrMultiplier}
              onChange={(e) => setIqrMultiplier(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-ew-resize accent-indigo-600"
            />
          </div>

          {isAnomalizing && (
            <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2 py-1 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/30 rounded-xl">
              <Loader2 className="animate-spin text-indigo-600 dark:text-indigo-400" size={10} />
              <span className="text-[9px] font-black uppercase text-indigo-600 dark:text-indigo-400 tracking-wider">Recalculating...</span>
            </div>
          )}
        </div>
      </div>

      {/* 2. Key High-level Statistics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-2xl flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Total Observations</span>
          <span className="text-xl font-black text-slate-900 dark:text-white mt-1 font-mono">{result?.totalValuesChecked}</span>
        </div>
        <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-2xl flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Missing Values Rate</span>
          <span className="text-xl font-black text-indigo-600 dark:text-indigo-400 mt-1 font-mono">
            {result && result.totalValuesChecked > 0 ? ((result.totalMissingCount / (result.totalValuesChecked + result.totalMissingCount)) * 100).toFixed(1) : 0}%
          </span>
        </div>
        <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-2xl flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Outlying Values Rate</span>
          <span className="text-xl font-black text-rose-500 mt-1 font-mono">
            {result && result.totalValuesChecked > 0 ? ((result.totalOutliersCount / result.totalValuesChecked) * 100).toFixed(2) : 0}%
          </span>
        </div>
        <div className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-2xl flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Outlying Cells Identified</span>
          <span className="text-xl font-black text-rose-500 mt-1 font-mono">{result?.totalOutliersCount}</span>
        </div>
      </div>

      {/* 3. Section Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={() => { setActiveTab('outliers'); setSearchQuery(''); }}
          className={`px-5 py-3 text-xs font-black tracking-tight border-b-2 transition-all ${
            activeTab === 'outliers' 
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          🚨 FLAGGED OUTLIERS ({result?.totalOutliersCount})
        </motion.button>
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={() => { setActiveTab('missing'); setSearchQuery(''); }}
          className={`px-5 py-3 text-xs font-black tracking-tight border-b-2 transition-all ${
            activeTab === 'missing' 
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          🔍 MISSING SPEC DIAGNOSTICS ({result?.missing?.length})
        </motion.button>
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={() => { setActiveTab('stats'); setSearchQuery(''); }}
          className={`px-5 py-3 text-xs font-black tracking-tight border-b-2 transition-all ${
            activeTab === 'stats' 
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          🔬 MATRIX PROPERTY BOUNDS
        </motion.button>
      </div>

      {/* Search and Filters panel */}
      {activeTab !== 'stats' && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-2.5 text-slate-400" size={14} />
            <input
              type="text"
              placeholder="Search by resin grade name, manufacturer or property key..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-indigo-500/20 outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={12} className="text-slate-400 sm:block hidden" />
            
            {activeTab === 'outliers' && (
              <select
                aria-label="Severity Filter Selection"
                value={severityFilter}
                onChange={(event) => setSeverityFilter(event.target.value as typeof severityFilter)}
                className="px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold focus:ring-2 focus:ring-indigo-500/20 outline-none"
              >
                <option value="all">All Deviation Profiles</option>
                <option value="extreme">Extreme Outliers (Z-score ≥ 4)</option>
                <option value="moderate">Moderate Outliers (2 ≤ Z-score &lt; 4)</option>
              </select>
            )}

            {activeTab === 'missing' && (
              <select
                aria-label="Missing Urgency Selection"
                value={missingUrgencyFilter}
                onChange={(event) => setMissingUrgencyFilter(event.target.value as typeof missingUrgencyFilter)}
                className="px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold focus:ring-2 focus:ring-indigo-500/20 outline-none"
              >
                <option value="all">All Specifications</option>
                <option value="critical">🔴 Critical Core Specs</option>
                <option value="high">🟡 High Importance Specs</option>
                <option value="normal">⚪ Normal properties</option>
              </select>
            )}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="bg-white dark:bg-slate-950/20 border border-slate-200 dark:border-slate-900 rounded-3xl overflow-hidden min-h-[300px]">
        {activeTab === 'outliers' && (
          <div className="overflow-x-auto">
            {filteredOutliers.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-xs font-semibold">
                No outlying values matched the current filters or thresholds. Good job!
              </div>
            ) : (
              <table className="w-full text-left border-collapse table-fixed min-w-[700px]">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-850 bg-slate-50/50 dark:bg-slate-900/10">
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[25%]">Resin Grade Name</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[15%]">Manufacturer</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[20%]">Outlying Key</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">Value</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[15%] text-right">Standard Mean</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[15%] text-right">Outlier Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-850">
                  {filteredOutliers.map((item, index) => {
                    const absZ = Math.abs(item.stats.zScore);
                    const isExtreme = absZ >= 4;
                    return (
                      <tr key={index} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/5 transition-colors">
                        <td className="p-4 text-xs font-black text-slate-800 dark:text-white truncate">{item.gradeName}</td>
                        <td className="p-4 text-xs font-semibold text-slate-500 dark:text-slate-400 truncate">{item.manufacturer}</td>
                        <td className="p-4 text-xs font-bold text-slate-700 dark:text-slate-300">
                          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-[11px] font-mono font-bold">
                            {item.propertyKey}
                          </span>
                        </td>
                        <td className="p-4 text-xs font-mono font-black text-right">{item.value.toFixed(2)}</td>
                        <td className="p-4 text-xs font-mono text-slate-500 text-right">{item.stats.mean.toFixed(2)}</td>
                        <td className="p-4 text-right">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black font-mono leading-none border uppercase tracking-wider ${
                            isExtreme 
                              ? 'bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/20 dark:text-rose-450 dark:border-rose-900/30' 
                              : 'bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-950/20 dark:text-amber-450 dark:border-amber-900/30'
                          }`}>
                            {item.stats.zScore > 0 ? '+' : ''}{item.stats.zScore.toFixed(2)} σ
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'missing' && (
          <div className="overflow-x-auto">
            {filteredMissing.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-xs font-semibold">
                No missing specifications found for active filters. Complete data!
              </div>
            ) : (
              <table className="w-full text-left border-collapse table-fixed min-w-[700px]">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-850 bg-slate-50/50 dark:bg-slate-900/10">
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[30%]">Resin Grade Name</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[20%]">Manufacturer</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[25%]">Missing Key</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[25%] text-right">Urgency Rank</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-850">
                  {filteredMissing.map((item, index) => {
                    const isCritical = item.importance === 'critical';
                    const isHigh = item.importance === 'high';
                    return (
                      <tr key={index} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/5 transition-colors">
                        <td className="p-4 text-xs font-black text-slate-800 dark:text-white truncate">{item.gradeName}</td>
                        <td className="p-4 text-xs font-semibold text-slate-500 dark:text-slate-400 truncate">{item.manufacturer}</td>
                        <td className="p-4 text-xs font-bold text-slate-700 dark:text-slate-300">
                          <span className="px-2 py-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-[11px] font-mono font-bold">
                            {item.propertyKey}
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black leading-none uppercase tracking-wider border ${
                            isCritical 
                              ? 'bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/20 dark:text-rose-450 dark:border-rose-900/30' 
                              : isHigh 
                                ? 'bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-950/20 dark:text-amber-450 dark:border-amber-900/30'
                                : 'bg-slate-50 text-slate-500 border-slate-200 dark:bg-slate-900 dark:text-slate-400 dark:border-slate-800'
                          }`}>
                            {isCritical ? '🔴 CRITICAL CORE' : isHigh ? '🟡 HIGH IMPORTANCE' : '⚪ NORMAL'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="overflow-x-auto">
            {!result?.propertyStats || result.propertyStats.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-xs font-semibold">
                No properties distributions metrics calculated.
              </div>
            ) : (
              <table className="w-full text-left border-collapse table-fixed min-w-[900px]">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-850 bg-slate-50/50 dark:bg-slate-900/10">
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[20%]">Property Field Name</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[20%]">Completeness Diagnostics</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">Mean Average</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">Std Dev (σ)</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">Q1 (25th %)</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">Q3 (75th %)</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">IQR Bounds</th>
                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-wider w-[10%] text-right">Anomalies</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-850 font-mono text-[11px]">
                  {result.propertyStats.map((stat, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/5 transition-colors">
                      <td className="p-4 font-black font-sans text-xs text-slate-800 dark:text-white truncate">{stat.key}</td>
                      <td className="p-4 font-sans max-w-xs">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between text-[10px] font-bold">
                            <span className="text-slate-400 font-mono">{stat.totalCount - stat.missingCount}/{stat.totalCount} cells</span>
                            <span className={stat.completenessRate >= 90 ? 'text-emerald-500' : stat.completenessRate >= 70 ? 'text-indigo-500' : 'text-amber-500'}>
                              {stat.completenessRate.toFixed(1)}%
                            </span>
                          </div>
                          <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-900 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full transition-all ${
                                stat.completenessRate >= 90 
                                  ? 'bg-emerald-500' 
                                  : stat.completenessRate >= 70 
                                    ? 'bg-indigo-500' 
                                    : 'bg-amber-500'
                              }`}
                              style={{ width: `${stat.completenessRate}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-right text-slate-800 dark:text-slate-200">{stat.mean ? stat.mean.toFixed(2) : 'N/A'}</td>
                      <td className="p-4 text-right text-slate-500">{stat.stdDev ? stat.stdDev.toFixed(2) : 'N/A'}</td>
                      <td className="p-4 text-right text-slate-500">{stat.q1 ? stat.q1.toFixed(2) : 'N/A'}</td>
                      <td className="p-4 text-right text-slate-500">{stat.q3 ? stat.q3.toFixed(2) : 'N/A'}</td>
                      <td className="p-4 text-right text-slate-500">{stat.iqr ? stat.iqr.toFixed(2) : 'N/A'}</td>
                      <td className="p-4 text-right font-black">
                        {stat.outlierCount > 0 ? (
                          <span className="px-2 py-0.5 bg-rose-50 text-rose-600 dark:bg-rose-950/20 dark:text-rose-400 border border-rose-100 dark:border-rose-900/30 rounded-md text-[10px]">
                            {stat.outlierCount} CELL{stat.outlierCount > 1 ? 'S' : ''}
                          </span>
                        ) : (
                          <span className="text-emerald-500">None</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
