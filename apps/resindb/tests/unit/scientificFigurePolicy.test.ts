import { describe, expect, it } from 'vitest';
import {
  applyScientificFigurePolicy,
  escapeScientificHtml,
  formatScientificNumber,
  SCIENTIFIC_FIGURE_POLICY_VERSION,
  SCIENTIFIC_FONT_FAMILY,
} from '@/components/charts/scientificFigurePolicy';

describe('scientific figure policy', () => {
  it('enforces accessible export, CJK typography, log-axis and reduced-motion defaults', () => {
    const option = applyScientificFigurePolicy({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'log' },
      yAxis: { type: 'value' },
      series: [{ type: 'scatter', data: [[1, 2]] }],
    }, {
      theme: 'light',
      title: 'Test figure',
      exportName: 'test-figure',
      reducedMotion: true,
      dataCount: 1,
    }) as Record<string, unknown>;
    expect(SCIENTIFIC_FIGURE_POLICY_VERSION).toBe('scientific-figure-policy-1.1.0');
    expect(SCIENTIFIC_FONT_FAMILY).toContain('Noto Sans SC');
    expect(SCIENTIFIC_FONT_FAMILY).toContain('Microsoft YaHei');
    expect(option.animation).toBe(false);
    expect(option.aria).toMatchObject({ enabled: true });
    expect(option.textStyle).toMatchObject({ fontFamily: SCIENTIFIC_FONT_FAMILY });
    expect(option.toolbox).toMatchObject({
      feature: { saveAsImage: { name: 'test-figure', pixelRatio: 3 } },
    });
    expect(option.tooltip).toMatchObject({
      trigger: 'axis',
      transitionDuration: 0,
      axisPointer: { snap: true },
    });
    expect(option.xAxis).toMatchObject({ type: 'log', logBase: 10 });
  });

  it('preserves an explicit axis-pointer snap override', () => {
    const option = applyScientificFigurePolicy({
      tooltip: { trigger: 'axis', axisPointer: { snap: false, type: 'cross' } },
      xAxis: { type: 'value' },
      yAxis: { type: 'value' },
      series: [{ type: 'line', data: [[1, 2]] }],
    }, {
      theme: 'dark',
      dataCount: 1,
    }) as Record<string, unknown>;

    expect(option.tooltip).toMatchObject({
      axisPointer: { snap: false, type: 'cross' },
    });
  });

  it('formats scientific values and escapes tooltip labels', () => {
    expect(formatScientificNumber(0.00001234)).toMatch(/e-/);
    expect(formatScientificNumber(12.3456)).toBe('12.35');
    expect(escapeScientificHtml('<sample & "name">')).toBe('&lt;sample &amp; &quot;name&quot;&gt;');
  });
});
