import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_SEQUENTIAL, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';

interface KdeTopologyChartProps { grid: { x: number; y: number; z: number }[]; dataPoints: { x: number; y: number }[]; xLabel: string; yLabel: string; theme: 'light' | 'dark' }

export const KdeTopologyChart: React.FC<KdeTopologyChartProps> = React.memo(({ grid, dataPoints, xLabel, yLabel, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    let maxDensity = 0;
    for (const point of grid) maxDensity = Math.max(maxDensity, point.z);
    return {
      title: { text: 'Bivariate Gaussian kernel-density estimate', subtext: 'Heatmap is the normalized fitted density; outlined markers are the finite observations.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      grid: { top: 76, bottom: 62, left: 68, right: 84, containLabel: true },
      tooltip: { formatter: (params: unknown) => { const item = scientificTooltipItem(params); const value = item?.data as number[] | undefined; if (!value) return ''; return item?.seriesType === 'scatter' ? `Observed point<br/>${xLabel}: ${formatScientificNumber(value[0])}<br/>${yLabel}: ${formatScientificNumber(value[1])}` : `Fitted density: ${formatScientificNumber(value[2])}<br/>Relative to grid maximum: ${formatScientificNumber((value[2] / Math.max(maxDensity, Number.EPSILON)) * 100)}%`; } },
      xAxis: { type: 'value', name: xLabel, nameLocation: 'middle', nameGap: 34, scale: true },
      yAxis: { type: 'value', name: yLabel, nameLocation: 'middle', nameGap: 46, scale: true },
      visualMap: { min: 0, max: maxDensity || 1, calculable: true, realtime: false, right: 4, top: 'middle', inRange: { color: [...SCIENTIFIC_SEQUENTIAL] } },
      series: [
        { name: 'KDE fitted density', type: 'heatmap', data: grid.map((point) => [point.x, point.y, point.z]), emphasis: { disabled: true } },
        { name: 'Observed points', type: 'scatter', data: dataPoints.filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y)).map((point) => [point.x, point.y]), symbolSize: dataPoints.length > 2_000 ? 2 : 4, progressive: 1_000, itemStyle: { color: theme === 'dark' ? '#ffffff' : '#0f172a', opacity: 0.55 } },
      ],
    };
  }, [dataPoints, grid, theme, xLabel, yLabel]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Bivariate Gaussian kernel density estimate" description="A fitted KDE heatmap is overlaid with finite observed points." exportName="bivariate-kde" dataCount={grid.length + dataPoints.length} empty={grid.length === 0} />;
});
