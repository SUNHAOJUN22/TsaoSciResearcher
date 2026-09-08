import React, { useMemo } from 'react';
import * as echarts from '@/lib/echarts';
import { useTheme } from '@/contexts/ThemeContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { getRadarChartOption } from './RadarBenchmark';
import { getAshbyChartOption } from './AshbyScatter';
import { getGpcChartOption } from './GpcDistribution';
import { getRheologyChartOption } from './RheologyCurve';
import { getMfrDensityChartOption } from './MfrDensityScatter';
import { getParallelChartOption } from './ParallelCoordinates';
import { ScientificEChart } from './ScientificEChart';
import type { Product } from '@/types/index';

export type ChartType = 'radar' | 'ashby' | 'gpc' | 'rheology' | 'mfr_density' | 'parallel';

interface ScientificChartProps {
  type: ChartType;
  data: unknown;
  loading?: boolean;
  className?: string;
  height?: string | number;
  onChartReady?: (instance: echarts.ECharts) => void;
}

function countSeriesPoints(option: echarts.EChartsOption | null): number {
  if (!option?.series) return 0;
  const series = Array.isArray(option.series) ? option.series : [option.series];
  return series.reduce((total, entry) => {
    if (!entry || typeof entry !== 'object') return total;
    const data = (entry as { data?: unknown[] }).data;
    return total + (Array.isArray(data) ? data.length : 0);
  }, 0);
}

function hasPlottableData(type: ChartType, data: unknown): boolean {
  if (!data) return false;
  if (type === 'rheology') {
    return Array.isArray((data as { products?: unknown[] }).products)
      && ((data as { products: unknown[] }).products.length > 0);
  }
  if (type === 'radar') {
    const series = Array.isArray(data) ? data : (data as { series?: unknown[] }).series;
    return Array.isArray(series) && series.some((entry) => (
      Array.isArray((entry as { value?: unknown[] }).value)
      && (entry as { value: unknown[] }).value.some((value) => Number.isFinite(Number(value)))
    ));
  }
  if (type === 'ashby' || type === 'mfr_density') {
    const series = Array.isArray(data) ? data : (data as { series?: unknown[] }).series;
    return Array.isArray(series) && series.some((entry) => Array.isArray((entry as { data?: unknown[] }).data)
      && ((entry as { data: unknown[] }).data.length > 0));
  }
  if (type === 'parallel') {
    const value = data as { series?: unknown[]; indicators?: unknown[] };
    return Array.isArray(value.series) && value.series.length > 0
      && Array.isArray(value.indicators) && value.indicators.length > 0;
  }
  return !Array.isArray(data) || data.length > 0;
}

export const ScientificChart: React.FC<ScientificChartProps> = React.memo(({
  type,
  data,
  loading = false,
  className = '',
  height = '100%',
  onChartReady,
}) => {
  const { theme } = useTheme();
  const { language } = useLanguage();
  const build = useMemo(() => {
    try {
      const typed = (data ?? {}) as Record<string, unknown>;
      let option: echarts.EChartsOption | null;
      switch (type) {
        case 'radar': {
          const series = Array.isArray(data) ? data : (typed.series as unknown[] ?? []);
          option = getRadarChartOption(
            series as { name: string; value: number[] }[],
            theme,
            typed.indicators as { name: string; min?: number; max?: number }[] | undefined,
            language,
          );
          break;
        }
        case 'ashby':
          option = getAshbyChartOption(data as Parameters<typeof getAshbyChartOption>[0], theme, language);
          break;
        case 'mfr_density':
          option = getMfrDensityChartOption(data as Parameters<typeof getMfrDensityChartOption>[0], theme, language);
          break;
        case 'parallel':
          option = getParallelChartOption(theme, data as Parameters<typeof getParallelChartOption>[1], language);
          break;
        case 'gpc':
          if (!Array.isArray(data)) throw new Error('GPC proxy input must be a product array.');
          option = getGpcChartOption(data as Product[], theme, language);
          break;
        case 'rheology':
          if (!Array.isArray(typed.products)) throw new Error('Rheology proxy input is missing products.');
          option = getRheologyChartOption(
            typed.products as Product[],
            theme,
            (typed.temps as number[] | undefined) ?? [],
            language,
          );
          break;
        default:
          option = null;
      }
      return { option, error: null as string | null };
    } catch (error) {
      return { option: null, error: error instanceof Error ? error.message : String(error) };
    }
  }, [data, language, theme, type]);

  const label = language === 'en' ? `Scientific figure: ${type}` : `科研图：${type}`;
  return (
    <ScientificEChart
      option={build.option}
      theme={theme}
      ariaLabel={label}
      description={language === 'en'
        ? 'Interactive scientific figure. Model-generated curves and measured observations are visually distinguished.'
        : '交互式科研图。模型生成曲线与观测数据采用不同视觉编码。'}
      exportName={`resindb-${type}`}
      dataCount={countSeriesPoints(build.option)}
      loading={loading}
      empty={!hasPlottableData(type, data)}
      error={build.error}
      className={className}
      height={height}
      onChartReady={onChartReady}
    />
  );
});
