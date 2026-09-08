import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import { Download, Loader2, Zap } from 'lucide-react';
import { ScientificEChart } from './ScientificEChart';
import {
  escapeScientificHtml,
  formatScientificNumber,
  SCIENTIFIC_PALETTE,
  scientificTooltipItem,
  type ScientificFigureTheme,
} from './scientificFigurePolicy';
import { useTheme } from '@/contexts/ThemeContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useCarreauWorker } from '@/hooks/math/useCarreau';
import type { ECharts, EChartsOption } from '@/lib/echarts';
import type { Product } from '@/types/index';

export interface RheologyGraphProps {
  products: Product[];
  temps: number[];
}

export type RheologyEvidenceType = 'rule-generated-proxy' | 'fitted-model-of-proxy';

export interface RheologySeriesPoint {
  value: [number, number];
  evidenceType: RheologyEvidenceType;
  evidenceLabel: string;
}

/**
 * Phase 2L intentionally preserves the existing deterministic MFR screening
 * rule. These points are synthetic proxy observations, not rheometer data.
 */
export function simulateRheologyProxyPoints(mfr: number, temperatureOffset: number): [number, number][] {
  const eta0 = (80000 / Math.pow(Math.max(0.1, mfr), 0.8)) * Math.exp(temperatureOffset * -0.025);
  const lambda = 0.5 * Math.pow(Math.max(0.1, mfr), 0.4);
  const n = 0.32;
  const a = 2;
  const data: [number, number][] = [];
  for (let exponent = -2; exponent <= 6; exponent += 0.5) {
    const shearRate = Math.pow(10, exponent);
    const deterministicPerturbation = 1
      + Math.sin((exponent + mfr + temperatureOffset) * 12.9898) * 0.06;
    const viscosity = eta0
      * Math.pow(1 + Math.pow(lambda * shearRate, a), (n - 1) / a)
      * deterministicPerturbation;
    data.push([shearRate, viscosity]);
  }
  return data;
}

export function sanitizePositiveRheologyPoints(
  points: readonly [number, number][],
): [number, number][] {
  return points.filter(([shearRate, viscosity]) => (
    Number.isFinite(shearRate)
    && Number.isFinite(viscosity)
    && shearRate > 0
    && viscosity > 0
  ));
}

function localize(language: 'zh' | 'en', zh: string, en: string): string {
  return language === 'zh' ? zh : en;
}

function evidenceLabel(type: RheologyEvidenceType, language: 'zh' | 'en'): string {
  return type === 'rule-generated-proxy'
    ? localize(language, 'MFR 规则生成代理', 'rule-generated MFR proxy')
    : localize(language, '代理点的 Carreau–Yasuda 拟合模型', 'Carreau–Yasuda fitted model of proxy points');
}

