import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { useLanguage } from '@/contexts/LanguageContext';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, formatScientificNumber } from './scientificFigurePolicy';

interface BayesChartProps {
  historical: { index: number; y: number; y_pred: number; y_std: number }[];
  suggestions: { params: Record<string, number>; mean: number; std: number; ei: number }[];
  targetName: string;
  maximize: boolean;
  theme: 'light' | 'dark';
}

export const BayesChart: React.FC<BayesChartProps> = React.memo(({ historical, suggestions, targetName, maximize, theme }) => {
  const { t, language } = useLanguage();
  const option = useMemo<EChartsOption | null>(() => {
    const best = suggestions[0];
    if (!best) return null;
    const suggestionIndex = historical.length + 2;
    const lower = historical.map((entry) => entry.y_pred - 2 * entry.y_std);
    const upperWidth = historical.map((entry, index) => 4 * entry.y_std || Math.max(0, entry.y_pred + 2 * entry.y_std - lower[index]));
    return {
      title: {
        text: t('bayesChartTitle'),
        subtext: language === 'en'
          ? `Historical observations and Gaussian-process model uncertainty; objective: ${maximize ? 'maximize' : 'minimize'} ${targetName}.`
          : `历史观测与高斯过程模型不确定性；目标：${maximize ? '最大化' : '最小化'} ${targetName}。`,
        left: 'center',
        top: 6,
        textStyle: { fontSize: 14, fontWeight: 650 },
        subtextStyle: { fontSize: 10 },
      },
      legend: { bottom: 4 },
      grid: { top: 76, bottom: 70, left: 70, right: 36, containLabel: true },
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const entries = Array.isArray(params) ? params as Array<{ dataIndex: number }> : [];
          const dataIndex = entries[0]?.dataIndex ?? -1;
          if (dataIndex === historical.length) {
            return `${t('bayesChartTooltipBest')}<br/>${t('bayesChartTooltipMean')}: ${formatScientificNumber(best.mean)}<br/>${t('bayesChartTooltipStd')}: ${formatScientificNumber(best.std)}<br/>EI: ${formatScientificNumber(best.ei)}`;
          }
          const row = historical[dataIndex];
          return row
            ? `${t('bayesChartTooltipFeedback')}<br/>${t('bayesChartTooltipActual')} ${targetName}: ${formatScientificNumber(row.y)}<br/>${t('bayesChartTooltipGpMean')}: ${formatScientificNumber(row.y_pred)}<br/>${t('bayesChartTooltipGpStd')}: ${formatScientificNumber(row.y_std)}`
            : '';
        },
      },
      xAxis: {
        type: 'category',
        data: [...historical.map((_, index) => index + 1), suggestionIndex],
        name: t('bayesChartXAxis'),
        nameLocation: 'middle',
        nameGap: 34,
        axisLabel: { show: false },
        axisTick: { show: false },
      },
      yAxis: { type: 'value', name: targetName, nameLocation: 'middle', nameGap: 50, scale: true },
      series: [
        {
          name: t('bayesChartGroundTruth'),
          type: 'scatter',
          data: historical.map((entry, index) => [index + 1, entry.y]),
          symbolSize: 6,
          itemStyle: { color: SCIENTIFIC_PALETTE[7], opacity: 0.75 },
        },
        {
          name: t('bayesChartMean'),
          type: 'line',
          data: historical.map((entry) => entry.y_pred),
          symbol: 'none',
          lineStyle: { color: SCIENTIFIC_PALETTE[0], width: 1.6 },
        },
        {
          name: t('bayesChartLowerConfidence'),
          type: 'line',
          data: lower,
          stack: 'gp-band',
          symbol: 'none',
          lineStyle: { opacity: 0 },
          silent: true,
        },
        {
          name: t('bayesChartConfidenceInterval'),
          type: 'line',
          data: upperWidth,
          stack: 'gp-band',
          symbol: 'none',
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(0,114,178,0.16)' },
          silent: true,
        },
        {
          name: t('bayesChartNextBest'),
          type: 'scatter',
          data: [[suggestionIndex, best.mean]],
          symbol: 'diamond',
          symbolSize: 13,
          itemStyle: { color: SCIENTIFIC_PALETTE[4], borderColor: '#ffffff', borderWidth: 1 },
          z: 5,
        },
      ],
    };
  }, [historical, language, maximize, suggestions, t, targetName]);

  return <ScientificEChart option={option} theme={theme} ariaLabel="Gaussian-process inverse-design model" description="Historical observations, Gaussian-process mean, model uncertainty band, and the expected-improvement candidate are separate layers." exportName="gaussian-process-inverse-design" dataCount={historical.length * 4 + 1} empty={!option} />;
});
