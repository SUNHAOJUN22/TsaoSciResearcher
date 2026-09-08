import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  buildDependencyCurve,
  buildDependencyFeatures,
  buildDependencyProperties,
  computeDependencySensitivityCells,
  getDependencyCurveOption,
  getDependencyHeatmapOption,
} from '@/components/features/Product/DependencyHeatmap';
import {
  getRheologyGraphOption,
  sanitizePositiveRheologyPoints,
  simulateRheologyProxyPoints,
} from '@/components/charts/RheologyGraph';
import { applyScientificFigurePolicy } from '@/components/charts/scientificFigurePolicy';
import type { FormulaConfig, Product } from '@/types/index';

const product: Product = {
  id: 'phase2l-product',
  gradeName: 'PP-PHASE2L',
  manufacturerId: 'phase2l-maker',
  manufacturer: 'Phase 2L Lab',
  categoryIds: ['聚丙烯'],
  properties: {
    density: { value: 0.95, unit: 'g/cm³' },
    mfr: { value: 4, unit: 'g/10 min' },
    tensileYield: { value: 25, unit: 'MPa' },
    flexuralModulus: { value: 1200, unit: 'MPa' },
    izodImpact: { value: 8, unit: 'kJ/m²' },
  },
  createdAt: '2026-01-01T00:00:00.000Z',
  updatedAt: '2026-01-01T00:00:00.000Z',
};

const formulas: FormulaConfig[] = [];
const expression = "props['mfr'] * 2";

describe('Phase 2L DependencyHeatmap migration', () => {
  it('preserves finite perturbation values and signs for formula and rule outputs', () => {
    const rows = buildDependencyFeatures(expression, product);
    const columns = buildDependencyProperties(product, 'en');
    const cells = computeDependencySensitivityCells(
      product,
      rows,
      columns,
      expression,
      formulas,
      15,
    );
    expect(cells.find((cell) => cell.rowKey === 'mfr' && cell.colKey === 'formula'))
      .toMatchObject({ score: 1, availability: 'available', evidenceType: 'formula-dependency' });
    expect(cells.find((cell) => cell.rowKey === 'mfr' && cell.colKey === 'viscosity'))
      .toMatchObject({ score: -1.02, availability: 'available', evidenceType: 'rule-generated-proxy' });
    expect(cells.find((cell) => cell.rowKey === 'mfr' && cell.colKey === 'tensile'))
      .toMatchObject({ score: 0, availability: 'available' });
  });

  it('represents missing evidence as null rather than a numeric zero', () => {
    const missingProduct: Product = {
      ...product,
      properties: { mfr: product.properties.mfr },
    };
    const rows = buildDependencyFeatures(expression, missingProduct);
    const columns = buildDependencyProperties(missingProduct, 'en');
    const cells = computeDependencySensitivityCells(
      missingProduct,
      rows,
      columns,
      expression,
      formulas,
      15,
    );
    const missingDensity = cells.find((cell) => cell.rowKey === 'density' && cell.colKey === 'formula');
    expect(missingDensity).toMatchObject({
      score: null,
      availability: 'missing-input',
    });
    expect(missingDensity?.score).not.toBe(0);
  });

  it('uses a continuous magnitude scale, explicit unavailable labels and no decorative smoothing', () => {
    const rows = buildDependencyFeatures(expression, product);
    const columns = buildDependencyProperties(product, 'en');
    const cells = computeDependencySensitivityCells(product, rows, columns, expression, formulas, 15);
    const option = getDependencyHeatmapOption(rows, columns, cells, null, 'dark', 'en') as Record<string, unknown>;
    expect(option.visualMap).toMatchObject({ type: 'continuous', min: 0 });
    const series = (option.series as { data: { score: number | null; label?: { formatter?: () => string } }[] }[])[0];
    const unavailable = series.data.find((entry) => entry.score === null);
    if (unavailable) expect(unavailable.label?.formatter?.()).toBe('—');

    const curve = buildDependencyCurve(product, 'mfr', 'formula', expression, formulas);
    const curveOption = getDependencyCurveOption(curve, columns[0], 'light', 'en');
    expect((curveOption.series as { smooth?: boolean }[])[0]).toMatchObject({ smooth: false });
  });

  it('inherits accessible three-times PNG export and theme policy from ScientificEChart', () => {
    const rows = buildDependencyFeatures(expression, product);
    const columns = buildDependencyProperties(product, 'en');
    const cells = computeDependencySensitivityCells(product, rows, columns, expression, formulas, 15);
    const governed = applyScientificFigurePolicy(
      getDependencyHeatmapOption(rows, columns, cells, null, 'dark', 'en'),
      {
        theme: 'dark',
        title: 'Dependency heatmap',
        description: 'Formula dependency and rule proxy evidence',
        exportName: 'dependency-local-sensitivity',
        dataCount: cells.length,
      },
    ) as Record<string, unknown>;
    expect(governed.aria).toMatchObject({ enabled: true });
    expect(governed.toolbox).toMatchObject({
      feature: {
        saveAsImage: {
          name: 'dependency-local-sensitivity',
          pixelRatio: 3,
          backgroundColor: '#0f172a',
        },
      },
    });
  });
});

