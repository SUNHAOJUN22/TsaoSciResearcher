import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, escapeScientificHtml, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';

interface MooChartProps {
  evaluatedCandidates: { params: Record<string, number>; means: Record<string, number> }[];
  paretoFront: { params: Record<string, number>; means: Record<string, number>; stds: Record<string, number> }[];
  historical: Record<string, number>[];
  targets: { name: string; maximize: boolean }[];
  theme: 'light' | 'dark';
}

export const MooChart: React.FC<MooChartProps> = React.memo(({ evaluatedCandidates, paretoFront, historical, targets, theme }) => {
  const option = useMemo<EChartsOption | null>(() => {
    if (targets.length !== 2) return null;
    const [xTarget, yTarget] = targets;
    const sortedPareto = [...paretoFront].sort((left, right) => left.means[xTarget.name] - right.means[xTarget.name]);
    return {
      title: { text: 'Two-objective Pareto exploration', subtext: 'Candidate and Pareto coordinates are Gaussian-process mean predictions; historical markers are observed records.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      legend: { bottom: 4, data: ['Historical observations', 'Evaluated model pool', 'Predicted Pareto front'] },
      grid: { top: 76, bottom: 70, left: 70, right: 36, containLabel: true },
      tooltip: { trigger: 'item', formatter: (params: unknown) => {
        const item = scientificTooltipItem(params);
        const value = item?.value as [number, number] | undefined;
        if (!value) return '';
        if (item?.seriesName === 'Predicted Pareto front') {
          const dataIndex = typeof item.dataIndex === 'number' ? item.dataIndex : -1;
          const point = sortedPareto[dataIndex];
          const parameters = point ? Object.entries(point.params).map(([name, parameter]) => `${escapeScientificHtml(name)}: ${formatScientificNumber(parameter)}`).join('<br/>') : '';
          return `Predicted non-dominated candidate<br/>${escapeScientificHtml(xTarget.name)}: ${formatScientificNumber(value[0])}<br/>${escapeScientificHtml(yTarget.name)}: ${formatScientificNumber(value[1])}${parameters ? `<br/><hr/>${parameters}` : ''}`;
        }
        return `${String(item?.seriesName ?? '')}<br/>${escapeScientificHtml(xTarget.name)}: ${formatScientificNumber(value[0])}<br/>${escapeScientificHtml(yTarget.name)}: ${formatScientificNumber(value[1])}`;
      } },
      xAxis: { type: 'value', name: `${xTarget.name} (${xTarget.maximize ? 'maximize' : 'minimize'})`, nameLocation: 'middle', nameGap: 34, scale: true },
      yAxis: { type: 'value', name: `${yTarget.name} (${yTarget.maximize ? 'maximize' : 'minimize'})`, nameLocation: 'middle', nameGap: 48, scale: true },
      series: [
        { name: 'Evaluated model pool', type: 'scatter', data: evaluatedCandidates.map((candidate) => [candidate.means[xTarget.name], candidate.means[yTarget.name]]), symbolSize: 3, progressive: 2_000, large: evaluatedCandidates.length > 8_000, itemStyle: { color: '#94a3b8', opacity: 0.35 } },
        { name: 'Historical observations', type: 'scatter', data: historical.map((entry) => [entry[xTarget.name], entry[yTarget.name]]), symbolSize: 7, symbol: 'triangle', itemStyle: { color: SCIENTIFIC_PALETTE[0] } },
        { name: 'Predicted Pareto front', type: 'line', data: sortedPareto.map((entry) => [entry.means[xTarget.name], entry.means[yTarget.name]]), symbolSize: 6, lineStyle: { color: SCIENTIFIC_PALETTE[1], width: 1.8 }, itemStyle: { color: SCIENTIFIC_PALETTE[1] } },
      ],
    };
  }, [evaluatedCandidates, historical, paretoFront, targets]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Two-objective predicted Pareto front" description="Historical observations are separated from Gaussian-process candidate means and the predicted non-dominated front." exportName="predicted-pareto-front" dataCount={evaluatedCandidates.length + historical.length + paretoFront.length} empty={!option} />;
});
