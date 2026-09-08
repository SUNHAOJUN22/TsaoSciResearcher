import { describe, expect, it } from 'vitest';
import {
  buildDependencyFeatures,
  buildDependencyProperties,
  computeDependencySensitivityCells,
  getDependencyHeatmapOption,
} from '@/components/features/Product/DependencyHeatmap';
import {
  getRheologyGraphOption,
  sanitizePositiveRheologyPoints,
  simulateRheologyProxyPoints,
} from '@/components/charts/RheologyGraph';
import type { Product } from '@/types/index';

const product: Product = {
  id: 'phase2l-science',
  gradeName: 'PP-SCIENCE',
  manufacturerId: 'maker',
  manufacturer: 'Scientific Test',
  categoryIds: ['聚丙烯'],
  properties: {
    density: { value: 0.95 },
    mfr: { value: 5 },
    tensileYield: { value: 25 },
    flexuralModulus: { value: 1200 },
    izodImpact: { value: 8 },
  },
  createdAt: '2026-01-01',
  updatedAt: '2026-01-01',
};

describe('Phase 2L scientific semantics', () => {
  it('does not label local perturbation sensitivity as statistical association or causality', () => {
    const rows = buildDependencyFeatures("props['mfr'] * 2", product);
    const columns = buildDependencyProperties(product, 'en');
    const cells = computeDependencySensitivityCells(
      product,
      rows,
      columns,
      "props['mfr'] * 2",
      [],
      15,
    );
    const option = getDependencyHeatmapOption(rows, columns, cells, null, 'light', 'en');
    const formatter = (option.tooltip as { formatter: (params: unknown) => string }).formatter;
    const formulaCell = (option.series as { data: unknown[] }[])[0]?.data[0];
    const tooltip = formatter({ data: formulaCell });
    expect(tooltip).toContain('formula dependency');
    expect(tooltip).toContain('not statistical association or causal attribution');
  });

  it('does not expose invalid rheology values to logarithmic axes or the fitted series', () => {
    const valid = sanitizePositiveRheologyPoints([
      ...simulateRheologyProxyPoints(4, 0),
      [0, 1],
      [1, -1],
      [2, Number.NaN],
      [3, Number.POSITIVE_INFINITY],
    ]);
    expect(valid.every(([rate, viscosity]) => (
      Number.isFinite(rate)
      && Number.isFinite(viscosity)
      && rate > 0
      && viscosity > 0
    ))).toBe(true);

    const option = getRheologyGraphOption(valid, [], 'light', 'PP-SCIENCE', 190, 'en');
    const plotted = (option.series as { data: { value: [number, number] }[] }[])[0]?.data ?? [];
    expect(plotted.every(({ value: [rate, viscosity] }) => rate > 0 && viscosity > 0)).toBe(true);
    expect((option.title as { subtext?: string }).subtext).toContain('not measured rheology');
  });
});
