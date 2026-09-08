import type { EChartsOption } from '@/lib/echarts';

export type ScientificFigureTheme = 'light' | 'dark';
export const SCIENTIFIC_FIGURE_POLICY_VERSION = 'scientific-figure-policy-1.1.0';
export const SCIENTIFIC_FONT_FAMILY = [
  'Inter',
  'Noto Sans SC',
  'Noto Sans CJK SC',
  'Microsoft YaHei',
  'PingFang SC',
  'WenQuanYi Micro Hei',
  'Segoe UI',
  'system-ui',
  'sans-serif',
].map((name) => (name.includes(' ') ? `"${name}"` : name)).join(',');
export const SCIENTIFIC_PALETTE = [
  '#0072B2',
  '#D55E00',
  '#009E73',
  '#CC79A7',
  '#E69F00',
  '#56B4E9',
  '#F0E442',
  '#000000',
] as const;
export const SCIENTIFIC_SEQUENTIAL = [
  '#f7fbff',
  '#deebf7',
  '#c6dbef',
  '#9ecae1',
  '#6baed6',
  '#4292c6',
  '#2171b5',
  '#08519c',
  '#08306b',
] as const;

export interface ScientificFigureContext {
  theme: ScientificFigureTheme;
  title?: string;
  description?: string;
  exportName?: string;
  dataCount?: number;
  reducedMotion?: boolean;
}

export function scientificTooltipItem(params: unknown): Record<string, unknown> | null {
  const candidate = Array.isArray(params) ? params[0] : params;
  return candidate && typeof candidate === 'object'
    ? candidate as Record<string, unknown>
    : null;
}

