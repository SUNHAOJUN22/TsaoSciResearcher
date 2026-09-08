import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import { ScientificEChart } from './ScientificEChart';
import { SCIENTIFIC_PALETTE, SCIENTIFIC_SEQUENTIAL, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';

interface RsmHeatmapChartProps {
  grid: { x1: number; x2: number; y: number }[][];
  stationaryPoint?: { x1: number; x2: number; y: number } | null;
  minX1: number;
  maxX1: number;
  minX2: number;
  maxX2: number;
  dataPoints: { x1: number; x2: number; y: number }[];
  x1Label: string;
  x2Label: string;
  yLabel: string;
  theme: 'light' | 'dark';
}

export const RsmHeatmapChart: React.FC<RsmHeatmapChartProps> = React.memo((props) => {
  const { grid, stationaryPoint, minX1, maxX1, minX2, maxX2, dataPoints, x1Label, x2Label, yLabel, theme } = props;
  const option = useMemo<EChartsOption>(() => {
    const heatmapData = grid.flatMap((row) => row.map((cell) => [cell.x1, cell.x2, cell.y] as [number, number, number]));
    let minimum = Infinity;
    let maximum = -Infinity;
    for (const point of heatmapData) {
      minimum = Math.min(minimum, point[2]);
      maximum = Math.max(maximum, point[2]);
    }
    const series: EChartsOption['series'] = [
      {
        name: 'Quadratic response surface (model)',
        type: 'heatmap',
        data: heatmapData,
        emphasis: { disabled: true },
        tooltip: {
          formatter: (params: unknown) => {
            const item = scientificTooltipItem(params);
            const value = item?.data as [number, number, number] | undefined;
            return value
              ? `${x1Label}: ${formatScientificNumber(value[0])}<br/>${x2Label}: ${formatScientificNumber(value[1])}<br/>Fitted ${yLabel}: ${formatScientificNumber(value[2])}`
              : '';
          },
        },
      },
      {
        name: 'Observed data',
        type: 'scatter',
        data: dataPoints.map((point) => [point.x1, point.x2, point.y]),
        symbolSize: 7,
        itemStyle: { color: theme === 'dark' ? '#ffffff' : '#0f172a', borderColor: SCIENTIFIC_PALETTE[0], borderWidth: 1.5 },
        tooltip: {
          formatter: (params: unknown) => {
            const item = scientificTooltipItem(params);
            const value = item?.data as [number, number, number] | undefined;
            return value
              ? `Observed data<br/>${x1Label}: ${formatScientificNumber(value[0])}<br/>${x2Label}: ${formatScientificNumber(value[1])}<br/>${yLabel}: ${formatScientificNumber(value[2])}`
              : '';
          },
        },
      },
    ];
    if (stationaryPoint) {
      series.push({
        name: 'Stationary point (classification not implied)',
        type: 'scatter',
        data: [[stationaryPoint.x1, stationaryPoint.x2, stationaryPoint.y]],
        symbol: 'diamond',
        symbolSize: 12,
        itemStyle: { color: SCIENTIFIC_PALETTE[1], borderColor: '#ffffff', borderWidth: 1.5 },
        tooltip: {
          formatter: () => `Stationary point — not automatically an optimum<br/>${x1Label}: ${formatScientificNumber(stationaryPoint.x1)}<br/>${x2Label}: ${formatScientificNumber(stationaryPoint.x2)}<br/>Fitted ${yLabel}: ${formatScientificNumber(stationaryPoint.y)}`,
        },
        z: 4,
      });
    }
    return {
      title: {
        text: 'Quadratic response-surface model',
        subtext: 'Heatmap is fitted model output; outlined markers are observations. Stationary-point classification is not implied.',
        left: 'center',
        top: 6,
        textStyle: { fontSize: 14, fontWeight: 650 },
        subtextStyle: { fontSize: 10 },
      },
      grid: { top: 76, bottom: 62, left: 68, right: 86, containLabel: true },
      xAxis: { type: 'value', name: x1Label, nameLocation: 'middle', nameGap: 34, min: minX1, max: maxX1 },
      yAxis: { type: 'value', name: x2Label, nameLocation: 'middle', nameGap: 48, min: minX2, max: maxX2 },
      visualMap: {
        min: Number.isFinite(minimum) ? minimum : 0,
        max: Number.isFinite(maximum) ? maximum : 1,
        calculable: true,
        realtime: false,
        inRange: { color: [...SCIENTIFIC_SEQUENTIAL] },
        right: 4,
        top: 'middle',
        text: [yLabel, ''],
      },
      series,
    };
  }, [dataPoints, grid, maxX1, maxX2, minX1, minX2, stationaryPoint, theme, x1Label, x2Label, yLabel]);

  const dataCount = grid.reduce((sum, row) => sum + row.length, 0) + dataPoints.length + (stationaryPoint ? 1 : 0);
  return (
    <ScientificEChart
      option={option}
      theme={theme}
      ariaLabel="Quadratic response surface with observed points"
      description="The heatmap is fitted model output. Observations and the stationary point are drawn as separate marker layers."
      exportName="quadratic-response-surface"
      dataCount={dataCount}
      empty={grid.length === 0}
    />
  );
});
