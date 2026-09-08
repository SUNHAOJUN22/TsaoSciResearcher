import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, formatScientificNumber } from './scientificFigurePolicy';

interface FeatureImportanceChartProps {
  importances: { feature: string; importance: number; positive: boolean }[];
  theme: 'light' | 'dark';
}

export const FeatureImportanceChart: React.FC<FeatureImportanceChartProps> = React.memo(({ importances, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    const sorted = [...importances].sort((left, right) => left.importance - right.importance);
    return {
      title: {
        text: 'Standardized ridge sensitivity attribution',
        subtext: 'Absolute standardized coefficients normalized to 100%; signs show conditional association, not causality or SHAP.',
        left: 'center',
        top: 6,
        textStyle: { fontSize: 14, fontWeight: 650 },
        subtextStyle: { fontSize: 10 },
      },
      grid: { top: 76, bottom: 58, left: 24, right: 52, containLabel: true },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          const entry = Array.isArray(params) ? params[0] as { dataIndex: number; name: string; value: number } : null;
          if (!entry) return '';
          const source = sorted[entry.dataIndex];
          return `<strong>${entry.name}</strong><br/>Normalized |β| share: ${formatScientificNumber(entry.value)}%<br/>Standardized coefficient direction: ${source.positive ? 'positive' : 'negative'}<br/><em>Association only; not causal effect.</em>`;
        },
      },
      xAxis: {
        type: 'value',
        name: 'Normalized |standardized ridge coefficient| (%)',
        nameLocation: 'middle',
        nameGap: 32,
        min: 0,
        axisLabel: { formatter: '{value}%' },
      },
      yAxis: {
        type: 'category',
        data: sorted.map((entry) => entry.feature),
        axisLabel: { width: 180, overflow: 'truncate' },
        axisTick: { show: false },
      },
      series: [{
        name: 'Ridge sensitivity attribution',
        type: 'bar',
        barMaxWidth: 22,
        data: sorted.map((entry) => ({
          value: entry.importance * 100,
          itemStyle: { color: entry.positive ? SCIENTIFIC_PALETTE[2] : SCIENTIFIC_PALETTE[1] },
        })),
        label: { show: true, position: 'right', formatter: ({ value }: { value?: unknown }) => `${formatScientificNumber(Number(value))}%` },
      }],
    };
  }, [importances]);

  return (
    <ScientificEChart
      option={option}
      theme={theme}
      ariaLabel="Standardized ridge regression sensitivity attribution"
      description="Bars show normalized absolute standardized ridge coefficients. Sign is association direction and does not imply causality."
      exportName="ridge-sensitivity-attribution"
      dataCount={importances.length}
      empty={importances.length === 0}
    />
  );
});
