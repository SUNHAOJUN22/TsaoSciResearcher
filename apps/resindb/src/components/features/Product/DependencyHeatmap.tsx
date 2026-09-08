import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Beaker, Download, Info, Sliders, TrendingDown, TrendingUp } from 'lucide-react';
import { ScientificEChart } from '@/components/charts/ScientificEChart';
import {
  escapeScientificHtml,
  formatScientificNumber,
  SCIENTIFIC_SEQUENTIAL,
  scientificGridColor,
  scientificMutedColor,
  scientificTextColor,
  scientificTooltipItem,
  type ScientificFigureTheme,
} from '@/components/charts/scientificFigurePolicy';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import type { ECharts, EChartsOption } from '@/lib/echarts';
import { formulaEngine } from '@/lib/formulaParser';
import type { FormulaConfig, Product } from '@/types/index';

export interface DependencyHeatmapProps {
  expression: string;
  name: string;
  formulas: FormulaConfig[];
  allProducts: Product[];
}

export interface DependencyFeatureInfo {
  key: string;
  labelZh: string;
  labelEn: string;
  unit: string;
  descriptionZh: string;
  descriptionEn: string;
}

export type DependencyEvidenceType = 'formula-dependency' | 'rule-generated-proxy';
export type DependencyAvailability = 'available' | 'missing-input' | 'unavailable-output';

export interface DependencyPropertyInfo {
  key: string;
  labelZh: string;
  labelEn: string;
  unit: string;
  descriptionZh: string;
  descriptionEn: string;
  evidenceType: DependencyEvidenceType;
}

export interface DependencySensitivityCell {
  rowKey: string;
  colKey: string;
  score: number | null;
  availability: DependencyAvailability;
  evidenceType: DependencyEvidenceType;
  reason: string | null;
}

export interface DependencyCurvePoint {
  percent: string;
  percentNum: number;
  value: number;
}

interface DependencyHeatmapPoint {
  value: [number, number, number];
  rowKey: string;
  colKey: string;
  inputLabel: string;
  outputLabel: string;
  score: number | null;
  availability: DependencyAvailability;
  evidenceType: DependencyEvidenceType;
  reason: string | null;
  itemStyle?: Record<string, unknown>;
  label?: Record<string, unknown>;
}

const STANDARD_FEATURES: readonly DependencyFeatureInfo[] = [
  {
    key: 'density',
    labelZh: '材料密度',
    labelEn: 'Material Density',
    unit: 'g/cm³',
    descriptionZh: '参考产品中用于局部扰动的材料密度输入。',
    descriptionEn: 'Material-density input perturbed locally around the reference product.',
  },
  {
    key: 'mfr',
    labelZh: '熔体流动速率 MFR',
    labelEn: 'Melt Flow Rate MFR',
    unit: 'g/10 min',
    descriptionZh: '参考产品中用于局部扰动的熔体流动速率输入。',
    descriptionEn: 'Melt-flow-rate input perturbed locally around the reference product.',
  },
  {
    key: 'tensileYield',
    labelZh: '拉伸屈服强度',
    labelEn: 'Tensile Yield Strength',
    unit: 'MPa',
    descriptionZh: '参考产品中用于局部扰动的拉伸屈服输入。',
    descriptionEn: 'Tensile-yield input perturbed locally around the reference product.',
  },
  {
    key: 'flexuralModulus',
    labelZh: '弯曲模量',
    labelEn: 'Flexural Modulus',
    unit: 'MPa',
    descriptionZh: '参考产品中用于局部扰动的弯曲模量输入。',
    descriptionEn: 'Flexural-modulus input perturbed locally around the reference product.',
  },
  {
    key: 'izodImpact',
    labelZh: '悬臂梁冲击强度',
    labelEn: 'Izod Impact Strength',
    unit: 'kJ/m²',
    descriptionZh: '参考产品中用于局部扰动的冲击强度输入。',
    descriptionEn: 'Impact-strength input perturbed locally around the reference product.',
  },
] as const;

