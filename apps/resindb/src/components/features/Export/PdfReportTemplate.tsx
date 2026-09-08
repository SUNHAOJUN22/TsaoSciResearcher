import React, { forwardRef, useEffect, useMemo, useRef } from 'react';
import { Calculator } from 'lucide-react';

import { PROPERTY_GROUPS } from '@/config/constants';
import { useLanguage } from '@/contexts/LanguageContext';
import { useFormulas } from '@/hooks/math/useFormulas';
import * as echarts from '@/lib/echarts';
import { formulaEngine } from '@/lib/formulaParser';
import type { Product, PropertyValue } from '@/types/index';
import { RADAR_DEFAULT_MAX } from '@/utils/productUtils';
import { buildFiniteRadarProjection } from '@/utils/radarProjection';

interface PdfReportTemplateProps {
  product: Product;
}

type PropertyGroupMap = Record<string, Array<[string, PropertyValue]>>;

function groupProperties(product: Product): PropertyGroupMap {
  const groups: PropertyGroupMap = {
    General: [],
    Mechanical: [],
    Thermal: [],
    'Optical/Electrical': [],
    Chemical: [],
    Other: [],
  };

  for (const [key, value] of Object.entries(product.properties ?? {})) {
    const groupName = Object.keys(PROPERTY_GROUPS).find((candidate) =>
      PROPERTY_GROUPS[candidate].some((groupKey) => key.includes(groupKey) || groupKey === key),
    );
    groups[groupName ?? 'Other'].push([key, value as PropertyValue]);
  }
  return groups;
}

