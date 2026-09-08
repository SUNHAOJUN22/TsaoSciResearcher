import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE } from './scientificFigurePolicy';

interface SpcChartProps {
  histogram: { x: number; y: number }[];
  normalCurve: { x: number; y: number }[];
  histogramBins: number[];
  mean: number;
  sigma: number;
  usl: number;
  lsl: number;
  theme: 'light' | 'dark';
}

export const SpcChart: React.FC<SpcChartProps> = React.memo(({ histogram, normalCurve, mean, sigma, usl, lsl, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    const upperThreeSigma = mean + 3 * sigma;
    const lowerThreeSigma = mean - 3 * sigma;
    return {
      title: { text: 'Process distribution and reference limits', subtext: 'LSL/USL are specification limits; μ±3σ are distribution references and are not specification limits.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      legend: { bottom: 4, data: ['Observed histogram', 'Normal reference curve'] },
      grid: { top: 76, bottom: 70, left: 70, right: 36, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'value', name: 'Measured value', nameLocation: 'middle', nameGap: 34, scale: true },
      yAxis: { type: 'value', name: 'Frequency / density', nameLocation: 'middle', nameGap: 48, min: 0 },
      series: [
        {
          name: 'Observed histogram',
          type: 'bar',
          barWidth: '92%',
          data: histogram.map((entry) => [entry.x, entry.y]),
          itemStyle: { color: SCIENTIFIC_PALETTE[0], opacity: 0.55 },
          markLine: {
            symbol: ['none', 'none'],
            silent: true,
            label: { position: 'insideEndTop', formatter: '{b}' },
            data: [
              { xAxis: lsl, name: 'LSL specification', lineStyle: { color: SCIENTIFIC_PALETTE[1], type: 'dashed', width: 1.5 } },
              { xAxis: usl, name: 'USL specification', lineStyle: { color: SCIENTIFIC_PALETTE[1], type: 'dashed', width: 1.5 } },
              { xAxis: mean, name: 'Mean μ', lineStyle: { color: SCIENTIFIC_PALETTE[2], type: 'solid', width: 1.5 } },
              { xAxis: lowerThreeSigma, name: 'μ−3σ reference', lineStyle: { color: SCIENTIFIC_PALETTE[4], type: 'dotted', width: 1.3 } },
              { xAxis: upperThreeSigma, name: 'μ+3σ reference', lineStyle: { color: SCIENTIFIC_PALETTE[4], type: 'dotted', width: 1.3 } },
            ],
          },
        },
        { name: 'Normal reference curve', type: 'line', smooth: false, showSymbol: false, data: normalCurve.map((entry) => [entry.x, entry.y]), lineStyle: { width: 1.7, color: SCIENTIFIC_PALETTE[3] } },
      ],
    };
  }, [histogram, lsl, mean, normalCurve, sigma, usl]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="SPC histogram with specification and distribution reference limits" description="Observed histogram, normal reference curve, specification limits, mean, and plus or minus three sigma references are visually distinct." exportName="spc-distribution-reference-limits" dataCount={histogram.length + normalCurve.length} empty={histogram.length === 0} />;
});
