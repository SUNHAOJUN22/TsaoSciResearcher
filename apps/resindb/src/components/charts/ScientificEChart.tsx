import React, {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import { AlertCircle, Database, Loader2 } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import * as echarts from '@/lib/echarts';
import { applyScientificFigurePolicy, type ScientificFigureTheme } from './scientificFigurePolicy';

export interface ScientificEChartProps {
  option: echarts.EChartsOption | null;
  theme: ScientificFigureTheme;
  ariaLabel: string;
  description?: string;
  exportName?: string;
  dataCount?: number;
  loading?: boolean;
  empty?: boolean;
  error?: string | null;
  className?: string;
  height?: number | string;
  onChartReady?: (chart: echarts.ECharts) => void;
}

const FIGURE_STATE_TEXT = {
  zh: {
    calculating: '正在计算科学图表',
    unavailable: '图表暂不可用',
    empty: '暂无可绘制数据',
    calculatingDetail: '数值模型正在后台 Worker 中运行。',
    emptyDetail: '请调整变量、筛选条件或样本选择。',
  },
  en: {
    calculating: 'Calculating scientific figure',
    unavailable: 'Figure unavailable',
    empty: 'No plottable data',
    calculatingDetail: 'The numerical model is running in a background Worker.',
    emptyDetail: 'Adjust the variables, filters, or sample selection.',
  },
} as const;

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  return reduced;
}

export const ScientificEChart: React.FC<ScientificEChartProps> = React.memo(({
  option,
  theme,
  ariaLabel,
  description,
  exportName,
  dataCount = 0,
  loading = false,
  empty = false,
  error = null,
  className = '',
  height = '100%',
  onChartReady,
}) => {
  const { language } = useLanguage();
  const messages = FIGURE_STATE_TEXT[language];
  const descriptionId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const onChartReadyRef = useRef(onChartReady);
  const reducedMotion = useReducedMotion();
  const normalizedOption = useMemo(() => (
    option
      ? applyScientificFigurePolicy(option, {
          theme,
          title: ariaLabel,
          description,
          exportName,
          dataCount,
          reducedMotion,
        })
      : null
  ), [ariaLabel, dataCount, description, exportName, option, reducedMotion, theme]);

  useEffect(() => {
    onChartReadyRef.current = onChartReady;
  }, [onChartReady]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    const chart = echarts.getInstanceByDom(container)
      ?? echarts.init(container, undefined, { renderer: 'canvas', useDirtyRect: true });
    chartRef.current = chart;
    onChartReadyRef.current?.(chart);

    let disposed = false;
    const markRendered = () => {
      if (!disposed && !chart.isDisposed()) {
        container.dataset.scientificChartRendered = 'true';
      }
    };
    chart.on('finished', markRendered);
    container.dataset.scientificChartRendered = 'false';

    const resizeAfterLayout = () => {
      if (disposed || chart.isDisposed()) return;
      const bounds = container.getBoundingClientRect();
      if (bounds.width > 0 && bounds.height > 0) {
        chart.resize({ animation: { duration: 0 } });
      }
    };
    const frame = requestAnimationFrame(resizeAfterLayout);
    void document.fonts?.ready.then(resizeAfterLayout);

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      chart.off('finished', markRendered);
      delete container.dataset.scientificChartRendered;
      if (!chart.isDisposed()) chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const container = containerRef.current;
    if (!chart || chart.isDisposed()) return undefined;
    if (container) container.dataset.scientificChartRendered = 'false';
    if (!normalizedOption || empty || error) {
      chart.clear();
      return undefined;
    }
    chart.setOption(normalizedOption, { notMerge: true, lazyUpdate: false });
    const resize = () => {
      const bounds = container?.getBoundingClientRect();
      if (bounds && bounds.width > 0 && bounds.height > 0 && !chart.isDisposed()) {
        chart.resize({ animation: { duration: 0 } });
      }
    };
    resize();
    const frame = requestAnimationFrame(resize);
    return () => cancelAnimationFrame(frame);
  }, [empty, error, normalizedOption]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    let frame = 0;
    const scheduleResize = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const chart = chartRef.current;
        const bounds = container.getBoundingClientRect();
        if (chart && !chart.isDisposed() && bounds.width > 0 && bounds.height > 0) {
          chart.resize({ animation: { duration: 0 } });
        }
      });
    };

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', scheduleResize);
      scheduleResize();
      return () => {
        cancelAnimationFrame(frame);
        window.removeEventListener('resize', scheduleResize);
      };
    }

    const observer = new ResizeObserver((entries) => {
      if (entries.some((entry) => entry.contentRect.width > 0 && entry.contentRect.height > 0)) {
        scheduleResize();
      }
    });
    observer.observe(container);
    scheduleResize();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  const stateVisible = loading || empty || Boolean(error);
  const figureState = loading
    ? 'loading'
    : error
      ? 'error'
      : empty
        ? 'empty'
        : normalizedOption
          ? 'ready'
          : 'unavailable';

  return (
    <div
      className={`scientific-figure relative w-full overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 ${className}`}
      style={{ height, minHeight: 300 }}
      data-scientific-figure="true"
      data-scientific-figure-state={figureState}
      data-scientific-figure-points={dataCount}
    >
      <div
        ref={containerRef}
        role="img"
        aria-label={ariaLabel}
        aria-describedby={description ? descriptionId : undefined}
        className={`h-full w-full transition-opacity ${stateVisible ? 'opacity-0' : 'opacity-100'}`}
        data-scientific-chart-canvas="true"
      />
      {description && <span id={descriptionId} className="sr-only">{description}</span>}
      {stateVisible && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-white/96 p-6 text-center dark:bg-slate-950/96"
          role={error ? 'alert' : 'status'}
        >
          <div className="max-w-sm">
            {loading ? (
              <Loader2
                className="mx-auto mb-3 animate-spin text-indigo-600 motion-reduce:animate-none"
                size={28}
                aria-hidden="true"
              />
            ) : error ? (
              <AlertCircle className="mx-auto mb-3 text-rose-600" size={28} aria-hidden="true" />
            ) : (
              <Database className="mx-auto mb-3 text-slate-400" size={28} aria-hidden="true" />
            )}
            <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              {loading ? messages.calculating : error ? messages.unavailable : messages.empty}
            </div>
            <div className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
              {error ?? (loading ? messages.calculatingDetail : messages.emptyDetail)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
