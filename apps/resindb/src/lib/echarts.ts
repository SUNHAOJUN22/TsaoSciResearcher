import * as echarts from 'echarts/core';
import {
  BarChart,
  BoxplotChart,
  CustomChart,
  EffectScatterChart,
  GraphChart,
  HeatmapChart,
  LineChart,
  ParallelChart,
  PieChart,
  RadarChart,
  ScatterChart,
} from 'echarts/charts';
import {
  AriaComponent,
  CalendarComponent,
  DataZoomComponent,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  ParallelComponent,
  PolarComponent,
  SingleAxisComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
  TransformComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  BarChart,
  BoxplotChart,
  CustomChart,
  EffectScatterChart,
  GraphChart,
  HeatmapChart,
  LineChart,
  ParallelChart,
  PieChart,
  RadarChart,
  ScatterChart,
  AriaComponent,
  CalendarComponent,
  DataZoomComponent,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  ParallelComponent,
  PolarComponent,
  SingleAxisComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
  TransformComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export * from 'echarts/core';
export { echarts };
export type { EChartsOption, SeriesOption } from 'echarts';
export type { GridComponentOption, TooltipComponentOption } from 'echarts/components';
export type { ScatterSeriesOption } from 'echarts/charts';
