import { describe, expect, it } from 'vitest';
import { getRadarChartOption } from '@/components/charts/RadarBenchmark';
import { getAshbyChartOption } from '@/components/charts/AshbyScatter';
import { getGpcChartOption } from '@/components/charts/GpcDistribution';
import { getRheologyChartOption } from '@/components/charts/RheologyCurve';
import type { Product } from '@/types/index';

const product = {
  id: 'p-1',
  gradeName: 'PP-TEST',
  manufacturer: 'Test',
  manufacturerId: 'm-test',
  categoryIds: ['聚丙烯'],
  properties: { MFR: { value: 5, unit: 'g/10 min' } },
  createdAt: '2026-01-01',
  updatedAt: '2026-01-01',
} as Product;

describe('scientific chart semantics', () => {
  it('uses dimensionless percentile bounds for radar values', () => {
    const option = getRadarChartOption([{ name: 'A', value: [10, 20, 30, 40, 50, 60] }], 'light', undefined, 'en');
    const radar = option.radar as { indicator: { min: number; max: number }[] };
    expect(radar.indicator.every((entry) => entry.min === 0 && entry.max === 100)).toBe(true);
  });

  it('does not draw an unsupported fallback fit on a sparse log-log Ashby map', () => {
    const option = getAshbyChartOption({
      series: [{ name: 'A', data: [[1, 2, 'a'], [2, 3, 'b']] }],
    }, 'light', 'en');
    const series = option.series as { type?: string; name?: string }[];
    expect(series.filter((entry) => entry.type === 'line')).toHaveLength(0);
  });

  it('labels generated GPC and rheology curves as proxies', () => {
    const gpc = getGpcChartOption([product], 'light', 'en');
    const rheology = getRheologyChartOption([product], 'light', [190], 'en');
    expect((gpc.title as { subtext?: string }).subtext).toContain('not measured GPC');
    expect((rheology.title as { subtext?: string }).subtext).toContain('not fitted rheometry');
    expect((gpc.series as { smooth?: boolean; areaStyle?: unknown }[])[0]).toMatchObject({ smooth: false });
    expect((gpc.series as { areaStyle?: unknown }[])[0].areaStyle).toBeUndefined();
  });
});
