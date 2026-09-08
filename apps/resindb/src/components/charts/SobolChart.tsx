import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, formatScientificNumber } from './scientificFigurePolicy';

interface SobolChartProps {
  firstOrder: { name: string; value: number }[];
  totalEffect: { name: string; value: number }[];
  interactions: { name: string; value: number }[];
  theme: 'light' | 'dark';
}

export const SobolChart: React.FC<SobolChartProps> = React.memo(({ firstOrder, totalEffect, interactions, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    const firstByName = new Map(firstOrder.map((entry) => [entry.name, entry.value]));
    const interactionByName = new Map(interactions.map((entry) => [entry.name, entry.value]));
    const ordered = [...totalEffect].reverse();
    return {
      title: { text: 'Jansen variance-based sensitivity indices', subtext: 'Sampling uses independent pseudo-random normal Saltelli A/B matrices. ST−S1 is aggregate higher-order contribution, not pairwise interaction.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      legend: { bottom: 4, data: ['First order S1', 'Aggregate ST−S1'] },
      grid: { top: 76, bottom: 70, left: 28, right: 40, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (params: unknown) => { const entries = Array.isArray(params) ? params as Array<{ name: string; seriesName: string; value: number }> : []; if (!entries.length) return ''; const name = entries[0].name; const first = Number(firstByName.get(name) ?? 0); const aggregate = Number(interactionByName.get(name) ?? 0); const total = Number(totalEffect.find((entry) => entry.name === name)?.value ?? first + aggregate); return `<strong>${name}</strong><br/>Total effect ST: ${formatScientificNumber(total)}<br/>First order S1: ${formatScientificNumber(first)}<br/>Aggregate ST−S1: ${formatScientificNumber(aggregate)}<br/><em>Not a pairwise interaction estimate.</em>`; } },
      xAxis: { type: 'value', name: 'Sensitivity index', nameLocation: 'middle', nameGap: 34, min: 0 },
      yAxis: { type: 'category', data: ordered.map((entry) => entry.name), axisLabel: { width: 160, overflow: 'truncate' }, axisTick: { show: false } },
      series: [
        { name: 'First order S1', type: 'bar', stack: 'total', data: ordered.map((entry) => firstByName.get(entry.name) ?? 0), barMaxWidth: 22, itemStyle: { color: SCIENTIFIC_PALETTE[0] } },
        { name: 'Aggregate ST−S1', type: 'bar', stack: 'total', data: ordered.map((entry) => interactionByName.get(entry.name) ?? 0), barMaxWidth: 22, itemStyle: { color: SCIENTIFIC_PALETTE[4] } },
      ],
    };
  }, [firstOrder, interactions, totalEffect]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Jansen variance based sensitivity indices" description="First-order and total-effect sensitivity are displayed, with total-minus-first-order labelled as aggregate higher-order contribution rather than pairwise interaction." exportName="jansen-sensitivity-indices" dataCount={totalEffect.length * 2} empty={totalEffect.length === 0} />;
});
