import type { EChartsOption } from '@/lib/echarts';
import {
  SCIENTIFIC_PALETTE,
  escapeScientificHtml,
  formatScientificNumber,
  scientificMutedColor,
  scientificTooltipItem,
} from './scientificFigurePolicy';

type ScatterSeries = { name: string; data: [number, number, string][] };
type ScatterInput = {
  series?: ScatterSeries[];
  xAxis?: string;
  yAxis?: string;
  xBounds?: { min: number; max: number };
  yBounds?: { min: number; max: number };
};

export const getMfrDensityChartOption = (
  data: ScatterInput | unknown[],
  theme: 'light' | 'dark',
  language: 'zh' | 'en' = 'zh',
): EChartsOption => {
  const source = Array.isArray(data) ? {} : data;
  const seriesData = (Array.isArray(data) ? data : source.series ?? []) as ScatterSeries[];
  const xAxisName = source.xAxis ?? (language === 'en' ? 'Density' : '密度');
  const yAxisName = source.yAxis ?? 'MFR';
  const pointCount = seriesData.reduce((sum, series) => sum + series.data.length, 0);

  return {
    title: {
      text: language === 'en' ? 'Processability–structure map' : '加工性–结构映射',
      subtext: language === 'en'
        ? 'Observed values; MFR is displayed on a logarithmic scale.'
        : '绘制观测值；MFR 使用对数坐标。',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 650 },
      subtextStyle: { color: scientificMutedColor(theme), fontSize: 10 },
    },
    grid: { left: 70, right: 36, bottom: 70, top: 72, containLabel: true },
    legend: { bottom: 4 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'filter' },
      { type: 'inside', yAxisIndex: 0, filterMode: 'filter' },
    ],
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const item = scientificTooltipItem(params);
        const value = item?.value as [number, number, string] | undefined;
        if (!value) return '';
        return `<strong>${escapeScientificHtml(value[2])}</strong><br/>${escapeScientificHtml(xAxisName)}: ${formatScientificNumber(Number(value[0]))}<br/>${escapeScientificHtml(yAxisName)}: ${formatScientificNumber(Number(value[1]))}`;
      },
    },
    xAxis: {
      type: 'value',
      name: xAxisName,
      nameLocation: 'middle',
      nameGap: 34,
      scale: true,
      min: source.xBounds?.min,
      max: source.xBounds?.max,
    },
    yAxis: {
      type: 'log',
      name: yAxisName,
      nameLocation: 'middle',
      nameGap: 48,
      min: source.yBounds?.min,
      max: source.yBounds?.max,
    },
    series: seriesData.map((series, index) => ({
      name: series.name,
      type: 'scatter' as const,
      symbolSize: pointCount > 3_000 ? 4 : 7,
      progressive: 2_000,
      progressiveThreshold: 3_000,
      large: pointCount > 8_000,
      largeThreshold: 8_000,
      itemStyle: { opacity: 0.72, color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length] },
      emphasis: { scale: 1.1, itemStyle: { opacity: 1, borderWidth: 1 } },
      data: series.data.filter((point) => Number.isFinite(Number(point[0])) && Number(point[1]) > 0),
    })),
  };
};
