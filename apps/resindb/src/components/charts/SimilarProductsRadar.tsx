import React, { useMemo } from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import type { Product } from '@/types/index';
import {
  buildNormalizedComparisonProfile,
  parseFiniteNumericValue,
  type SimilarityResult,
} from '@/services/mathUtils';
import { useLanguage } from '@/contexts/LanguageContext';

interface SimilarProductsRadarProps {
  targetProduct: Product;
  similarProducts: SimilarityResult[];
  allProducts: Product[];
}

interface RadarDatum {
  subject: string;
  fullKey: string;
  minimum: number;
  maximum: number;
  [seriesKey: string]: string | number;
}

export const SimilarProductsRadar: React.FC<SimilarProductsRadarProps> = ({
  targetProduct,
  similarProducts,
  allProducts,
}) => {
  const { tProp } = useLanguage();

  const profile = useMemo(() => buildNormalizedComparisonProfile(
    targetProduct,
    similarProducts.slice(0, 3),
    allProducts,
    (product, key) => parseFiniteNumericValue(product.properties[key]?.value),
    6,
  ), [allProducts, similarProducts, targetProduct]);

  const data = useMemo<RadarDatum[]>(() => profile.points.map((point) => ({
    subject: tProp(point.key).slice(0, 12),
    fullKey: point.key,
    minimum: point.minimum,
    maximum: point.maximum,
    ...point.normalized,
  })), [profile.points, tProp]);

  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'];

  if (data.length < 3) {
    return (
      <div className="flex items-center justify-center p-8 text-slate-400 font-mono text-xs text-center">
        At least three finite, variable properties shared by every compared grade are required for a radar profile.
      </div>
    );
  }

  return (
    <div className="w-full h-80 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-inner relative mt-4">
      <div className="absolute top-4 left-4 z-10 max-w-[75%]">
        <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500">
          Normalized shared-property profile
        </h4>
        <p className="mt-1 text-[8px] font-mono text-slate-400 leading-tight">
          0-100 min-max index across the governed comparison set; raw units are not mixed on one radial scale.
        </p>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="58%" outerRadius="62%" data={data}>
          <PolarGrid stroke="rgba(148, 163, 184, 0.2)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 'bold' }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fill: '#94a3b8', fontSize: 8 }}
            tickCount={5}
            axisLine={false}
          />
          <Tooltip
            formatter={(value) => [`${Number(value).toFixed(1)} / 100`, 'Normalized index']}
            labelFormatter={(_label, payload) => {
              const item = payload[0]?.payload as RadarDatum | undefined;
              return item
                ? `${tProp(item.fullKey)} · global range ${item.minimum} to ${item.maximum}`
                : '';
            }}
            contentStyle={{
              backgroundColor: 'rgba(15, 23, 42, 0.9)',
              borderColor: 'rgba(51, 65, 85, 0.5)',
              borderRadius: '8px',
              fontSize: '12px',
              color: '#fff',
              fontFamily: 'monospace',
            }}
          />
          {profile.series.map((series, index) => (
            <Radar
              key={series.productId}
              name={series.label}
              dataKey={series.key}
              stroke={colors[index % colors.length]}
              fill={colors[index % colors.length]}
              fillOpacity={index === 0 ? 0.35 : 0.08}
              strokeWidth={2}
              strokeDasharray={index === 0 ? undefined : '3 3'}
            />
          ))}
          <Legend
            wrapperStyle={{ fontSize: '10px', fontFamily: 'monospace', fontWeight: 'bold' }}
            iconType="circle"
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