function localize(language: 'zh' | 'en', zh: string, en: string): string {
  return language === 'zh' ? zh : en;
}

function parseFinite(value: unknown): number | null {
  const parsed = typeof value === 'number' ? value : Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : null;
}

function directValue(product: Product, key: string): number | null {
  return parseFinite(product.properties?.[key]?.value);
}

function aliasedValue(product: Product, keys: readonly string[]): number | null {
  for (const key of keys) {
    const value = parseFinite(product.properties?.[key]?.value);
    if (value !== null) return value;
  }
  return null;
}

/** Preserves the existing formula graph and rule-generated screening outputs. */
export function evaluateDependencyOutput(
  colKey: string,
  product: Product,
  expression: string,
  formulas: FormulaConfig[],
): number | null {
  const density = Math.max(0, aliasedValue(product, ['密度', 'density', 'Density']) ?? 0.95);
  const mfr = aliasedValue(product, ['熔体质量流动速率', 'mfr', 'MFR']) ?? 2;
  const tensile = aliasedValue(product, [
    '拉伸屈服应力', '拉伸断裂应力', 'tensileYield', 'tensile', 'Tensile Strength',
  ]) ?? 25;
  const flexural = aliasedValue(product, [
    '弯曲模量', 'flexuralModulus', '弯曲弹性模量', 'Flexural Modulus',
  ]) ?? 1200;
  const impact = aliasedValue(product, [
    '简支梁缺口冲击强度', '悬臂梁缺口冲击强度', 'izodImpact', '冲击强度', 'Izod Impact',
  ]) ?? 8;

  switch (colKey) {
    case 'formula': {
      if (!expression.trim()) return null;
      try {
        const temporaryFormula: FormulaConfig = {
          id: 'temp_hm_id',
          name: 'HeatmapTemp',
          expression,
          unit: '',
        };
        const graph = formulaEngine.compileGraph([
          ...formulas.filter((formula) => formula.id !== temporaryFormula.id),
          temporaryFormula,
        ]);
        const value = graph(product)[temporaryFormula.id];
        return Number.isFinite(value) ? value : null;
      } catch {
        return null;
      }
    }
    case 'viscosity':
      return mfr > 0 ? 3500 / mfr : null;
    case 'tensile':
      return tensile * Math.pow(density / 0.95, 1.8);
    case 'stiffness':
      return flexural * Math.pow(density / 0.95, 2.5);
    case 'toughness':
      return impact * (flexural > 0 ? Math.sqrt(1200 / flexural) : 1);
    default:
      return null;
  }
}

export function buildDependencyFeatures(
  expression: string,
  referenceProduct: Product | null,
): DependencyFeatureInfo[] {
  const features = STANDARD_FEATURES.map((feature) => ({ ...feature }));
  const matches = expression.match(/props\['([^']+)'\]/g) ?? [];
  const variables = new Set(matches.map((match) => match.replace(/^props\['/, '').replace(/'\]$/, '')));
  for (const variable of variables) {
    if (features.some((feature) => feature.key === variable)) continue;
    features.push({
      key: variable,
      labelZh: `${variable}（公式变量）`,
      labelEn: `${variable} (formula variable)`,
      unit: referenceProduct?.properties?.[variable]?.unit ?? '',
      descriptionZh: `当前公式直接引用的输入变量“${variable}”。`,
      descriptionEn: `Input variable “${variable}” referenced directly by the active formula.`,
    });
  }
  return features;
}

