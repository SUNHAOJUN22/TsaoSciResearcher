import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, escapeScientificHtml, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';

interface MahalanobisChartProps {
  distances: { index: number; id: string; name: string; distance: number; isOutlier: boolean }[];
  threshold: number;
  theme: 'light' | 'dark';
}

export const MahalanobisChart: React.FC<MahalanobisChartProps> = React.memo(({ distances, threshold, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    let maximum = threshold;
    for (const entry of distances) maximum = Math.max(maximum, entry.distance);
    return {
      title: { text: 'Regularized Mahalanobis distance screening', subtext: 'Threshold is a χ² screening reference under the model assumptions; flagged points require review.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      grid: { top: 76, bottom: 62, left: 70, right: 36, containLabel: true },
      dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'filter' }],
      tooltip: { formatter: (params: unknown) => { const item = scientificTooltipItem(params); const data = item?.data as { name?: string; distance?: number; isOutlier?: boolean } | undefined; return data ? `<strong>${escapeScientificHtml(data.name)}</strong><br/>D²: ${formatScientificNumber(Number(data.distance))}<br/>Screening status: ${data.isOutlier ? 'above χ² reference' : 'within χ² reference'}` : ''; } },
      xAxis: { type: 'value', name: 'Sample index', nameLocation: 'middle', nameGap: 32, min: 0, max: distances.length + 1 },
      yAxis: { type: 'value', name: 'Mahalanobis D²', nameLocation: 'middle', nameGap: 46, min: 0, max: maximum > 0 ? maximum * 1.15 : 1 },
      series: [{
        name: 'Sample distance',
        type: 'scatter',
        symbolSize: 7,
        progressive: 1_000,
        data: distances.map((entry) => ({
          value: [entry.index, entry.distance],
          name: entry.name,
          distance: entry.distance,
          isOutlier: entry.isOutlier,
          itemStyle: { color: entry.isOutlier ? SCIENTIFIC_PALETTE[1] : SCIENTIFIC_PALETTE[0], opacity: 0.78 },
        })),
        markLine: {
          symbol: ['none', 'none'],
          silent: true,
          lineStyle: { color: SCIENTIFIC_PALETTE[1], type: 'dashed', width: 1.5 },
          label: { formatter: 'χ² screening reference: {c}' },
          data: [{ yAxis: threshold }],
        },
      }],
    };
  }, [distances, threshold]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Mahalanobis distance screening" description="Each point is a regularized multivariate distance. The horizontal line is a screening reference, not automatic proof of failure." exportName="mahalanobis-screening" dataCount={distances.length} empty={distances.length === 0} />;
});
