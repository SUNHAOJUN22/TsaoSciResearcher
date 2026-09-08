import type { EChartsOption } from '@/lib/echarts';
import type { Product } from '@/types/index';
import { materialEngine } from '@/lib/materialScience';
import {
  SCIENTIFIC_PALETTE,
  escapeScientificHtml,
  formatScientificNumber,
  scientificMutedColor,
} from './scientificFigurePolicy';

const simulateCarreauYasudaProxy = (mfr: number, temperatureOffset: number, rate: number): number => {
  const safeFlow = Math.max(0.1, mfr);
  const eta0 = (80_000 / safeFlow ** 0.8) * Math.exp(temperatureOffset * -0.025);
  const lambda = 0.5 * safeFlow ** 0.4;
  const n = 0.32;
  const a = 2;
  return eta0 * (1 + (lambda * rate) ** a) ** ((n - 1) / a);
};

interface RheologyProxySeries {
  name: string;
  data: [number, number][];
  flowIndex: number | null;
  temperature: number;
  productIndex: number;
  temperatureIndex: number;
}

export const getRheologyChartOption = (
  products: Product[],
  theme: 'light' | 'dark',
  temperatures: number[] = [190, 210, 230],
  language: 'zh' | 'en' = 'zh',
): EChartsOption => {
  const proxies: RheologyProxySeries[] = [];
  products.forEach((product, productIndex) => {
    const flowValue = product.properties['熔体质量流动速率']?.value
      ?? product.properties.MFR?.value
      ?? product.properties.MFI?.value
      ?? product.properties['门尼粘度']?.value
      ?? product.properties['Mooney Viscosity']?.value;
    const parsed = Number(flowValue);
    const flowProxy = Number.isFinite(parsed) && parsed > 0 ? parsed : 5;
    const selectedTemperatures = products.length === 1 ? temperatures : [temperatures[0] ?? 190];
    selectedTemperatures.forEach((temperature, temperatureIndex) => {
      const data: [number, number][] = [];
      for (let index = 0; index <= 32; index++) {
        const rate = 10 ** (-2 + index * 0.25);
        data.push([rate, simulateCarreauYasudaProxy(flowProxy, temperature - 190, rate)]);
      }
      const highShear = data.filter(([rate]) => rate > 10).map(([rate, viscosity]) => ({ rate, stress: rate * viscosity }));
      proxies.push({
        name: `${product.gradeName}${selectedTemperatures.length > 1 ? ` @ ${temperature} °C` : ''}`,
        data,
        flowIndex: materialEngine.calculatePowerLawIndex(highShear)?.n ?? null,
        temperature,
        productIndex,
        temperatureIndex,
      });
    });
  });

  return {
    title: {
      text: language === 'en' ? 'Illustrative shear-viscosity proxy' : '示意性剪切黏度代理曲线',
      subtext: language === 'en'
        ? 'Rule-generated from flow attributes with fixed Carreau–Yasuda assumptions; not fitted rheometry.'
        : '由流动属性和固定 Carreau–Yasuda 假设生成；不是流变实验拟合结果。',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 650 },
      subtextStyle: { color: scientificMutedColor(theme), fontSize: 10 },
    },
    grid: { left: 76, right: 36, bottom: 70, top: 72, containLabel: true },
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
        const lines = [`γ̇: ${formatScientificNumber(Number(entries[0].axisValue))} s⁻¹`];
        for (const entry of entries) {
          const proxy = proxies[entry.seriesIndex];
          lines.push(`<strong>${escapeScientificHtml(entry.seriesName)}</strong>: ${formatScientificNumber(entry.value[1])} Pa·s`);
          lines.push(`${language === 'en' ? 'Proxy high-shear n' : '代理高剪切 n'}: ${proxy.flowIndex === null ? '—' : formatScientificNumber(proxy.flowIndex)}`);
        }
        return lines.join('<br/>');
      },
    },
    xAxis: { type: 'log', name: 'γ̇ (s⁻¹)', nameLocation: 'middle', nameGap: 34 },
    yAxis: { type: 'log', name: 'η (Pa·s)', nameLocation: 'middle', nameGap: 52 },
    series: proxies.map((series) => ({
      name: series.name,
      type: 'line' as const,
      smooth: false,
      showSymbol: false,
      data: series.data,
      lineStyle: {
        width: 1.7,
        color: SCIENTIFIC_PALETTE[series.productIndex % SCIENTIFIC_PALETTE.length],
        opacity: series.temperatureIndex === 0 ? 1 : 0.72,
        type: series.temperatureIndex === 0 ? 'solid' as const : series.temperatureIndex === 1 ? 'dashed' as const : 'dotted' as const,
      },
    })),
  };
};