export function buildDependencyProperties(
  referenceProduct: Product | null,
  language: 'zh' | 'en',
): DependencyPropertyInfo[] {
  return [
    {
      key: 'formula',
      labelZh: '当前公式计算值',
      labelEn: 'Active formula output',
      unit: referenceProduct ? localize(language, '自定义', 'formula unit') : '',
      descriptionZh: '由当前公式图实时计算，属于公式依赖证据。',
      descriptionEn: 'Computed by the active formula graph; this is formula-dependency evidence.',
      evidenceType: 'formula-dependency',
    },
    {
      key: 'viscosity',
      labelZh: 'MFR 派生粘度代理',
      labelEn: 'MFR-derived viscosity proxy',
      unit: 'Pa·s',
      descriptionZh: '按既有 MFR 互反规则生成的筛选代理，并非实测流变数据。',
      descriptionEn: 'Screening proxy generated by the reciprocal MFR rule; not measured rheology.',
      evidenceType: 'rule-generated-proxy',
    },
    {
      key: 'tensile',
      labelZh: '拉伸规则代理',
      labelEn: 'Tensile rule proxy',
      unit: 'MPa',
      descriptionZh: '按既有拉伸与密度规则生成的筛选代理。',
      descriptionEn: 'Screening proxy generated by the tensile-density rule.',
      evidenceType: 'rule-generated-proxy',
    },
    {
      key: 'stiffness',
      labelZh: '刚度规则代理',
      labelEn: 'Stiffness rule proxy',
      unit: 'MPa',
      descriptionZh: '按既有弯曲模量与密度规则生成的筛选代理。',
      descriptionEn: 'Screening proxy generated by the flexural-density rule.',
      evidenceType: 'rule-generated-proxy',
    },
    {
      key: 'toughness',
      labelZh: '韧性规则代理',
      labelEn: 'Toughness rule proxy',
      unit: 'kJ/m²',
      descriptionZh: '按既有冲击与模量规则生成的筛选代理。',
      descriptionEn: 'Screening proxy generated by the impact-modulus rule.',
      evidenceType: 'rule-generated-proxy',
    },
  ];
}

function perturb(product: Product, key: string, value: number): Product {
  return {
    ...product,
    properties: {
      ...product.properties,
      [key]: { ...product.properties[key], value },
    },
  };
}

export function computeDependencySensitivityCells(
  referenceProduct: Product | null,
  rows: readonly DependencyFeatureInfo[],
  columns: readonly DependencyPropertyInfo[],
  expression: string,
  formulas: FormulaConfig[],
  perturbationPct: number,
): DependencySensitivityCell[] {
  if (!referenceProduct) return [];
  const cells: DependencySensitivityCell[] = [];
  for (const row of rows) {
    const baseInput = directValue(referenceProduct, row.key);
    for (const column of columns) {
      if (baseInput === null || baseInput === 0) {
        cells.push({
          rowKey: row.key,
          colKey: column.key,
          score: null,
          availability: 'missing-input',
          evidenceType: column.evidenceType,
          reason: 'The reference product has no finite non-zero value for this input key.',
        });
        continue;
      }
      const baseOutput = evaluateDependencyOutput(column.key, referenceProduct, expression, formulas);
      if (baseOutput === null || baseOutput === 0) {
        cells.push({
          rowKey: row.key,
          colKey: column.key,
          score: null,
          availability: 'unavailable-output',
          evidenceType: column.evidenceType,
          reason: 'The formula or rule did not produce a finite non-zero baseline output.',
        });
        continue;
      }
      const plusInput = baseInput * (1 + perturbationPct / 100);
      const minusInput = baseInput * (1 - perturbationPct / 100);
      const plusOutput = evaluateDependencyOutput(
        column.key, perturb(referenceProduct, row.key, plusInput), expression, formulas,
      );
      const minusOutput = evaluateDependencyOutput(
        column.key, perturb(referenceProduct, row.key, minusInput), expression, formulas,
      );
      const deltaInput = plusInput - minusInput;
      if (plusOutput === null || minusOutput === null || deltaInput === 0) {
        cells.push({
          rowKey: row.key,
          colKey: column.key,
          score: null,
          availability: 'unavailable-output',
          evidenceType: column.evidenceType,
          reason: 'The perturbed formula or rule output is unavailable.',
        });
        continue;
      }
      const sensitivity = ((plusOutput - minusOutput) / baseOutput) / (deltaInput / baseInput);
      cells.push(Number.isFinite(sensitivity)
        ? {
            rowKey: row.key,
            colKey: column.key,
            score: Math.round(sensitivity * 100) / 100,
            availability: 'available',
            evidenceType: column.evidenceType,
            reason: null,
          }
        : {
            rowKey: row.key,
            colKey: column.key,
            score: null,
            availability: 'unavailable-output',
            evidenceType: column.evidenceType,
            reason: 'The dimensionless sensitivity is not finite.',
          });
    }
  }
  return cells;
}

