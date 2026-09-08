import type { EChartsOption } from '@/lib/echarts';
import { SCIENTIFIC_PALETTE, scientificMutedColor } from './scientificFigurePolicy';

export const getParallelChartOption = (
  theme: 'light' | 'dark',
  data: {
    series: { name: string; value: number[] }[];
    indicators: { name: string; max: number; min?: number }[];
  },
  language: 'zh' | 'en' = 'zh',
): EChartsOption | null => {
  if (!data?.series?.length || !data.indicators?.length) return null;
  const opacity = data.series.length > 250 ? 0.08 : data.series.length > 80 ? 0.16 : 0.45;
  return {
    title: {
      text: language === 'en' ? 'Multivariate profile comparison' : '多变量轮廓对比',
      subtext: language === 'en'
        ? 'Axes retain their declared ranges; line opacity adapts to sample count.'
        : '各轴保留声明范围；线条透明度随样本量调整。',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 650 },
      subtextStyle: { color: scientificMutedColor(theme), fontSize: 10 },
    },
    legend: { data: data.series.map((entry) => entry.name), bottom: 4 },
    parallelAxis: data.indicators.map((indicator, index) => ({
      dim: index,
      name: indicator.name,
      min: indicator.min ?? 0,
      max: indicator.max,
      nameLocation: 'end' as const,
      nameTextStyle: { color: scientificMutedColor(theme), fontSize: 10 },
      axisLabel: { color: scientificMutedColor(theme), fontSize: 9, hideOverlap: true },
    })),
    parallel: {
      left: 56,
      right: 56,
      bottom: 62,
      top: 78,
      parallelAxisDefault: { type: 'value', nameLocation: 'end', nameGap: 10 },
    },
    series: data.series.map((entry, index) => ({
      name: entry.name,
      type: 'parallel' as const,
      lineStyle: {
        width: data.series.length > 80 ? 1 : 1.4,
        opacity,
        color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length],
      },
      emphasis: { lineStyle: { width: 2.2, opacity: 1 } },
      data: [entry.value],
      progressive: 500,
    })),
  };
};