export function getRheologyGraphOption(
  proxyPoints: readonly [number, number][],
  fittedPoints: readonly [number, number][],
  theme: ScientificFigureTheme,
  productLabel: string,
  targetTemperature: number,
  language: 'zh' | 'en',
): EChartsOption {
  const proxyData: RheologySeriesPoint[] = sanitizePositiveRheologyPoints(proxyPoints).map((value) => ({
    value,
    evidenceType: 'rule-generated-proxy',
    evidenceLabel: evidenceLabel('rule-generated-proxy', language),
  }));
  const fittedData: RheologySeriesPoint[] = sanitizePositiveRheologyPoints(fittedPoints).map((value) => ({
    value,
    evidenceType: 'fitted-model-of-proxy',
    evidenceLabel: evidenceLabel('fitted-model-of-proxy', language),
  }));

  return {
    title: {
      left: 14,
      top: 8,
      text: localize(
        language,
        `${productLabel}：MFR 派生流变筛选代理`,
        `${productLabel}: MFR-derived rheology screening proxy`,
      ),
      subtext: localize(
        language,
        `${targetTemperature} °C；代理点不是实测流变，虚线仅拟合这些代理点。`,
        `${targetTemperature} °C; proxy points are not measured rheology, and the dashed line only fits those proxies.`,
      ),
      textStyle: { fontSize: 14, fontWeight: 700 },
      subtextStyle: { fontSize: 10, lineHeight: 15 },
    },
    grid: { left: 76, right: 32, top: 92, bottom: 76 },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = scientificTooltipItem(params);
        const point = item?.data as RheologySeriesPoint | undefined;
        if (!point?.value) return '';
        return [
          `<strong>${escapeScientificHtml(point.evidenceLabel)}</strong>`,
          `${escapeScientificHtml(localize(language, '剪切速率', 'Shear rate'))}: ${formatScientificNumber(point.value[0])} s⁻¹`,
          `${escapeScientificHtml(localize(language, '粘度', 'Viscosity'))}: ${formatScientificNumber(point.value[1])} Pa·s`,
          `<em>${escapeScientificHtml(localize(language, '筛选代理，不是实测流变证据。', 'Screening proxy; not measured rheology evidence.'))}</em>`,
        ].join('<br/>');
      },
    },
    legend: { bottom: 8 },
    xAxis: {
      type: 'log',
      name: localize(language, '剪切速率 (s⁻¹)', 'Shear rate (s⁻¹)'),
      nameLocation: 'middle',
      nameGap: 34,
      logBase: 10,
    },
    yAxis: {
      type: 'log',
      name: localize(language, '粘度 (Pa·s)', 'Viscosity (Pa·s)'),
      nameLocation: 'middle',
      nameGap: 52,
      logBase: 10,
    },
    series: [
      {
        name: localize(language, 'MFR 规则代理点', 'Rule-generated MFR proxy points'),
        type: 'scatter',
        data: proxyData,
        symbolSize: 7,
        itemStyle: { color: SCIENTIFIC_PALETTE[0], opacity: 0.82 },
      },
      ...(fittedData.length > 0
        ? [{
            name: localize(language, '代理点拟合模型', 'Fitted model of proxy points'),
            type: 'line' as const,
            data: fittedData,
            smooth: false,
            showSymbol: false,
            lineStyle: { color: SCIENTIFIC_PALETTE[1], width: 2.5, type: 'dashed' as const },
          }]
        : []),
    ],
  };
}

function exportPng(chart: ECharts | null, theme: ScientificFigureTheme): void {
  if (!chart || chart.isDisposed()) return;
  const anchor = document.createElement('a');
  anchor.href = chart.getDataURL({
    type: 'png',
    pixelRatio: 3,
    backgroundColor: theme === 'dark' ? '#0f172a' : '#ffffff',
  });
  anchor.download = 'mfr-derived-rheology-proxy.png';
  anchor.click();
}

function finiteMfr(product: Product | undefined): number {
  const raw = product?.properties['熔体质量流动速率']?.value
    || product?.properties.MFR?.value
    || 5;
  const parsed = Number.parseFloat(String(raw));
  return Number.isFinite(parsed) ? parsed : 5;
}