export function buildDependencyCurve(
  referenceProduct: Product | null,
  rowKey: string,
  colKey: string,
  expression: string,
  formulas: FormulaConfig[],
): DependencyCurvePoint[] {
  if (!referenceProduct) return [];
  const baseInput = directValue(referenceProduct, rowKey);
  if (baseInput === null || baseInput === 0) return [];
  const points: DependencyCurvePoint[] = [];
  for (const percent of [-40, -30, -20, -10, 0, 10, 20, 30, 40]) {
    const value = evaluateDependencyOutput(
      colKey,
      perturb(referenceProduct, rowKey, baseInput * (1 + percent / 100)),
      expression,
      formulas,
    );
    if (value !== null) {
      points.push({
        percent: `${percent > 0 ? '+' : ''}${percent}%`,
        percentNum: percent,
        value: Math.round(value * 1000) / 1000,
      });
    }
  }
  return points;
}

function evidenceLabel(type: DependencyEvidenceType, language: 'zh' | 'en'): string {
  return type === 'formula-dependency'
    ? localize(language, '公式依赖', 'formula dependency')
    : localize(language, '规则生成代理', 'rule-generated proxy');
}

function availabilityLabel(type: DependencyAvailability, language: 'zh' | 'en'): string {
  if (type === 'missing-input') return localize(language, '输入缺失', 'missing input');
  if (type === 'unavailable-output') return localize(language, '输出不可用', 'unavailable output');
  return localize(language, '可用', 'available');
}