export function escapeScientificHtml(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function formatScientificNumber(value: number, significantDigits = 4): string {
  if (!Number.isFinite(value)) return '—';
  if (value === 0) return '0';
  const magnitude = Math.abs(value);
  if (magnitude >= 1e4 || magnitude < 1e-3) {
    return value.toExponential(Math.max(1, significantDigits - 1));
  }
  return Number(value.toPrecision(significantDigits)).toString();
}

export const scientificTextColor = (theme: ScientificFigureTheme) => (
  theme === 'dark' ? '#e2e8f0' : '#0f172a'
);
export const scientificMutedColor = (theme: ScientificFigureTheme) => (
  theme === 'dark' ? '#94a3b8' : '#475569'
);
export const scientificGridColor = (theme: ScientificFigureTheme) => (
  theme === 'dark' ? 'rgba(148,163,184,.16)' : 'rgba(71,85,105,.14)'
);

function normalizeAxis(axis: unknown, theme: ScientificFigureTheme): unknown {
  if (!axis || typeof axis !== 'object') return axis;
  if (Array.isArray(axis)) return axis.map((entry) => normalizeAxis(entry, theme));
  const source = axis as Record<string, unknown>;
  const result: Record<string, unknown> = {
    ...source,
    nameTextStyle: {
      color: scientificMutedColor(theme),
      fontFamily: SCIENTIFIC_FONT_FAMILY,
      fontSize: 11,
      fontWeight: 600,
      ...(source.nameTextStyle as object | undefined),
    },
    axisLabel: {
      color: scientificMutedColor(theme),
      fontFamily: SCIENTIFIC_FONT_FAMILY,
      fontSize: 10,
      hideOverlap: true,
      ...(source.axisLabel as object | undefined),
    },
    axisLine: {
      show: true,
      lineStyle: { color: scientificGridColor(theme) },
      ...(source.axisLine as object | undefined),
    },
    axisTick: {
      lineStyle: { color: scientificGridColor(theme) },
      ...(source.axisTick as object | undefined),
    },
    splitLine: {
      show: true,
      lineStyle: { color: scientificGridColor(theme), type: 'dashed', width: 1 },
      ...(source.splitLine as object | undefined),
    },
  };
  if (source.type === 'log') {
    result.logBase = 10;
    if (result.min === undefined) {
      result.min = (extent: { min: number }) => (extent.min > 0 ? extent.min * 0.9 : 1e-3);
    }
  }
  return result;
}

export function applyScientificFigurePolicy(
  option: EChartsOption,
  context: ScientificFigureContext,
): EChartsOption {
  const source = option as Record<string, unknown>;
  const { theme } = context;
  const dataCount = Math.max(0, context.dataCount ?? 0);
  const animate = !context.reducedMotion && dataCount <= 1500;
  const tooltip = source.tooltip && typeof source.tooltip === 'object' && !Array.isArray(source.tooltip)
    ? source.tooltip as Record<string, unknown>
    : {};
  const axisPointer = tooltip.axisPointer
    && typeof tooltip.axisPointer === 'object'
    && !Array.isArray(tooltip.axisPointer)
    ? tooltip.axisPointer as Record<string, unknown>
    : {};
  const legend = source.legend && typeof source.legend === 'object' && !Array.isArray(source.legend)
    ? source.legend as Record<string, unknown>
    : {};
  const toolbox = source.toolbox && typeof source.toolbox === 'object' && !Array.isArray(source.toolbox)
    ? source.toolbox as Record<string, unknown>
    : {};
  const feature = toolbox.feature && typeof toolbox.feature === 'object'
    ? toolbox.feature as Record<string, unknown>
    : {};
  const saveAsImage = feature.saveAsImage && typeof feature.saveAsImage === 'object'
    ? feature.saveAsImage as Record<string, unknown>
    : {};

  return {
    ...option,
    backgroundColor: 'transparent',
    color: source.color ?? [...SCIENTIFIC_PALETTE],
    animation: animate,
    animationDuration: animate ? 260 : 0,
    animationDurationUpdate: animate ? 180 : 0,
    textStyle: {
      color: scientificTextColor(theme),
      fontFamily: SCIENTIFIC_FONT_FAMILY,
      ...(source.textStyle as object | undefined),
    },
    aria: {
      enabled: true,
      description: context.description ?? context.title ?? 'Scientific figure',
      decal: { show: false },
      ...(source.aria as object | undefined),
    },
    tooltip: {
      confine: true,
      appendToBody: true,
      transitionDuration: 0,
      backgroundColor: theme === 'dark' ? 'rgba(15,23,42,.97)' : 'rgba(255,255,255,.98)',
      borderColor: theme === 'dark' ? '#334155' : '#cbd5e1',
      borderWidth: 1,
      padding: 10,
      textStyle: {
        color: scientificTextColor(theme),
        fontFamily: SCIENTIFIC_FONT_FAMILY,
        fontSize: 11,
      },
      extraCssText: 'box-shadow:0 10px 28px rgba(15,23,42,.16);border-radius:8px;pointer-events:none;',
      ...tooltip,
      ...(tooltip.trigger === 'axis' ? { axisPointer: { snap: true, ...axisPointer } } : {}),
    },
    legend: source.legend === undefined
      ? undefined
      : {
          type: 'scroll',
          itemWidth: 14,
          itemHeight: 8,
          textStyle: {
            color: scientificMutedColor(theme),
            fontFamily: SCIENTIFIC_FONT_FAMILY,
            fontSize: 10,
          },
          ...legend,
        },
    toolbox: source.toolbox === false
      ? undefined
      : {
          right: 8,
          top: 6,
          itemSize: 14,
          iconStyle: { borderColor: scientificMutedColor(theme) },
          ...toolbox,
          feature: {
            ...feature,
            saveAsImage: {
              name: context.exportName ?? 'scientific-figure',
              pixelRatio: 3,
              backgroundColor: theme === 'dark' ? '#0f172a' : '#ffffff',
              ...saveAsImage,
            },
          },
        },
    xAxis: normalizeAxis(source.xAxis, theme) as EChartsOption['xAxis'],
    yAxis: normalizeAxis(source.yAxis, theme) as EChartsOption['yAxis'],
  };
}
