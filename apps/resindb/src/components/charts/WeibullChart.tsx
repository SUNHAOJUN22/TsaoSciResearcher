import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';
import { summarizeFinite } from '@/lib/numericAggregation';

interface WeibullChartProps {
  points: { value: number; x: number; y: number; p: number }[];
  m: number;
  eta: number;
  rSquared: number;
  safeValue95: number;
  targetKey: string;
  theme: 'light' | 'dark';
}

export const WeibullChart: React.FC<WeibullChartProps> = React.memo((props) => {
  const { points, m, eta, rSquared, safeValue95, targetKey, theme } = props;
  const option = useMemo<EChartsOption>(() => {
    const bounds = summarizeFinite(points, (point) => point.x);
    const minX = bounds?.minimum ?? 0;
    const maxX = bounds?.maximum ?? 0;
    const b5Log = safeValue95 > 0 ? Math.log(safeValue95) : null;
    return {
      title: {
        text: 'Two-parameter Weibull probability plot',
        subtext: `Bernard median-rank OLS (not MLE); m=${formatScientificNumber(m)}, η=${formatScientificNumber(eta)}, R²=${rSquared.toFixed(4)}.`,
        left: 'center',
        top: 6,
        textStyle: { fontSize: 14, fontWeight: 650 },
        subtextStyle: { fontSize: 10 },
      },
      legend: { bottom: 4, data: ['Median-rank observations', 'OLS fit (model)'] },
      grid: { top: 76, bottom: 70, left: 72, right: 36, containLabel: true },
      tooltip: {
        trigger: 'item',
        formatter: (params: unknown) => {
          const item = scientificTooltipItem(params);
          if (item?.seriesType === 'line') return 'Bernard median-rank OLS fit (not maximum likelihood).';
          const value = item?.data as [number, number, number, number] | undefined;
          return value
            ? `Median-rank observation<br/>${targetKey}: ${formatScientificNumber(value[2])}<br/>Cumulative failure: ${formatScientificNumber(value[3] * 100)}%`
            : '';
        },
      },
      xAxis: { type: 'value', name: `ln(${targetKey})`, nameLocation: 'middle', nameGap: 34, scale: true },
      yAxis: { type: 'value', name: 'ln[-ln(1 − P)]', nameLocation: 'middle', nameGap: 50, scale: true },
      series: [
        {
          name: 'Median-rank observations',
          type: 'scatter',
          data: points.map((point) => [point.x, point.y, point.value, point.p]),
          symbolSize: 7,
          itemStyle: { color: SCIENTIFIC_PALETTE[0] },
          markLine: b5Log === null ? undefined : {
            symbol: ['none', 'none'],
            silent: true,
            lineStyle: { color: SCIENTIFIC_PALETTE[2], type: 'dotted', width: 1.4 },
            label: { formatter: `B5 / 95% survival = ${formatScientificNumber(safeValue95)}` },
            data: [{ xAxis: b5Log }],
          },
        },
        {
          name: 'OLS fit (model)',
          type: 'line',
          data: [[minX, m * (minX - Math.log(eta))], [maxX, m * (maxX - Math.log(eta))]],
          symbol: 'none',
          lineStyle: { color: SCIENTIFIC_PALETTE[1], width: 1.6, type: 'dashed' },
          silent: true,
        },
      ],
    };
  }, [eta, m, points, rSquared, safeValue95, targetKey]);

  return (
    <ScientificEChart
      option={option}
      theme={theme}
      ariaLabel="Weibull median-rank probability plot"
      description="The figure uses Bernard median ranks and ordinary least-squares linearization, not maximum-likelihood estimation."
      exportName="weibull-median-rank-ols"
      dataCount={points.length + 2}
      empty={points.length < 3}
    />
  );
});