describe('Phase 2L RheologyGraph migration', () => {
  it('preserves the deterministic MFR proxy rule exactly across repeated calls', () => {
    const first = simulateRheologyProxyPoints(5, 10);
    const second = simulateRheologyProxyPoints(5, 10);
    expect(first).toEqual(second);
    expect(first).toHaveLength(17);
    expect(first[0]?.[0]).toBe(0.01);
    expect(first.every(([rate, viscosity]) => rate > 0 && viscosity > 0)).toBe(true);
  });

  it('removes non-positive, NaN and infinite values before log axes and fitting', () => {
    const sanitized = sanitizePositiveRheologyPoints([
      [0.1, 1000],
      [0, 20],
      [-1, 20],
      [1, 0],
      [2, Number.NaN],
      [Number.POSITIVE_INFINITY, 3],
    ]);
    expect(sanitized).toEqual([[0.1, 1000]]);
  });

  it('labels proxy observations and fitted model separately with units and straight segments', () => {
    const proxy = simulateRheologyProxyPoints(5, 0);
    const fitted: [number, number][] = [[0.01, 6000], [1, 3000], [100, 400]];
    const option = getRheologyGraphOption(proxy, fitted, 'light', 'PP-PHASE2L', 190, 'en');
    expect(option.xAxis).toMatchObject({ type: 'log', name: 'Shear rate (s⁻¹)' });
    expect(option.yAxis).toMatchObject({ type: 'log', name: 'Viscosity (Pa·s)' });
    const series = option.series as { name?: string; type?: string; smooth?: boolean }[];
    expect(series[0]?.name).toContain('Rule-generated MFR proxy');
    expect(series[1]?.name).toContain('Fitted model of proxy points');
    expect(series[1]).toMatchObject({ type: 'line', smooth: false });
    expect((option.title as { subtext?: string }).subtext).toContain('not measured rheology');
  });

  it('inherits dark-theme PNG export and accessibility policy', () => {
    const option = getRheologyGraphOption(
      simulateRheologyProxyPoints(5, 0),
      [],
      'dark',
      'PP-PHASE2L',
      190,
      'en',
    );
    const governed = applyScientificFigurePolicy(option, {
      theme: 'dark',
      title: 'MFR-derived rheology proxy',
      description: 'Rule-generated proxy, not measured rheology',
      exportName: 'mfr-derived-rheology-proxy',
      dataCount: 17,
    }) as Record<string, unknown>;
    expect(governed.aria).toMatchObject({ enabled: true });
    expect(governed.toolbox).toMatchObject({
      feature: { saveAsImage: { pixelRatio: 3, backgroundColor: '#0f172a' } },
    });
  });
});

describe('Phase 2L wrapper removal contract', () => {
  it('removes only the two authorized Legacy implementations', () => {
    const root = process.cwd();
    expect(existsSync(path.join(root, 'src/components/features/Product/DependencyHeatmapLegacy.tsx'))).toBe(false);
    expect(existsSync(path.join(root, 'src/components/charts/RheologyGraphLegacy.tsx'))).toBe(false);
    expect(existsSync(path.join(root, 'src/components/charts/DataVisualizerLegacy.tsx'))).toBe(true);
    expect(existsSync(path.join(root, 'src/components/modals/FormulaEditorModalLegacy.tsx'))).toBe(true);
    expect(existsSync(path.join(root, 'src/components/features/Analytics/PredictiveTrendsLegacy.tsx'))).toBe(true);
    expect(existsSync(path.join(root, 'src/components/features/Analytics/MaterialTrendForecasterLegacy.tsx'))).toBe(true);
    expect(existsSync(path.join(root, 'src/components/features/Analytics/ResinCapacityForecastLegacy.tsx'))).toBe(true);
  });

  it('keeps both migrated targets on the shared chart host without direct ECharts initialization', () => {
    const dependencySource = readFileSync(
      path.join(process.cwd(), 'src/components/features/Product/DependencyHeatmap.tsx'),
      'utf8',
    );
    const rheologySource = readFileSync(
      path.join(process.cwd(), 'src/components/charts/RheologyGraph.tsx'),
      'utf8',
    );
    for (const source of [dependencySource, rheologySource]) {
      expect(source).toContain('ScientificEChart');
      expect(source).toContain('data-scientific-boundary');
      expect(source).not.toMatch(/echarts\.init\s*\(/);
      expect(source).not.toMatch(/Legacy(?:DependencyHeatmap|RheologyGraph)/);
    }
  });
});