export const PdfReportTemplate = forwardRef<HTMLDivElement, PdfReportTemplateProps>(
  ({ product }, ref) => {
    const { tProp, language } = useLanguage();
    const chartRef = useRef<HTMLDivElement>(null);
    const { formulas } = useFormulas();
    const radar = useMemo(() => buildFiniteRadarProjection(product), [product]);
    const groups = useMemo(() => groupProperties(product), [product]);
    const computedValues = useMemo(
      () => (formulas.length > 0 ? formulaEngine.compileGraph(formulas)(product) : {}),
      [formulas, product],
    );

    useEffect(() => {
      if (radar.status !== 'OK' || !chartRef.current) return undefined;

      const chartInstance = echarts.init(chartRef.current);
      const indicator = radar.keys.map((key, index) => {
        const value = radar.values[index];
        const defaultMax = RADAR_DEFAULT_MAX[key] ?? 100;
        return {
          name: tProp(key).slice(0, 15),
          min: value < 0 ? value * 1.1 : 0,
          max: Math.max(defaultMax, value > 0 ? value * 1.1 : 1),
        };
      });

      chartInstance.setOption({
        backgroundColor: 'transparent',
        radar: {
          indicator,
          radius: '65%',
          splitNumber: 5,
          axisName: { color: '#334155', fontSize: 11, fontWeight: 'bold' },
          splitLine: { lineStyle: { color: '#cbd5e1' } },
          splitArea: {
            show: true,
            areaStyle: { color: ['#f8fafc', '#f1f5f9', '#e2e8f0', '#cbd5e1'] },
          },
          axisLine: { lineStyle: { color: '#cbd5e1' } },
        },
        series: [
          {
            type: 'radar',
            data: [
              {
                value: radar.values,
                areaStyle: { color: 'rgba(14, 165, 233, 0.2)' },
                lineStyle: { color: '#0ea5e9', width: 2 },
                symbol: 'circle',
                symbolSize: 6,
                itemStyle: { color: '#0ea5e9' },
              },
            ],
          },
        ],
        animation: false,
      });

      return () => chartInstance.dispose();
    }, [radar, tProp]);

    const isEnglish = language === 'en';

    return (
      <div className="absolute top-[-9999px] left-[-9999px]">
        <div
          ref={ref}
          style={{ width: '800px', backgroundColor: 'white', color: 'black' }}
          className="relative overflow-hidden p-10 font-sans"
        >
          <div className="pointer-events-none absolute inset-0 z-0 flex rotate-[-45deg] select-none items-center justify-center text-[120px] font-black lowercase tracking-tighter opacity-[0.03]">
            resindb pro
          </div>

          <div className="relative z-10">
            <div className="mb-6 flex items-center justify-between border-b-4 border-slate-900 pb-6">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-slate-900 text-3xl font-black text-white shadow-md">
                  R
                </div>
                <div>
                  <h1 className="text-3xl font-black tracking-tight text-slate-900">ResinDB Pro</h1>
                  <p className="mt-1 font-mono text-sm uppercase tracking-widest text-slate-500">
                    {isEnglish ? 'Technical Data Sheet' : '标准物性表 (TDS)'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="mb-1 text-xs font-bold uppercase text-slate-400">
                  {isEnglish ? 'Report Date' : '生成日期'}
                </p>
                <p className="font-mono text-lg font-bold text-slate-800">
                  {new Date().toLocaleDateString()}
                </p>
              </div>
            </div>

            <div className="mb-8 rounded-xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
              <h2 className="mb-2 text-4xl font-black text-slate-900">{product.gradeName}</h2>
              <div className="mt-3 flex items-center gap-6 border-t border-slate-200 pt-3 font-mono text-base text-slate-700">
                <span className="flex items-center gap-2 font-bold">
                  <span className="text-slate-400">
                    {isEnglish ? 'Manufacturer:' : '生产厂商:'}
                  </span>
                  <span className="text-slate-900">{product.manufacturer}</span>
                </span>
                <span className="flex items-center gap-2 font-bold">
                  <span className="text-slate-400">{isEnglish ? 'Data ID:' : '数据编号:'}</span>
                  <span className="text-slate-900">{product.id.slice(0, 8)}</span>
                </span>
              </div>
            </div>

            <div className="mb-8 grid grid-cols-5 gap-6">
              <div className="col-span-3 rounded-xl border border-slate-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-base font-bold uppercase tracking-widest text-slate-800">
                  {isEnglish ? 'Radar Analysis' : '多维性能全景'}
                </h3>
                {radar.status === 'OK' ? (
                  <div ref={chartRef} style={{ width: '100%', height: '280px' }} />
                ) : (
                  <div
                    className="flex h-[280px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 px-8 text-center text-sm text-slate-500"
                    data-radar-status={radar.status}
                  >
                    {isEnglish
                      ? `Radar not rendered: fewer than ${radar.minimumDimensions} finite properties. Missing or malformed values were not converted to zero.`
                      : `雷达图未生成：有限数值属性少于 ${radar.minimumDimensions} 项；缺失值或格式错误值不会被转换为零。`}
                  </div>
                )}
              </div>

              <div className="col-span-2 flex flex-col rounded-xl border border-indigo-100 bg-indigo-50/50 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-base font-bold uppercase tracking-widest text-indigo-900">
                  <Calculator size={18} className="text-indigo-600" />
                  {isEnglish ? 'Computed Metrics' : '算法衍生指标'}
                </h3>
                <div className="flex-1 space-y-4">
                  {formulas.length > 0 ? (
                    formulas.slice(0, 4).map((formula) => {
                      const value = computedValues[formula.id];
                      const displayValue =
                        typeof value === 'number' && Number.isFinite(value)
                          ? value.toFixed(2)
                          : '-';
                      return (
                        <div
                          key={formula.id}
                          className="rounded-lg border border-indigo-100 bg-white p-3 shadow-sm"
                        >
                          <div
                            className="mb-1 truncate text-xs font-bold uppercase text-slate-500"
                            title={formula.name}
                          >
                            {formula.name}
                          </div>
                          <div className="flex items-end gap-2">
                            <div className="font-mono text-xl font-bold text-indigo-700">
                              {displayValue}
                            </div>
                            {formula.unit ? (
                              <div className="mb-1 font-mono text-xs text-slate-400">
                                {formula.unit}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="mt-10 text-center text-sm text-slate-400">
                      {isEnglish
                        ? 'No computed formulas configured.'
                        : '暂无已配置的衍生算法公式。'}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-4 border-b-2 border-slate-800 pb-2 text-base font-bold uppercase tracking-widest text-slate-800">
                {isEnglish ? 'Reported Properties' : '已报告理化性能参数'}
              </h3>

              <div className="grid grid-cols-2 gap-x-8 gap-y-6">
                {Object.entries(groups).map(([groupName, items]) => {
                  if (items.length === 0) return null;
                  return (
                    <div key={groupName} className="break-inside-avoid">
                      <h4 className="mb-3 rounded-md border-l-4 border-slate-400 bg-slate-100 px-3 py-1.5 text-sm font-bold uppercase tracking-wider text-slate-700">
                        {isEnglish ? `${groupName} Properties` : `${tProp(groupName)} 性能组`}
                      </h4>
                      <table className="w-full border-collapse text-left font-mono text-xs">
                        <thead>
                          <tr className="border-b border-slate-300 text-slate-500">
                            <th className="w-[55%] px-2 py-2 font-medium">
                              {isEnglish ? 'Property' : '项目'}
                            </th>
                            <th className="w-[25%] px-2 py-2 font-medium">
                              {isEnglish ? 'Value' : '报告值'}
                            </th>
                            <th className="w-[20%] px-2 py-2 font-medium">
                              {isEnglish ? 'Unit' : '单位'}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {items.map(([key, property]) => (
                            <tr key={key}>
                              <td className="px-2 py-2.5 font-bold text-slate-700">
                                {tProp(key)}
                              </td>
                              <td className="px-2 py-2.5 text-slate-900">
                                {String(property.value ?? '-')}
                              </td>
                              <td className="px-2 py-2.5 text-slate-400">
                                {property.unit || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-12 flex justify-between border-t border-slate-200 pt-6 font-mono text-[10px] font-medium uppercase tracking-widest text-slate-400">
              <p>ResinDB Pro Data Intelligence System</p>
              <p>
                {isEnglish ? 'Screening document' : '筛选用途文档'} •{' '}
                {new Date().getFullYear()}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  },
);

PdfReportTemplate.displayName = 'PdfReportTemplate';