export function getDependencyHeatmapOption(
  rows: readonly DependencyFeatureInfo[],
  columns: readonly DependencyPropertyInfo[],
  cells: readonly DependencySensitivityCell[],
  selected: { rowKey: string; colKey: string } | null,
  theme: ScientificFigureTheme,
  language: 'zh' | 'en',
): EChartsOption {
  const maxMagnitude = Math.max(1, ...cells.map((cell) => Math.abs(cell.score ?? 0)));
  const data: DependencyHeatmapPoint[] = cells.map((cell) => {
    const rowIndex = rows.findIndex((row) => row.key === cell.rowKey);
    const colIndex = columns.findIndex((column) => column.key === cell.colKey);
    const isSelected = selected?.rowKey === cell.rowKey && selected.colKey === cell.colKey;
    return {
      value: [colIndex, rowIndex, Math.abs(cell.score ?? 0)],
      rowKey: cell.rowKey,
      colKey: cell.colKey,
      inputLabel: rows[rowIndex] ? localize(language, rows[rowIndex].labelZh, rows[rowIndex].labelEn) : cell.rowKey,
      outputLabel: columns[colIndex] ? localize(language, columns[colIndex].labelZh, columns[colIndex].labelEn) : cell.colKey,
      score: cell.score,
      availability: cell.availability,
      evidenceType: cell.evidenceType,
      reason: cell.reason,
      itemStyle: cell.score === null
        ? {
            color: theme === 'dark' ? '#1e293b' : '#e2e8f0',
            borderColor: theme === 'dark' ? '#64748b' : '#94a3b8',
            borderWidth: isSelected ? 3 : 1,
            borderType: 'dashed',
          }
        : {
            borderColor: isSelected ? '#f59e0b' : scientificGridColor(theme),
            borderWidth: isSelected ? 3 : 1,
          },
      label: {
        show: true,
        color: cell.score === null ? scientificMutedColor(theme) : scientificTextColor(theme),
        fontSize: 10,
        fontWeight: 700,
        formatter: () => cell.score === null
          ? '—'
          : `${cell.score > 0 ? '+' : ''}${cell.score.toFixed(2)}`,
      },
    };
  });

  return {
    grid: { left: 145, right: 48, top: 40, bottom: 95 },
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const item = scientificTooltipItem(params);
        const point = item?.data as DependencyHeatmapPoint | undefined;
        if (!point) return '';
        const score = point.score === null
          ? localize(language, '不可用（不是 0）', 'unavailable (not zero)')
          : `${point.score > 0 ? '+' : ''}${point.score.toFixed(2)}`;
        return [
          `<strong>${escapeScientificHtml(point.inputLabel)} → ${escapeScientificHtml(point.outputLabel)}</strong>`,
          `${escapeScientificHtml(localize(language, '无量纲局部灵敏度', 'Dimensionless local sensitivity'))}: ${escapeScientificHtml(score)}`,
          `${escapeScientificHtml(localize(language, '证据类型', 'Evidence type'))}: ${escapeScientificHtml(evidenceLabel(point.evidenceType, language))}`,
          `${escapeScientificHtml(localize(language, '校验状态', 'Validation state'))}: ${escapeScientificHtml(availabilityLabel(point.availability, language))}`,
          point.reason ? escapeScientificHtml(point.reason) : '',
          `<em>${escapeScientificHtml(localize(language, '局部单变量扰动描述，不是统计相关或因果归因。', 'Local one-variable perturbation description; not statistical association or causal attribution.'))}</em>`,
        ].filter(Boolean).join('<br/>');
      },
    },
    xAxis: {
      type: 'category',
      data: columns.map((column) => localize(language, column.labelZh, column.labelEn)),
      axisLabel: { interval: 0, rotate: 24, width: 110, overflow: 'truncate' },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => localize(language, row.labelZh, row.labelEn)),
      axisLabel: { interval: 0, width: 130, overflow: 'truncate' },
      splitArea: { show: true },
    },
    visualMap: {
      type: 'continuous',
      min: 0,
      max: maxMagnitude,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 8,
      text: [
        localize(language, '灵敏度幅值高', 'higher magnitude'),
        localize(language, '灵敏度幅值低', 'lower magnitude'),
      ],
      inRange: { color: [...SCIENTIFIC_SEQUENTIAL] },
      textStyle: { color: scientificMutedColor(theme), fontSize: 10 },
    },
    series: [{
      name: localize(language, '局部扰动灵敏度', 'Local perturbation sensitivity'),
      type: 'heatmap',
      data,
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(15,23,42,.22)' } },
    }],
  };
}

export function getDependencyCurveOption(
  curve: readonly DependencyCurvePoint[],
  output: DependencyPropertyInfo | undefined,
  theme: ScientificFigureTheme,
  language: 'zh' | 'en',
): EChartsOption {
  return {
    grid: { left: 58, right: 24, top: 36, bottom: 54 },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = scientificTooltipItem(params);
        const value = item?.value as [number, number] | undefined;
        if (!value) return '';
        return [
          `${escapeScientificHtml(localize(language, '输入扰动', 'Input perturbation'))}: ${formatScientificNumber(value[0])}%`,
          `${escapeScientificHtml(output ? localize(language, output.labelZh, output.labelEn) : 'Output')}: ${formatScientificNumber(value[1])} ${escapeScientificHtml(output?.unit ?? '')}`,
          `${escapeScientificHtml(localize(language, '证据类型', 'Evidence type'))}: ${escapeScientificHtml(output ? evidenceLabel(output.evidenceType, language) : '')}`,
        ].join('<br/>');
      },
    },
    xAxis: {
      type: 'value',
      name: localize(language, '输入扰动 (%)', 'Input perturbation (%)'),
      min: -40,
      max: 40,
    },
    yAxis: {
      type: 'value',
      name: output ? `${localize(language, output.labelZh, output.labelEn)} (${output.unit})` : '',
      scale: true,
    },
    series: [{
      name: localize(language, '规则/公式响应', 'Formula/rule response'),
      type: 'line',
      smooth: false,
      showSymbol: true,
      symbolSize: 6,
      data: curve.map((point) => [point.percentNum, point.value]),
      markLine: {
        silent: true,
        symbol: ['none', 'none'],
        data: [{ xAxis: 0 }],
        lineStyle: { type: 'dashed', width: 1, color: theme === 'dark' ? '#fbbf24' : '#d97706' },
      },
    }],
  };
}

