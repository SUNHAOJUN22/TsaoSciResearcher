import React, { useMemo, useState } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import type { Product } from '@/types/index';
import { useTheme } from '@/contexts/ThemeContext';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE } from './scientificFigurePolicy';

interface DegradationSimulatorProps { product: Product }

function finiteProperty(product: Product, keys: string[], fallback: number): number {
  for (const key of keys) {
    const value = Number(product.properties[key]?.value);
    if (Number.isFinite(value)) return value;
  }
  return fallback;
}

export const DegradationSimulator: React.FC<DegradationSimulatorProps> = ({ product }) => {
  const { theme } = useTheme();
  const [temperature, setTemperature] = useState(80);
  const [years, setYears] = useState(10);
  const scenario = useMemo(() => {
    const safeTemperature = Math.max(-200, Math.min(300, Number.isFinite(temperature) ? temperature : 80));
    const safeYears = Math.max(1, Math.min(50, Number.isFinite(years) ? years : 10));
    const baseline = finiteProperty(product, ['拉伸强度', 'Tensile Strength'], 50);
    const thermalProxy = finiteProperty(product, ['热变形温度', 'HDT', 'Heat Deflection Temperature'], 100);
    const apparentActivationEnergy = 80_000 + thermalProxy * 100;
    const gasConstant = 8.314;
    const preExponentialFactor = 1e12;
    const kelvin = safeTemperature + 273.15;
    const rateConstant = preExponentialFactor * Math.exp(-apparentActivationEnergy / (gasConstant * kelvin));
    const points: { time: number; mean: number; lower: number; upper: number }[] = [];
    for (let month = 0; month <= safeYears * 12; month++) {
      const time = month / 12;
      const mean = baseline * Math.exp(-rateConstant * time * 8_760);
      const fractionalBand = Math.min(0.35, 0.03 + 0.02 * Math.sqrt(time));
      points.push({ time, mean, lower: Math.max(0, mean * (1 - fractionalBand)), upper: mean * (1 + fractionalBand) });
    }
    return { baseline, safeTemperature, safeYears, apparentActivationEnergy, points };
  }, [product, temperature, years]);

  const option = useMemo<EChartsOption>(() => ({
    title: { text: 'Rule-based tensile-strength retention scenario', subtext: 'Cross-sectional property proxies and assumed Arrhenius parameters; heuristic band is not a confidence or prediction interval.', left: 'center', top: 6, textStyle: { fontSize: 13, fontWeight: 650 }, subtextStyle: { fontSize: 9 } },
    legend: { bottom: 4, data: ['Scenario mean', 'Heuristic scenario band'] },
    grid: { top: 72, bottom: 64, left: 68, right: 34, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value', name: 'Scenario time (years)', nameLocation: 'middle', nameGap: 32, min: 0, max: scenario.safeYears },
    yAxis: { type: 'value', name: 'Tensile-strength proxy (MPa)', nameLocation: 'middle', nameGap: 48, min: 0 },
    series: [
      { name: 'Band lower carrier', type: 'line', stack: 'scenario-band', data: scenario.points.map((point) => [point.time, point.lower]), symbol: 'none', lineStyle: { opacity: 0 }, silent: true },
      { name: 'Heuristic scenario band', type: 'line', stack: 'scenario-band', data: scenario.points.map((point) => [point.time, point.upper - point.lower]), symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(0,114,178,0.16)' }, silent: true },
      { name: 'Scenario mean', type: 'line', data: scenario.points.map((point) => [point.time, point.mean]), symbol: 'none', smooth: false, lineStyle: { color: SCIENTIFIC_PALETTE[0], width: 1.7 } },
    ],
  }), [scenario]);

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900" aria-label="Rule based degradation scenario">
      <div className="mb-3 flex flex-wrap items-end gap-4">
        <label className="grid gap-1 text-xs text-slate-500"><span>Scenario temperature (°C)</span><input type="number" value={temperature} min={-200} max={300} onChange={(event) => setTemperature(Number(event.target.value))} className="w-28 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-white" /></label>
        <label className="grid gap-1 text-xs text-slate-500"><span>Scenario horizon (years)</span><input type="number" value={years} min={1} max={50} onChange={(event) => setYears(Number(event.target.value))} className="w-28 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-white" /></label>
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-[10px] leading-4 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">Screening scenario only. Ea={Math.round(scenario.apparentActivationEnergy / 1_000)} kJ·mol⁻¹ is a property-derived assumption, not an experimental fit.</div>
      </div>
      <ScientificEChart option={option} theme={theme} ariaLabel="Rule based tensile strength retention scenario" description="The scenario is derived from cross-sectional material properties and assumed Arrhenius parameters. The band is heuristic and is not a statistical confidence interval." exportName="rule-based-retention-scenario" dataCount={scenario.points.length * 3} />
    </section>
  );
};
