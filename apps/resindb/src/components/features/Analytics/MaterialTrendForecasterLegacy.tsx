import { motion } from 'motion/react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useForecastingWorker } from '@/hooks/workers/useForecastingWorker';
import type { Product } from '@/types/index';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Info,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface MaterialTrendForecasterProps {
  products: Product[];
  selectedProducts?: Product[];
}

type ScenarioAlgorithm = 'linear' | 'exponential' | 'holt-linear';
type ScenarioCondition = 'thermal' | 'uv' | 'hydrolysis' | 'cyclic';

export const MaterialTrendForecaster: React.FC<MaterialTrendForecasterProps> = ({
  products,
  selectedProducts = [],
}) => {
  const { isProjecting, forecastResult, forecastError, runCalculatedForecast } = useForecastingWorker();
  const activeProducts = useMemo(
    () => selectedProducts.length > 0 ? selectedProducts : products,
    [products, selectedProducts],
  );
  const numericProperties = useMemo(() => {
    const keys = new Set<string>();
    for (const product of activeProducts) {
      for (const [key, property] of Object.entries(product.properties ?? {})) {
        const value = Number(property?.value);
        if (Number.isFinite(value) && value > 0) keys.add(key);
      }
    }
    return [...keys].sort();
  }, [activeProducts]);

  const [selectedProperty, setSelectedProperty] = useState('');
  const [algorithm, setAlgorithm] = useState<ScenarioAlgorithm>('exponential');
  const [condition, setCondition] = useState<ScenarioCondition>('thermal');
  const [stressFactor, setStressFactor] = useState(85);
  const [alpha, setAlpha] = useState(0.4);
  const [beta, setBeta] = useState(0.3);

  useEffect(() => {
    if (numericProperties.length > 0 && !numericProperties.includes(selectedProperty)) {
      const preferred = numericProperties.find((key) => [
        'tensile strength', '拉伸强度', 'impact strength', '缺口冲击强度',
      ].includes(key.toLowerCase()));
      setSelectedProperty(preferred ?? numericProperties[0]);
    }
  }, [numericProperties, selectedProperty]);

  useEffect(() => {
    const defaults: Record<ScenarioCondition, number> = {
      thermal: 85,
      uv: 12,
      hydrolysis: 90,
      cyclic: 15,
    };
    setStressFactor(defaults[condition]);
  }, [condition]);

  const runScenario = useCallback(() => {
    if (activeProducts.length > 0 && selectedProperty) {
      runCalculatedForecast(
        activeProducts,
        selectedProperty,
        algorithm,
        condition,
        stressFactor,
        alpha,
        beta,
      );
    }
  }, [activeProducts, selectedProperty, algorithm, condition, stressFactor, alpha, beta, runCalculatedForecast]);

  useEffect(() => {
    runScenario();
  }, [runScenario]);

  const conditionLabel: Record<ScenarioCondition, string> = {
    thermal: 'Q10-style thermal loss rule (°C; not an Arrhenius fit)',
    uv: 'UV exposure scenario (hours/day)',
    hydrolysis: 'Relative-humidity scenario (% RH)',
    cyclic: 'Cyclic-load scenario (MPa)',
  };
  const statusClass = (status: 'safe' | 'warning' | 'danger') => {
    if (status === 'safe') return 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/40';
    if (status === 'warning') return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/40';
    return 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/20 dark:text-rose-400 dark:border-rose-900/40';
  };

  return (
    <div className="space-y-6">
      <div className="p-5 bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-800/40 rounded-3xl space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <TrendingUp className="text-indigo-600 dark:text-indigo-400" size={20} />
          <h3 className="text-sm font-black text-indigo-950 dark:text-white uppercase tracking-tight">
            Material Aging Scenario Projection
          </h3>
          <span className="text-[10px] bg-indigo-600 text-white font-mono px-2 py-0.5 rounded-full font-bold uppercase tracking-widest">
            Rule-Based 12-Month Scenario
          </span>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-semibold">
          Explore a transparent rule-based aging scenario from the cross-sectional mean of selected grades.
          The baseline path is generated, not observed; projection bands are heuristic and are not confidence
          intervals, material certification, or validated service-life predictions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4 lg:col-span-1">
          <div className="p-5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-3xl space-y-4">
            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 pb-2">
              Scenario Inputs
            </h4>

            <div className="space-y-1.5">
              <label htmlFor="propertySelector" className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">
                Positive Material Property
              </label>
              {numericProperties.length === 0 ? (
                <div className="text-xs text-amber-500 font-semibold p-2">No positive numeric properties detected.</div>
              ) : (
                <select
                  id="propertySelector"
                  value={selectedProperty}
                  onChange={(event) => setSelectedProperty(event.target.value)}
                  className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold outline-none"
                >
                  {numericProperties.map((property) => <option key={property} value={property}>{property}</option>)}
                </select>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="conditionSelector" className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">
                Rule-Based Stress Mode
              </label>
              <select
                id="conditionSelector"
                value={condition}
                onChange={(event) => setCondition(event.target.value as ScenarioCondition)}
                className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold outline-none"
              >
                <option value="thermal">🔥 Q10-Style Thermal Scenario</option>
                <option value="uv">☀️ UV Exposure Scenario</option>
                <option value="hydrolysis">💧 Relative-Humidity Scenario</option>
                <option value="cyclic">🔄 Cyclic-Load Scenario</option>
              </select>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">Stress Input</span>
                <span className="font-mono text-xs font-black text-indigo-600 dark:text-indigo-400">
                  {stressFactor.toFixed(0)} {condition === 'thermal' ? '°C' : condition === 'uv' ? 'hrs/day' : condition === 'hydrolysis' ? '% RH' : 'MPa'}
                </span>
              </div>
              <input
                aria-label="Scenario stress input"
                type="range"
                min={condition === 'thermal' ? 30 : 0}
                max={condition === 'thermal' ? 180 : condition === 'uv' ? 24 : 100}
                step={1}
                value={stressFactor}
                onChange={(event) => setStressFactor(Number(event.target.value))}
                className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg appearance-none cursor-ew-resize accent-indigo-600"
              />
              <p className="text-[9px] text-slate-400 leading-relaxed italic font-semibold">* {conditionLabel[condition]}</p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800">
              <label htmlFor="algorithmSelector" className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">
                Projection Kernel
              </label>
              <select
                id="algorithmSelector"
                value={algorithm}
                onChange={(event) => setAlgorithm(event.target.value as ScenarioAlgorithm)}
                className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold outline-none"
              >
                <option value="linear">Linear OLS Scenario Trend</option>
                <option value="exponential">Log-Linear Exponential Scenario</option>
                <option value="holt-linear">Holt Linear Trend (No Seasonality)</option>
              </select>
            </div>

            {algorithm === 'holt-linear' && (
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                <label className="text-[9px] font-black text-slate-400 uppercase tracking-wide">
                  Alpha (level)
                  <input
                    type="number"
                    min={0.01}
                    max={0.99}
                    step={0.05}
                    value={alpha}
                    onChange={(event) => setAlpha(Number(event.target.value))}
                    className="mt-1 w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono"
                  />
                </label>
                <label className="text-[9px] font-black text-slate-400 uppercase tracking-wide">
                  Beta (trend)
                  <input
                    type="number"
                    min={0.01}
                    max={0.99}
                    step={0.05}
                    value={beta}
                    onChange={(event) => setBeta(Number(event.target.value))}
                    className="mt-1 w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono"
                  />
                </label>
              </div>
            )}

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={runScenario}
              disabled={isProjecting || !selectedProperty}
              className="w-full py-2.5 px-4 bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900 rounded-xl text-xs font-black uppercase tracking-wide flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <RefreshCw size={12} className={isProjecting ? 'animate-spin' : ''} />
              Recalculate Scenario
            </motion.button>

            <div className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl flex items-center gap-3">
              <Cpu className="text-indigo-500 shrink-0" size={16} />
              <div className="text-[10px] text-slate-500 font-semibold leading-normal">
                Baseline scope: <strong className="text-slate-800 dark:text-white">{activeProducts.length}</strong> grades.
                <span className="block mt-0.5">The mean is cross-sectional, not a measured aging time series.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          {forecastError ? (
            <div className="p-6 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/30 rounded-3xl flex items-start gap-3">
              <AlertTriangle className="text-rose-500 shrink-0 mt-0.5" size={16} />
              <div>
                <h4 className="text-xs font-black text-rose-800 dark:text-rose-400 uppercase tracking-wider">Scenario Engine Fault</h4>
                <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{forecastError}</p>
              </div>
            </div>
          ) : isProjecting && !forecastResult ? (
            <div className="bg-slate-50/50 dark:bg-slate-900/10 border border-slate-100 dark:border-slate-800 border-dashed rounded-3xl p-12 min-h-[400px] flex flex-col items-center justify-center space-y-6 text-center">
              <Loader2 className="animate-spin text-indigo-500" size={32} />
              <div className="max-w-xs space-y-1">
                <h4 className="text-sm font-bold text-slate-800 dark:text-white">Calculating Rule-Based Scenario</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 italic">Generating the transparent baseline path and projection kernel.</p>
              </div>
            </div>
          ) : forecastResult ? (
            <div className="space-y-4">
              <div className="p-4 bg-sky-50 dark:bg-sky-950/20 border border-sky-200 dark:border-sky-900/40 rounded-2xl flex gap-3 text-sky-800 dark:text-sky-300">
                <Info size={17} className="shrink-0 mt-0.5" />
                <p className="text-xs font-semibold leading-relaxed">
                  {forecastResult.analysis.baselinePathSource.replaceAll('-', ' ')}; {forecastResult.analysis.intervalMeaning.replaceAll('-', ' ')}.
                  Monthly loss rule: {(forecastResult.analysis.monthlyLossFraction * 100).toFixed(2)}%
                  {forecastResult.analysis.monthlyLossCapped ? ' (capped at the model boundary)' : ''}.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  ['Cross-Sectional Mean', forecastResult.metrics.currentValue.toFixed(2)],
                  ['12-Month Scenario', forecastResult.metrics.projectedValue12m.toFixed(2)],
                  ['Scenario Retention', `${forecastResult.metrics.retentionPercent.toFixed(1)}%`],
                  ['Scenario T50 Crossing', String(forecastResult.metrics.scenarioT50Months)],
                ].map(([label, value]) => (
                  <div key={label} className="p-4 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-2xl">
                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest block">{label}</span>
                    <span className="text-lg font-black text-slate-900 dark:text-white mt-2 font-mono block truncate">{value}</span>
                  </div>
                ))}
              </div>

              <div className="p-5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-3xl space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                    <Activity size={12} className="text-indigo-500" />
                    Rule-Generated Baseline Path vs Scenario Horizon
                  </h5>
                  <div className="flex gap-3 text-[9px] uppercase tracking-wide font-black">
                    <span className="text-slate-400">Synthetic baseline path</span>
                    <span className="text-indigo-500">Scenario projection</span>
                  </div>
                </div>
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={forecastResult.trendPoints} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" opacity={0.25} />
                      <XAxis dataKey="monthLabel" tick={{ fontSize: 9, fontWeight: 700, fill: '#64748b' }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fontSize: 9, fontWeight: 700, fill: '#64748b' }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '12px', fontSize: '11px', color: '#fff', fontWeight: '600' }} />
                      <ReferenceLine
                        y={forecastResult.metrics.currentValue * 0.7}
                        stroke="#f43f5e"
                        strokeDasharray="4 4"
                        label={{ value: 'Interpretation threshold (70%)', position: 'insideBottomRight', fill: '#f43f5e', fontSize: 8, fontWeight: 800 }}
                      />
                      <Area name="Heuristic scenario lower band" type="monotone" dataKey="lowerBound" stroke="none" fill="#6366f1" fillOpacity={0.06} />
                      <Area name="Heuristic scenario upper band" type="monotone" dataKey="upperBound" stroke="none" fill="#6366f1" fillOpacity={0.06} />
                      <Line name="Rule-generated baseline path" type="monotone" dataKey="observed" stroke="#64748b" strokeWidth={2.5} dot={{ r: 3, strokeWidth: 1 }} activeDot={{ r: 5 }} />
                      <Line name="Scenario projection" type="monotone" dataKey="predicted" stroke="#6366f1" strokeWidth={2.5} strokeDasharray="5 5" dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className={`p-5 border rounded-3xl flex items-start gap-3.5 ${statusClass(forecastResult.metrics.safetyStatus)}`}>
                {forecastResult.metrics.safetyStatus === 'safe' ? (
                  <CheckCircle2 size={18} className="text-emerald-500 shrink-0 mt-0.5" />
                ) : forecastResult.metrics.safetyStatus === 'warning' ? (
                  <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
                ) : (
                  <ShieldAlert size={18} className="text-rose-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <h5 className="text-xs font-black uppercase tracking-tight">
                    Scenario retention band: {forecastResult.metrics.retentionBand.replace('-', ' ')}
                  </h5>
                  <p className="text-xs mt-1 font-semibold leading-relaxed opacity-90">{forecastResult.metrics.safetyMessage}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50/50 dark:bg-slate-900/10 border border-slate-200 dark:border-slate-800 rounded-3xl p-12 min-h-[400px] flex flex-col items-center justify-center space-y-3 text-center border-dashed">
              <Sparkles className="text-indigo-500/80" size={32} />
              <div className="max-w-xs space-y-1">
                <h4 className="text-sm font-bold text-slate-800 dark:text-white">Awaiting Scenario Inputs</h4>
                <p className="text-xs text-slate-400 font-semibold leading-relaxed">Select a positive property and rule-based stress scenario.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
