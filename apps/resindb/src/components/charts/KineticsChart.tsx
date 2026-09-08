import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { useLanguage } from '@/contexts/LanguageContext';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE } from './scientificFigurePolicy';

interface KineticsChartProps {
  points: { x: number; y: number }[];
  line: { x: number; y: number }[];
  isoCurve: { time: number; alpha: number }[];
  isoTemp: number;
  theme: 'light' | 'dark';
}

export const KineticsChart: React.FC<KineticsChartProps> = React.memo(({ points, line, isoCurve, isoTemp, theme }) => {
  const { language } = useLanguage();
  const option = useMemo<EChartsOption>(() => ({
    title: [
      { text: 'Kissinger linearization', subtext: language === 'en' ? 'Observed DSC peak points and fitted line.' : 'DSC 峰温观测点与拟合直线。', left: 'center', top: 4, textStyle: { fontSize: 13, fontWeight: 650 }, subtextStyle: { fontSize: 9 } },
      { text: language === 'en' ? `Isothermal conversion scenario at ${isoTemp} °C` : `${isoTemp} °C 等温转化情景`, subtext: language === 'en' ? 'Derived first-order extrapolation, not a measured isothermal experiment.' : '由峰温拟合外推的一阶情景，不是实测等温实验。', left: 'center', top: '51%', textStyle: { fontSize: 13, fontWeight: 650 }, subtextStyle: { fontSize: 9 } },
    ],
    legend: { bottom: 4 },
    grid: [
      { top: 64, bottom: '56%', left: 72, right: 36, containLabel: true },
      { top: '62%', bottom: 64, left: 72, right: 36, containLabel: true },
    ],
    xAxis: [
      { gridIndex: 0, type: 'value', name: '1000/Tp (K⁻¹)', nameLocation: 'middle', nameGap: 32, scale: true, axisLabel: { formatter: (value: number) => (value * 1_000).toFixed(2) } },
      { gridIndex: 1, type: 'value', name: language === 'en' ? 'Isothermal time (min)' : '等温时间（min）', nameLocation: 'middle', nameGap: 32, scale: true },
    ],
    yAxis: [
      { gridIndex: 0, type: 'value', name: 'ln(β/Tp²)', nameLocation: 'middle', nameGap: 46, scale: true },
      { gridIndex: 1, type: 'value', name: language === 'en' ? 'Conversion (%)' : '转化率（%）', nameLocation: 'middle', nameGap: 46, min: 0, max: 100 },
    ],
    tooltip: { trigger: 'axis' },
    series: [
      { name: language === 'en' ? 'Observed DSC peaks' : 'DSC 峰温观测点', type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: points.map((point) => [point.x, point.y]), symbolSize: 7, itemStyle: { color: SCIENTIFIC_PALETTE[2] } },
      { name: language === 'en' ? 'Kissinger fit (model)' : 'Kissinger 拟合（模型）', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: line.map((point) => [point.x, point.y]), symbol: 'none', lineStyle: { width: 1.6, type: 'dashed', color: SCIENTIFIC_PALETTE[0] } },
      { name: language === 'en' ? 'Isothermal scenario' : '等温情景外推', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: isoCurve.map((point) => [point.time, point.alpha]), symbol: 'none', smooth: false, lineStyle: { width: 1.8, color: SCIENTIFIC_PALETTE[1] } },
    ],
  }), [isoCurve, isoTemp, language, line, points]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Kissinger kinetics and isothermal conversion scenario" description="Observed DSC peak points and their Kissinger fit are separated from the derived isothermal scenario." exportName="kissinger-kinetics" dataCount={points.length + line.length + isoCurve.length} empty={points.length < 3} height="100%" />;
});
