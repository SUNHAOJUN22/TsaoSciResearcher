import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE } from './scientificFigurePolicy';

interface PronyChartProps {
  points: { omega: number; storage: number; loss: number; storage_fit: number; loss_fit: number }[];
  theme: 'light' | 'dark';
}

export const PronyChart: React.FC<PronyChartProps> = React.memo(({ points, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    const sorted = [...points]
      .filter((point) => [point.omega, point.storage, point.loss, point.storage_fit, point.loss_fit].every(Number.isFinite) && point.omega > 0)
      .sort((left, right) => left.omega - right.omega);
    return {
      title: { text: 'Prony-series viscoelastic fit', subtext: 'Markers are observed dynamic moduli; lines are non-negative model fits. No smoothing interpolation is applied.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      legend: { bottom: 4, data: ["Observed E'", "Observed E''", "Model E'", "Model E''"] },
      grid: { top: 76, bottom: 70, left: 76, right: 36, containLabel: true },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'log', name: 'Angular frequency, ω (rad·s⁻¹)', nameLocation: 'middle', nameGap: 36 },
      yAxis: { type: 'log', name: 'Modulus (MPa)', nameLocation: 'middle', nameGap: 52 },
      series: [
        { name: "Observed E'", type: 'scatter', data: sorted.map((point) => [point.omega, point.storage]), symbolSize: 6, itemStyle: { color: SCIENTIFIC_PALETTE[0] } },
        { name: "Observed E''", type: 'scatter', data: sorted.map((point) => [point.omega, point.loss]), symbol: 'triangle', symbolSize: 6, itemStyle: { color: SCIENTIFIC_PALETTE[1] } },
        { name: "Model E'", type: 'line', data: sorted.map((point) => [point.omega, point.storage_fit]), symbol: 'none', smooth: false, lineStyle: { width: 1.6, color: SCIENTIFIC_PALETTE[0] } },
        { name: "Model E''", type: 'line', data: sorted.map((point) => [point.omega, point.loss_fit]), symbol: 'none', smooth: false, lineStyle: { width: 1.6, type: 'dashed', color: SCIENTIFIC_PALETTE[1] } },
      ],
    };
  }, [points]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Prony series observed and fitted moduli" description="Observed storage and loss moduli are shown as markers; non-negative Prony-series fits are shown as lines." exportName="prony-viscoelastic-fit" dataCount={points.length * 4} empty={points.length === 0} />;
});
