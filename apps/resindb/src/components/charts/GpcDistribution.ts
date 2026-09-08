import type { EChartsOption } from '@/lib/echarts';
import type { Product } from '@/types/index';
import { materialEngine } from '@/lib/materialScience';
import {
  SCIENTIFIC_PALETTE,
  escapeScientificHtml,
  formatScientificNumber,
  scientificMutedColor,
} from './scientificFigurePolicy';

interface ProxySeries {
  name: string;
  data: [number, number][];
  moments: ReturnType<typeof materialEngine.calculateMWDMoments>;
}

export const getGpcChartOption = (
  products: Product[],
  theme: 'light' | 'dark',
  language: 'zh' | 'en' = 'zh',
): EChartsOption => {
  const proxySeries: ProxySeries[] = products.map((product) => {
    const flowValue = product.properties['熔体质量流动速率']?.value
      ?? product.properties.MFR?.value
      ?? product.properties.MFI?.value
      ?? product.properties['门尼粘度']?.value
      ?? product.properties['Mooney Viscosity']?.value;
    const parsed = Number(flowValue);
    const flowProxy = Number.isFinite(parsed) && parsed > 0 ? parsed : 5;
    const peakLogMw = 5.8 - Math.log10(flowProxy) * 0.4;
    const polyethylene = product.gradeName.includes('PE') || product.categoryIds?.includes('聚乙烯');
    const width = polyethylene ? (product.gradeName.includes('LL') ? 0.35 : 0.5) : 0.45;
    const data: [number, number][] = [];
    for (let index = 0; index <= 75; index++) {
      const x = 2.5 + index * 0.08;
      data.push([x, Math.exp(-((x - peakLogMw) ** 2) / (2 * width ** 2))]);
    }
    return {
      name: product.gradeName,
      data,
      moments: materialEngine.calculateMWDMoments(data.map(([x, y]) => ({ x: 10 ** x, y }))),
    };
  });

  return {
    title: {
      text: language === 'en' ? 'Illustrative molecular-weight proxy' : '示意性分子量分布代理',
      subtext: language === 'en'
        ? 'Rule-generated from flow/viscosity attributes; not measured GPC data.'
        : '由流动/黏度属性规则生成；不是实测 GPC 数据。',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 650 },
      subtextStyle: { color: scientificMutedColor(theme), fontSize: 10 },
    },
    grid: { left: 72, right: 36, bottom: 70, top: 72, containLabel: true },
    legend: { bottom: 4 },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const entries = Array.isArray(params) ? params as Array<{
          axisValue: number;
          seriesIndex: number;
          seriesName: string;
          value: [number, number];
        }> : [];
        if (!entries.length) return '';
        const lines = [`log₁₀(M / g·mol⁻¹): ${formatScientificNumber(Number(entries[0].axisValue))}`];
        for (const entry of entries) {
          const proxy = proxySeries[entry.seriesIndex];
          lines.push(`<strong>${escapeScientificHtml(entry.seriesName)}</strong>: ${formatScientificNumber(entry.value[1])}`);
          lines.push(`${language === 'en' ? 'Proxy Mw / Đ' : '代理 Mw / Đ'}: ${proxy.moments ? `${formatScientificNumber(proxy.moments.mw)} / ${formatScientificNumber(proxy.moments.pdi)}` : '—'}`);
        }
        return lines.join('<br/>');
      },
    },
    xAxis: {
      type: 'value',
      name: 'log₁₀(M / g·mol⁻¹)',
      nameLocation: 'middle',
      nameGap: 34,
      min: 2.5,
      max: 8.5,
    },
    yAxis: {
      type: 'value',
      name: language === 'en' ? 'Normalized proxy intensity (a.u.)' : '归一化代理强度（a.u.）',
      nameLocation: 'middle',
      nameGap: 48,
      min: 0,
      max: 1.05,
    },
    series: proxySeries.map((series, index) => ({
      name: series.name,
      type: 'line' as const,
      smooth: false,
      showSymbol: false,
      data: series.data,
      lineStyle: { width: 1.7, color: SCIENTIFIC_PALETTE[index % SCIENTIFIC_PALETTE.length], opacity: 0.9 },
      emphasis: { lineStyle: { width: 2.4 } },
    })),
  };
};
