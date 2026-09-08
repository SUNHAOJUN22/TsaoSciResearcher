import type { EChartsOption } from '@/lib/echarts';
import { materialEngine } from '@/lib/materialScience';
import {
  SCIENTIFIC_PALETTE,
  escapeScientificHtml,
  formatScientificNumber,
  scientificMutedColor,
  scientificTooltipItem,
} from './scientificFigurePolicy';

type AshbySeries = { name: string; data: [number, number, string][] };
type AshbyInput = {
  series?: AshbySeries[];
  xAxis?: string;
  yAxis?: string;
  xBounds?: { min: number; max: number };
  yBounds?: { min: number; max: number };
};

export const getAshbyChartOption = (
  data: AshbyInput | unknown[],
  theme: 'light' | 'dark',
  language: 'zh' | 'en' = 'zh',
): EChartsOption => {
  const source = Array.isArray(data) ? {} : data;
  const seriesData = (Array.isArray(data) ? data : source.series ?? []) as AshbySeries[];
  const xAxisName = source.xAxis ?? (language === 'en' ? 'Property X' : '性能 X');
  const yAxisName = source.yAxis ?? (language === 'en' ? 'Property Y' : '性能 Y');
  const allPoints = seriesData.flatMap((series) => series.data)
    .map((point) => [Number(point[0]), Number(point[1])] as [number, number])
    .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y) && x > 0 && y > 0);
  const correlation = allPoints.length > 5 ? materialEngine.analyzeCorrelationLog(allPoints) : null;

  let observedMinX = Infinity;
  let observedMaxX = -Infinity;
  for (const [x] of allPoints) {
    observedMinX = Math.min(observedMinX, x);
    observedMaxX = Math.max(observedMaxX, x);
  }
  const minX = source.xBounds?.min ?? (Number.isFinite(observedMinX) ? observedMinX : 0.1);
  const maxX = source.xBounds?.max ?? (Number.isFinite(observedMaxX) ? observedMaxX : 100);
  const fitData: [number, number][] = [];
  if (correlation && minX > 0 && maxX > minX) {
    const logMin = Math.log10(minX);
    const logMax = Math.log10(maxX);
    for (let index = 0; index < 48; index++) {
      const x = 10 ** (logMin + (index / 47) * (logMax - logMin));
      const y = correlation.regressionFn(x);
      if (Number.isFinite(y) && y > 0) fitData.push([x, y]);
    }
  }

  const paretoCandidates = seriesData.flatMap((series) => series.data)
    .map((point) => ({ x: Number(point[0]), y: Number(point[1]), name: String(point[2]) }))
    .filter((point) => point.x > 0 && point.y > 0);
  const paretoNames = new Set(materialEngine.getParetoPoints(paretoCandidates));
  const pointCount = seriesData.reduce((sum, series) => sum + series.data.length, 0);

  return {
    title: {
      text: language === 'en' ? 'Ashby property map' : 'Ashby 性能映射',
      subtext: correlation
        ? (language === 'en'
          ? `Log–log power-law fit shown as a model: R²=${correlation.r2.toFixed(3)}`
          : `虚线为对数域幂律拟合模型：R²=${correlation.r2.toFixed(3)}`)
        : (language === 'en' ? 'Observed positive values only; no fit is shown.' : '仅绘制正值观测点；样本不足时不显示拟合。'),
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
        if (item?.seriesType === 'line') {
          return language === 'en' ? 'Log–log power-law fit (model)' : '对数域幂律拟合（模型）';
        }
        const value = item?.value as [number, number, string] | undefined;
        if (!value) return '';
        const name = escapeScientificHtml(value[2]);
        const pareto = paretoNames.has(String(value[2]));
        return `<strong>${name}</strong><br/>${escapeScientificHtml(xAxisName)}: ${formatScientificNumber(Number(value[0]))}<br/>${escapeScientificHtml(yAxisName)}: ${formatScientificNumber(Number(value[1]))}${pareto ? `<br/><b>${language === 'en' ? 'Non-dominated observation' : '非支配观测点'}</b>` : ''}`;
      },
    },
    xAxis: {
      type: 'log',
      name: xAxisName,
      nameLocation: 'middle',
      nameGap: 34,
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
    series: [
      ...seriesData.map((series, index) => ({
        name: series.name,
        type: 'scatter' as const,
        symbolSize: pointCount > 3_000 ? 4 : 7,
        progressive: 2_000,
        progressiveThreshold: 3_000,
        large: pointCount > 8_000,
        largeThreshold: 8_000,
        itemStyle: { opacity: 0.72, color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length] },
        emphasis: { scale: 1.1, itemStyle: { opacity: 1, borderWidth: 1 } },
        data: series.data.filter((point) => Number(point[0]) > 0 && Number(point[1]) > 0),
      })),
      ...(fitData.length ? [{
        name: language === 'en' ? 'Power-law fit (model)' : '幂律拟合（模型）',
        type: 'line' as const,
        data: fitData,
        lineStyle: { type: 'dashed' as const, color: scientificMutedColor(theme), width: 1.5, opacity: 0.9 },
        symbol: 'none',
        silent: true,
        z: 2,
      }] : []),
    ],
  };
};
