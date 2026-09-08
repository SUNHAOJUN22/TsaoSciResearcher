import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';
import { summarizeFinite } from '@/lib/numericAggregation';

interface ArrheniusChartProps {
  points: { tempC: number; time: number; x: number; y: number }[];
  equation: { m: number; b: number };
  rSquared: number;
  theme: 'light' | 'dark';
}

export const ArrheniusChart: React.FC<ArrheniusChartProps> = React.memo(({ points, equation, rSquared, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    const bounds = summarizeFinite(points, (point) => point.x);
    const minX = bounds?.minimum ?? 0;
    const maxX = bounds?.maximum ?? 0;
    const span = Math.max(maxX - minX, 1e-6);
    const lineStart = minX - span * 0.08;
    const lineEnd = maxX + span * 0.08;
    return {
      title: {
        text: 'Arrhenius lifetime linearization',
        subtext: `OLS in ln(t / h) versus 1/T; R²=${rSquared.toFixed(4)}. Extrapolation assumes one dominant apparent activation process.`,
        left: 'center',
        top: 6,
        textStyle: { fontSize: 14, fontWeight: 650 },
        subtextStyle: { fontSize: 10 },
      },
      legend: { bottom: 4, data: ['Observed lifetime', 'Linear fit (model)'] },
      grid: { top: 76, bottom: 70, left: 70, right: 36, containLabel: true },
      tooltip: {
        trigger: 'item',
        formatter: (params: unknown) => {
          const item = scientificTooltipItem(params);
          if (item?.seriesType === 'line') return `Linear fit (model)<br/>R²=${rSquared.toFixed(4)}`;
          const value = item?.data as [number, number, number, number] | undefined;
          return value
            ? `Observed lifetime<br/>T: ${formatScientificNumber(value[2])} °C<br/>1000/T: ${formatScientificNumber(value[0])} K⁻¹<br/>ln(t / h): ${formatScientificNumber(value[1])}<br/>t: ${formatScientificNumber(value[3])} h`
            : '';
        },
      },
      xAxis: { type: 'value', name: '1000/T (K⁻¹)', nameLocation: 'middle', nameGap: 34, scale: true },
      yAxis: { type: 'value', name: 'ln(t / h)', nameLocation: 'middle', nameGap: 48, scale: true },
      series: [
        {
          name: 'Observed lifetime',
          type: 'scatter',
          data: points.map((point) => [point.x * 1_000, point.y, point.tempC, point.time]),
          symbolSize: 7,
          itemStyle: { color: SCIENTIFIC_PALETTE[1] },
        },
        {
          name: 'Linear fit (model)',
          type: 'line',
          data: [
            [lineStart * 1_000, equation.m * lineStart + equation.b],
            [lineEnd * 1_000, equation.m * lineEnd + equation.b],
          ],
          symbol: 'none',
          lineStyle: { color: SCIENTIFIC_PALETTE[0], width: 1.6, type: 'dashed' },
          silent: true,
        },
      ],
    };
  }, [equation.b, equation.m, points, rSquared]);

  return (
    <ScientificEChart
      option={option}
      theme={theme}
      ariaLabel="Arrhenius lifetime linearization"
      description="Observed lifetime points and an ordinary least-squares Arrhenius fit are shown separately."
      exportName="arrhenius-lifetime-linearization"
      dataCount={points.length + 2}
      empty={points.length < 2}
    />
  );
});