function exportPng(chart: ECharts | null, name: string, theme: ScientificFigureTheme): void {
  if (!chart || chart.isDisposed()) return;
  const anchor = document.createElement('a');
  anchor.href = chart.getDataURL({
    type: 'png',
    pixelRatio: 3,
    backgroundColor: theme === 'dark' ? '#0f172a' : '#ffffff',
  });
  anchor.download = `${name}.png`;
  anchor.click();
}

function markChartReady(chart: ECharts, name: string): void {
  const dom = chart.getDom();
  dom.dataset.phase2lChart = name;
  dom.dataset.phase2lReadyCount = String(Number(dom.dataset.phase2lReadyCount ?? '0') + 1);
}

export const DependencyHeatmap: React.FC<DependencyHeatmapProps> = React.memo(({
  expression,
  name,
  formulas,
  allProducts,
}) => {
  const { language } = useLanguage();
  const { theme } = useTheme();
  const [selectedProductIndex, setSelectedProductIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [perturbationPct, setPerturbationPct] = useState(15);
  const [selectedCell, setSelectedCell] = useState<{ rowKey: string; colKey: string } | null>(null);
  const chartRef = useRef<ECharts | null>(null);

  const referenceProduct = allProducts[selectedProductIndex] ?? allProducts[0] ?? null;
  const filteredProducts = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return allProducts
      .filter((product) => !query
        || product.gradeName.toLowerCase().includes(query)
        || product.manufacturer.toLowerCase().includes(query))
      .slice(0, 20);
  }, [allProducts, searchQuery]);
  const rows = useMemo(
    () => buildDependencyFeatures(expression, referenceProduct),
    [expression, referenceProduct],
  );
  const columns = useMemo(
    () => buildDependencyProperties(referenceProduct, language),
    [language, referenceProduct],
  );
  const cells = useMemo(
    () => computeDependencySensitivityCells(
      referenceProduct, rows, columns, expression, formulas, perturbationPct,
    ),
    [columns, expression, formulas, perturbationPct, referenceProduct, rows],
  );
  const selectedModel = selectedCell
    ? cells.find((cell) => cell.rowKey === selectedCell.rowKey && cell.colKey === selectedCell.colKey) ?? null
    : null;
  const selectedRow = selectedCell ? rows.find((row) => row.key === selectedCell.rowKey) : undefined;
  const selectedColumn = selectedCell ? columns.find((column) => column.key === selectedCell.colKey) : undefined;
  const curve = useMemo(
    () => selectedCell
      ? buildDependencyCurve(
          referenceProduct, selectedCell.rowKey, selectedCell.colKey, expression, formulas,
        )
      : [],
    [expression, formulas, referenceProduct, selectedCell],
  );
  const heatmapOption = useMemo(
    () => getDependencyHeatmapOption(rows, columns, cells, selectedCell, theme, language),
    [cells, columns, language, rows, selectedCell, theme],
  );
  const curveOption = useMemo(
    () => getDependencyCurveOption(curve, selectedColumn, theme, language),
    [curve, language, selectedColumn, theme],
  );
  const t = useCallback((zh: string, en: string) => localize(language, zh, en), [language]);

  const handleHeatmapReady = useCallback((chart: ECharts) => {
    chartRef.current = chart;
    markChartReady(chart, 'dependency-heatmap');
    chart.off('click');
    chart.on('click', (params: unknown) => {
      const point = scientificTooltipItem(params)?.data as DependencyHeatmapPoint | undefined;
      if (point?.rowKey && point.colKey) {
        setSelectedCell({ rowKey: point.rowKey, colKey: point.colKey });
      }
    });
  }, []);

  return (
    <section
      data-testid="dependency-heatmap-migrated"
      data-scientific-boundary="local-perturbation-not-causality"
      data-legacy-wrapper="false"
      className="flex flex-1 flex-col gap-4 overflow-y-auto p-1"
    >
      <div className="rounded-2xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-xs leading-5 text-indigo-900 dark:border-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-100">
        <strong>{t('科学边界：', 'Scientific boundary: ')}</strong>
        {t(
          '本视图是参考产品附近的单变量局部扰动灵敏度。公式列表示公式依赖；其余列是规则生成代理。这里没有计算统计相关性，也不构成因果归因。缺失证据显示为“—”，不会伪装成零。',
          'This view is a one-variable local perturbation sensitivity around a reference product. The formula column is formula-dependency evidence; the other columns are rule-generated proxies. Statistical association is not computed here, and no value is causal attribution. Missing evidence is shown as “—”, never as zero.',
        )}
      </div>

      <div className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/40 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <label className="space-y-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
          <span className="flex items-center gap-1.5"><Beaker size={13} />{t('参考产品', 'Reference product')}</span>
          <input
            aria-label={t('筛选参考产品', 'Filter reference products')}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder={t('搜索牌号或厂家', 'Search grade or manufacturer')}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900"
          />
          <select
            data-testid="dependency-reference-product"
            value={referenceProduct?.id ?? ''}
            onChange={(event) => {
              const index = allProducts.findIndex((product) => product.id === event.target.value);
              setSelectedProductIndex(Math.max(0, index));
              setSelectedCell(null);
            }}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            {filteredProducts.map((product) => (
              <option key={product.id} value={product.id}>{product.gradeName} — {product.manufacturer}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
          <span className="flex items-center gap-1.5"><Sliders size={13} />{t('局部扰动幅度', 'Local perturbation amplitude')}: ±{perturbationPct}%</span>
          <input
            data-testid="dependency-perturbation-slider"
            type="range"
            min={5}
            max={30}
            step={5}
            value={perturbationPct}
            onChange={(event) => setPerturbationPct(Number(event.target.value))}
            className="w-full accent-indigo-600"
          />
          <select
            data-testid="dependency-keyboard-cell-selector"
            aria-label={t('键盘选择灵敏度单元格', 'Select a sensitivity cell with the keyboard')}
            value={selectedCell ? `${selectedCell.rowKey}::${selectedCell.colKey}` : ''}
            onChange={(event) => {
              const [rowKey, colKey] = event.target.value.split('::');
              setSelectedCell(rowKey && colKey ? { rowKey, colKey } : null);
            }}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">{t('选择矩阵关系…', 'Select a matrix relationship…')}</option>
            {cells.map((cell) => {
              const row = rows.find((candidate) => candidate.key === cell.rowKey);
              const column = columns.find((candidate) => candidate.key === cell.colKey);
              return (
                <option key={`${cell.rowKey}-${cell.colKey}`} value={`${cell.rowKey}::${cell.colKey}`}>
                  {row ? t(row.labelZh, row.labelEn) : cell.rowKey} → {column ? t(column.labelZh, column.labelEn) : cell.colKey}: {cell.score === null ? t('不可用', 'unavailable') : `${cell.score > 0 ? '+' : ''}${cell.score.toFixed(2)}`}
                </option>
              );
            })}
          </select>
        </label>

        <button
          type="button"
          data-testid="dependency-export-png"
          onClick={() => exportPng(chartRef.current, 'dependency-local-sensitivity', theme)}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 focus:outline-none focus-visible:ring-2"
        >
          <Download size={14} />{t('导出 PNG', 'Export PNG')}
        </button>
      </div>

      <div className="grid min-h-[680px] gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,.65fr)]">
        <div data-testid="dependency-heatmap-scientific-chart" className="min-h-[520px]">
          <ScientificEChart
            option={heatmapOption}
            theme={theme}
            ariaLabel={t(`${name} 局部扰动灵敏度矩阵`, `${name} local perturbation sensitivity matrix`)}
            description={t(
              '颜色仅编码可用灵敏度的绝对幅值，正负号由单元格标签给出；破折号表示缺失或不可用证据。',
              'Color encodes only the absolute magnitude of available sensitivity. Cell labels retain the sign; an em dash denotes missing or unavailable evidence.',
            )}
            exportName="dependency-local-sensitivity"
            dataCount={cells.length}
            empty={!referenceProduct || cells.length === 0}
            height="100%"
            onChartReady={handleHeatmapReady}
          />
        </div>

        <div className="flex min-h-[520px] flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/20">
          {selectedCell && selectedRow && selectedColumn ? (
            <>
              <div data-testid="dependency-selection-summary" className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
                <div className="text-[10px] font-black uppercase tracking-wider text-slate-400">{t('已选关系', 'Selected relationship')}</div>
                <div className="mt-1 text-sm font-black text-slate-900 dark:text-white">
                  {t(selectedRow.labelZh, selectedRow.labelEn)} → {t(selectedColumn.labelZh, selectedColumn.labelEn)}
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <div className="text-slate-400">{t('灵敏度', 'Sensitivity')}</div>
                    <div className="font-mono text-lg font-black">
                      {selectedModel?.score === null || selectedModel === null
                        ? '—'
                        : `${selectedModel.score > 0 ? '+' : ''}${selectedModel.score.toFixed(2)}`}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400">{t('证据类型', 'Evidence type')}</div>
                    <div className="font-bold">{evidenceLabel(selectedColumn.evidenceType, language)}</div>
                  </div>
                </div>
                {selectedModel?.score !== null && selectedModel ? (
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                    {selectedModel.score > 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                    {selectedModel.score > 0
                      ? t('局部正向响应', 'positive local response')
                      : selectedModel.score < 0
                        ? t('局部负向响应', 'negative local response')
                        : t('局部响应接近零', 'local response near zero')}
                  </div>
                ) : (
                  <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-slate-100 p-2 text-xs dark:bg-slate-900">
                    <Info size={13} className="mt-0.5 shrink-0" />
                    {selectedModel?.reason ?? t('该关系没有可验证的有限数值。', 'This relationship has no verifiable finite value.')}
                  </div>
                )}
              </div>

              <div data-testid="dependency-curve-scientific-chart" className="min-h-[330px] flex-1">
                <ScientificEChart
                  option={curveOption}
                  theme={theme}
                  ariaLabel={t('所选局部扰动响应曲线', 'Selected local perturbation response curve')}
                  description={t(
                    '离散点是既有公式或规则在固定扰动步长上的计算结果，直线仅连接这些点，不进行装饰性平滑。',
                    'Points are outputs of the existing formula or rule at fixed perturbation steps. Straight segments only connect those points; no decorative smoothing is applied.',
                  )}
                  exportName="dependency-local-response"
                  dataCount={curve.length}
                  empty={curve.length === 0}
                  height="100%"
                  onChartReady={(chart) => markChartReady(chart, 'dependency-curve')}
                />
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              {t('点击热图单元格，或使用键盘关系选择器，查看公式/规则响应曲线。', 'Click a heatmap cell, or use the keyboard relationship selector, to inspect the formula/rule response curve.')}
            </div>
          )}
        </div>
      </div>
    </section>
  );
});