export const RheologyGraph: React.FC<RheologyGraphProps> = React.memo(({ products, temps }) => {
  const { theme } = useTheme();
  const { language } = useLanguage();
  const chartRef = useRef<ECharts | null>(null);
  const { fittedParams, isFitting, fitCarreau, error } = useCarreauWorker();
  const mainProduct = products[0];
  const targetTemperature = temps[0] || 190;
  const proxyPoints = useMemo(
    () => mainProduct
      ? simulateRheologyProxyPoints(finiteMfr(mainProduct), targetTemperature - 190)
      : [],
    [mainProduct, targetTemperature],
  );
  const validProxyPoints = useMemo(
    () => sanitizePositiveRheologyPoints(proxyPoints),
    [proxyPoints],
  );
  const validFittedPoints = useMemo(
    () => sanitizePositiveRheologyPoints(fittedParams?.fittedData ?? []),
    [fittedParams?.fittedData],
  );

  useEffect(() => {
    if (validProxyPoints.length >= 3) {
      fitCarreau(
        validProxyPoints.map(([rate]) => rate),
        validProxyPoints.map(([, viscosity]) => viscosity),
      );
    }
  }, [fitCarreau, validProxyPoints]);

  const option = useMemo(
    () => getRheologyGraphOption(
      validProxyPoints,
      validFittedPoints,
      theme,
      mainProduct?.gradeName ?? localize(language, '未选择产品', 'No product selected'),
      targetTemperature,
      language,
    ),
    [language, mainProduct?.gradeName, targetTemperature, theme, validFittedPoints, validProxyPoints],
  );
  const handleChartReady = useCallback((chart: ECharts) => {
    chartRef.current = chart;
    const dom = chart.getDom();
    dom.dataset.phase2lChart = 'rheology-graph';
    dom.dataset.phase2lReadyCount = String(Number(dom.dataset.phase2lReadyCount ?? '0') + 1);
  }, []);
  const t = useCallback(
    (zh: string, en: string) => localize(language, zh, en),
    [language],
  );

  return (
    <section
      data-testid="rheology-graph-migrated"
      data-scientific-boundary="mfr-derived-proxy-not-measurement"
      data-legacy-wrapper="false"
      className="absolute inset-0 flex flex-col gap-3 px-5 pb-6 pt-20 md:px-8"
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <h3 className="flex items-center gap-2 text-lg font-black text-slate-900 dark:text-white">
            <Zap className="text-rose-500" size={20} />
            {t('MFR 派生流变筛选代理与 Carreau–Yasuda 拟合', 'MFR-derived rheology screening proxy and Carreau–Yasuda fit')}
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-300">
            {t(
              '科学边界：散点由既有 MFR 规则生成，不是实测流变数据；虚线是对这些代理点的有界非线性拟合，不是对测量值的拟合。',
              'Scientific boundary: scatter points are generated by the existing MFR rule, not measured rheology. The dashed line is a bounded nonlinear fit to those proxy points, not a fit to measurements.',
            )}
          </p>
        </div>

        <div className="flex items-start gap-2">
          <div data-testid="rheology-fit-parameters" className="min-w-[285px] rounded-2xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-950/90">
            {isFitting ? (
              <div className="flex min-h-20 items-center justify-center gap-2 text-xs font-bold text-rose-500" role="status">
                <Loader2 className="animate-spin motion-reduce:animate-none" size={18} />
                {t('正在拟合代理点…', 'Fitting proxy points…')}
              </div>
            ) : fittedParams ? (
              <>
                <div className="flex items-center justify-between border-b border-slate-100 pb-2 text-[10px] font-black uppercase tracking-wider text-slate-400 dark:border-slate-800">
                  <span>{t('代理拟合参数', 'Proxy-fit parameters')}</span>
                  <span className="rounded bg-emerald-50 px-2 py-0.5 font-mono text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-300">R² = {fittedParams.rSquared.toFixed(3)}</span>
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                  <div><dt className="text-slate-400">η₀ (Pa·s)</dt><dd className="font-mono font-black">{fittedParams.eta0.toExponential(2)}</dd></div>
                  <div><dt className="text-slate-400">λ (s)</dt><dd className="font-mono font-black">{fittedParams.lambda.toExponential(2)}</dd></div>
                  <div><dt className="text-slate-400">n</dt><dd className="font-mono font-black">{fittedParams.n.toFixed(3)}</dd></div>
                  <div><dt className="text-slate-400">a</dt><dd className="font-mono font-black">{fittedParams.a.toFixed(2)}</dd></div>
                </dl>
              </>
            ) : error ? (
              <div className="text-xs font-bold text-rose-600" role="alert">{error}</div>
            ) : (
              <div className="text-xs text-slate-500">{t('没有可拟合的正值代理点。', 'No positive proxy points are available for fitting.')}</div>
            )}
          </div>
          <button
            type="button"
            data-testid="rheology-export-png"
            onClick={() => exportPng(chartRef.current, theme)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-2 text-xs font-bold text-white hover:bg-rose-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/50"
          >
            <Download size={14} />
            PNG
          </button>
        </div>
      </div>

      <div data-testid="rheology-scientific-chart" className="min-h-[360px] flex-1">
        <ScientificEChart
          option={option}
          theme={theme}
          ariaLabel={t('MFR 派生流变代理及代理拟合模型', 'MFR-derived rheology proxy and fitted model of proxy points')}
          description={t(
            '所有绘图点均须为有限正值，以满足对数坐标定义域。非正值、NaN、Infinity 和缺失值不会进入图表或拟合。',
            'Every plotted point must be finite and positive to satisfy the logarithmic-domain contract. Non-positive values, NaN, Infinity, and missing values do not enter the chart or fit.',
          )}
          exportName="mfr-derived-rheology-proxy"
          dataCount={validProxyPoints.length + validFittedPoints.length}
          loading={isFitting && validFittedPoints.length === 0}
          empty={!mainProduct || validProxyPoints.length === 0}
          error={error}
          height="100%"
          onChartReady={handleChartReady}
        />
      </div>
    </section>
  );
});
