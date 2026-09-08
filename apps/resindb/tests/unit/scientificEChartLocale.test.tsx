import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { ScientificEChart } from '@/components/charts/ScientificEChart';
import { LanguageProvider } from '@/contexts/LanguageContext';

const { chart, handlers } = vi.hoisted(() => {
  const eventHandlers = new Map<string, () => void>();
  const chartMock = {
    clear: vi.fn(),
    dispose: vi.fn(),
    isDisposed: vi.fn(() => false),
    resize: vi.fn(),
    setOption: vi.fn(() => eventHandlers.get('finished')?.()),
    on: vi.fn((event: string, handler: () => void) => eventHandlers.set(event, handler)),
    off: vi.fn((event: string, handler: () => void) => {
      if (eventHandlers.get(event) === handler) eventHandlers.delete(event);
    }),
  };
  return { chart: chartMock, handlers: eventHandlers };
});

vi.mock('@/lib/echarts', () => ({
  getInstanceByDom: vi.fn(() => null),
  init: vi.fn(() => chart),
}));

beforeEach(() => {
  window.localStorage.clear();
  handlers.clear();
  vi.clearAllMocks();
  chart.isDisposed.mockReturnValue(false);
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    callback(0);
    return 1;
  });
  vi.stubGlobal('cancelAnimationFrame', vi.fn());
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
});

describe('ScientificEChart language and render states', () => {
  test('renders governed Chinese and English empty states without exposing internal keys', () => {
    render(
      <LanguageProvider>
        <ScientificEChart
          option={null}
          theme="light"
          ariaLabel="测试图表"
          exportName="locale-state"
          empty
        />
      </LanguageProvider>,
    );

    expect(screen.getByText('暂无可绘制数据')).toBeInTheDocument();
    expect(screen.getByText('请调整变量、筛选条件或样本选择。')).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new CustomEvent('resindb-language-change', { detail: 'en-US' }));
    });

    expect(screen.getByText('No plottable data')).toBeInTheDocument();
    expect(screen.getByText('Adjust the variables, filters, or sample selection.')).toBeInTheDocument();
  });

  test('exposes a completed non-empty render contract after the ECharts finished event', () => {
    const { container } = render(
      <LanguageProvider>
        <ScientificEChart
          option={{
            xAxis: { type: 'value' },
            yAxis: { type: 'value' },
            series: [{ type: 'line', data: [[0, 0], [1, 1]] }],
          }}
          theme="light"
          ariaLabel="数理曲线"
          exportName="render-state"
          dataCount={2}
        />
      </LanguageProvider>,
    );

    const figure = container.querySelector('[data-scientific-figure="true"]');
    const surface = container.querySelector('[data-scientific-chart-canvas="true"]');
    expect(figure).toHaveAttribute('data-scientific-figure-state', 'ready');
    expect(figure).toHaveAttribute('data-scientific-figure-points', '2');
    expect(surface).toHaveAttribute('data-scientific-chart-rendered', 'true');
    expect(chart.setOption).toHaveBeenCalledWith(
      expect.any(Object),
      { notMerge: true, lazyUpdate: false },
    );
  });
});
