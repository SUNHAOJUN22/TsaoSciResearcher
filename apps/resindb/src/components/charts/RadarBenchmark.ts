import type { EChartsOption } from '@/lib/echarts';
import {
  SCIENTIFIC_PALETTE,
  scientificGridColor,
  scientificMutedColor,
  scientificTextColor,
} from './scientificFigurePolicy';

interface RadarData {
  name: string;
  value: number[];
}

interface Indicator {
  name: string;
  max?: number;
  min?: number;
}

export const getRadarChartOption = (
  data: RadarData[],
  theme: 'light' | 'dark',
  customIndicators?: Indicator[],
  language: 'zh' | 'en' = 'zh',
): EChartsOption => {
  const defaultLabels = language === 'en'
    ? ['Flow', 'Rigidity', 'Thermal resistance', 'Tensile', 'Impact', 'Data completeness']
    : ['流动性', '硬度与刚性', '耐热性', '拉伸性能', '冲击强度', '数据完整度'];
  const indicators = customIndicators?.length
    ? customIndicators.map((indicator) => ({ min: 0, max: 100, ...indicator }))
    : defaultLabels.map((name) => ({ name, min: 0, max: 100 }));

  return {
    title: {
      text: language === 'en' ? 'Normalized performance fingerprint' : '归一化性能指纹',
      subtext: language === 'en'
        ? 'Percentile ranks within the active sample set; axes are dimensionless 0–100 scores.'
        : '基于当前样本集的百分位排名；各轴均为无量纲 0–100 分数。',
      left: 'center',
      top: 6,
      textStyle: { color: scientificTextColor(theme), fontSize: 14, fontWeight: 650 },
      subtextStyle: { color: scientificMutedColor(theme), fontSize: 10 },
    },
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 4,
      data: data.map((entry) => entry.name),
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 5,
      center: ['50%', '52%'],
      radius: '58%',
      axisName: { color: scientificMutedColor(theme), fontWeight: 600, fontSize: 10 },
      splitLine: { lineStyle: { color: scientificGridColor(theme) } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: scientificGridColor(theme) } },
    },
    series: [{
      name: language === 'en' ? 'Percentile fingerprint' : '百分位指纹',
      type: 'radar',
      data: data.map((item, index) => ({
        value: item.value.map((value) => Math.max(0, Math.min(100, Number(value)))),
        name: item.name,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 1.8, opacity: 0.9, color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length] },
        areaStyle: { opacity: 0.06, color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length] },
        itemStyle: { color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length] },
      })),
    }],
  };
};
