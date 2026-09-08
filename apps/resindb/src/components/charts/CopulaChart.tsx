import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_SEQUENTIAL, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';

interface CopulaChartProps { grid: { u: number; v: number; z: number }[]; theme: 'light' | 'dark' }

export const CopulaChart: React.FC<CopulaChartProps> = React.memo(({ grid, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    let maxDensity = 0;
    for (const point of grid) maxDensity = Math.max(maxDensity, point.z);
    return {
      title: { text: 'Gaussian-copula density in probability space', subtext: 'u and v are empirical cumulative probabilities; density is a fitted dependence model.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      grid: { top: 76, bottom: 62, left: 68, right: 84, containLabel: true },
      tooltip: { formatter: (params: unknown) => { const item = scientificTooltipItem(params); const value = item?.data as [number, number, number] | undefined; return value ? `u: ${formatScientificNumber(value[0])}<br/>v: ${formatScientificNumber(value[1])}<br/>Fitted density: ${formatScientificNumber(value[2])}` : ''; } },
      xAxis: { type: 'value', name: 'u = ECDF(X)', nameLocation: 'middle', nameGap: 34, min: 0, max: 1 },
      yAxis: { type: 'value', name: 'v = ECDF(Y)', nameLocation: 'middle', nameGap: 46, min: 0, max: 1 },
      visualMap: { min: 0, max: maxDensity || 1, calculable: true, realtime: false, right: 4, top: 'middle', inRange: { color: [...SCIENTIFIC_SEQUENTIAL] } },
      series: [{ name: 'Fitted copula density', type: 'heatmap', data: grid.map((point) => [point.u, point.v, point.z]), emphasis: { disabled: true } }],
    };
  }, [grid]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Gaussian copula fitted density" description="The heatmap is a fitted density in empirical probability space." exportName="gaussian-copula-density" dataCount={grid.length} empty={grid.length === 0} />;
});
