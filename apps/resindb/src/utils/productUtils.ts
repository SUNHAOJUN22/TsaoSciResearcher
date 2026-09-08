import { Product, ColumnConfig, PropertyValue } from '@/types/index';
import { DEFAULT_VISIBLE_COLUMNS } from '@/config/uiDefaults';

const EXPLICIT_PLACEHOLDERS = new Set([
  '',
  'unknown',
  'n/a',
  'na',
  '-',
  '--',
  '暂无',
  '未检测',
  'null',
  'nan',
]);

/**
 * Checks whether a value is an explicit missing-data marker.
 * Numeric zero and legitimate categorical text are valid scientific values.
 */
export const isPlaceholderValue = (value: unknown): boolean => {
  if (value === null || value === undefined) return true;
  if (typeof value === 'number') return !Number.isFinite(value);
  const normalized = String(value).trim().toLowerCase();
  return EXPLICIT_PLACEHOLDERS.has(normalized);
};

function propertyHasValue(properties: Record<string, PropertyValue>, keys: string[]): boolean {
  return keys.some((key) => {
    const property = properties[key];
    return property !== undefined && !isPlaceholderValue(property.value);
  });
}

export const getDynamicColumns = (products: Product[]): ColumnConfig[] => {
  const propertyKeys = new Set<string>();
  products.forEach((product) => {
    Object.keys(product.properties ?? {}).forEach((key) => propertyKeys.add(key));
  });
  const dynamicCols: ColumnConfig[] = Array.from(propertyKeys)
    .map((key) => ({
      key,
      label: key,
      visible: DEFAULT_VISIBLE_COLUMNS.includes(key),
      isSystem: false,
    }))
    .sort((a, b) => {
      const aIsLikelyImportant = DEFAULT_VISIBLE_COLUMNS.includes(a.key);
      const bIsLikelyImportant = DEFAULT_VISIBLE_COLUMNS.includes(b.key);
      if (aIsLikelyImportant && !bIsLikelyImportant) return -1;
      if (!aIsLikelyImportant && bIsLikelyImportant) return 1;
      return a.label.localeCompare(b.label);
    });
  return [
    { key: 'gradeName', label: 'gradeName', visible: true, isSystem: true },
    { key: 'manufacturer', label: 'manufacturer', visible: true, isSystem: true },
    ...dynamicCols,
  ];
};

/**
 * Calculates a multi-dimensional material data quality score (0-100).
 */
export const calculateCompleteness = (product: Product): number => {
  if (!product) return 0;

  let score = 0;
  const props = product.properties ?? {};
  const propKeys = Object.keys(props);

  if (product.gradeName?.trim().length > 2) score += 10;
  if (product.manufacturer?.trim() && !isPlaceholderValue(product.manufacturer) && product.manufacturer.trim().toLowerCase() !== 'unknown') score += 10;
  if (propertyHasValue(props, ['典型应用', 'Typical Application'])) score += 5;

  const cids = product.categoryIds ?? [];
  const isRubber = cids.some((id) => id.includes('rubber') || id.includes('epdm'));
  const isTPE = cids.some((id) => id.includes('tpe') || id.includes('tpu'));

  if (propertyHasValue(props, ['密度', 'Density'])) score += 10;

  if (isRubber || isTPE) {
    if (propertyHasValue(props, ['门尼粘度', 'Mooney Viscosity'])) score += 15;
    else if (isTPE && propertyHasValue(props, ['邵氏硬度', 'Hardness'])) score += 15;

    if (propertyHasValue(props, ['邵氏硬度', 'Hardness'])) score += 10;
    if (propertyHasValue(props, ['拉伸强度', 'Tensile Strength'])) score += 10;
    if (propertyHasValue(props, ['断裂伸长率', 'Elongation'])) score += 10;
  } else {
    if (propertyHasValue(props, ['熔体质量流动速率', 'MFR', 'MFI'])) score += 15;
    if (propertyHasValue(props, ['拉伸屈服应力', 'Tensile Stress', '拉伸强度'])) score += 10;
    if (propertyHasValue(props, ['弯曲模量', 'Flexural Modulus'])) score += 10;
    if (propertyHasValue(props, ['缺口冲击强度', 'Impact Strength'])) score += 10;
  }

  let standardCount = 0;
  propKeys.forEach((key) => {
    if (!isPlaceholderValue(props[key]?.value) && (props[key]?.standard?.trim().length ?? 0) > 2) standardCount += 1;
  });
  score += Math.min(10, standardCount * 2);
  if (propertyHasValue(props, ['热变形温度', '维卡软化温度', 'HDT'])) score += 5;
  if (propertyHasValue(props, ['阻燃等级', 'Flammability'])) score += 5;

  const validPropertyCount = getValidPropertiesCount(props);
  if (validPropertyCount > 5) score += 3;
  if (validPropertyCount > 10) score += 4;
  if (validPropertyCount > 20) score += 3;

  return Math.min(100, Math.round(score));
};

const lowerCache = new Map<string, string>();
export function getLower(value: string | undefined | null): string {
  if (value === undefined || value === null) return '';
  let lower = lowerCache.get(value);
  if (lower === undefined) {
    if (lowerCache.size >= 2_000) lowerCache.clear();
    lower = String(value).toLowerCase();
    lowerCache.set(value, lower);
  }
  return lower;
}

export const isLowBest = (key: string): boolean => {
  const normalized = getLower(key);
  return (
    normalized.includes('density') || normalized.includes('密度') ||
    normalized.includes('mfr') || normalized.includes('flow') || normalized.includes('流动') ||
    normalized.includes('shrinkage') || normalized.includes('收缩') ||
    normalized.includes('haze') || normalized.includes('雾度') ||
    normalized.includes('absorption') || normalized.includes('吸水') ||
    normalized.includes('yellow') || normalized.includes('黄色') ||
    normalized.includes('ash') || normalized.includes('灰分') ||
    normalized.includes('volatile') || normalized.includes('挥发') ||
    normalized.includes('coefficient') || normalized.includes('系数') ||
    normalized.includes('loss') || normalized.includes('损耗') ||
    normalized.includes('warpage') || normalized.includes('翘曲') ||
    normalized.includes('compression set') || normalized.includes('压缩永久变形')
  );
};

export const RADAR_KEYS = [
  '流动性',
  '硬度刚性',
  '耐热性',
  '拉伸性能',
  '冲击强度',
  '综合数据',
];

export const getPerformanceFingerprint = (product: Product): number[] => {
  const props = product.properties ?? {};
  const cids = product.categoryIds ?? [];
  const isRubber = cids.some((id) => id.includes('rubber') || id.includes('epdm'));
  const isTPE = cids.some((id) => id.includes('tpe') || id.includes('tpu'));

  const getValue = (keys: string[]) => {
    for (const key of keys) {
      const raw = props[key]?.value;
      if (isPlaceholderValue(raw)) continue;
      const numeric = Number(raw);
      if (Number.isFinite(numeric)) return numeric;
    }
    return 0;
  };

  const flow = isRubber
    ? getValue(['门尼粘度', 'Mooney Viscosity', 'ML 1+4', '门尼', 'Mooney', 'ML1+4'])
    : getValue(['熔体质量流动速率', 'MFR', 'MFI', 'Melt Flow Index', 'Melt Flow Rate', '流动速率', '流动性', '熔指']);

  const rigidity = isRubber || isTPE
    ? getValue(['邵氏硬度', 'Hardness', 'Shore A', 'Shore D', '硬度', 'Hardness (Shore A)', '邵氏A'])
    : getValue(['弯曲模量', 'Flexural Modulus', '弯曲弹性模量', '刚性模量', 'Flex Modulus', '弯曲模量(23°C)']);

  const heat = getValue(['热变形温度', 'HDT', '维卡软化温度', 'Vicat', '熔点', 'Melting Point', '脆化温度', 'Heat Deflection Temperature', 'HDT (0.45 MPa)']);
  const tensile = getValue(['拉伸屈服应力', 'Tensile Stress', '拉伸强度', 'Tensile Strength', '断裂拉伸应力', '屈服强度', 'Tensile Yield Stress', '拉伸断裂强度']);
  const impact = getValue(['悬臂梁缺口冲击强度', 'Izod Impact', '简支梁缺口冲击强度', 'Charpy Impact', '冲击强度', '落锤冲击', 'Notched Izod', 'Izod', '无缺口冲击强度']);

  return [flow, rigidity, heat, tensile, impact, calculateCompleteness(product)];
};

export const RADAR_DEFAULT_MAX: Record<string, number> = {
  流动性: 100,
  硬度刚性: 5_000,
  耐热性: 300,
  拉伸性能: 150,
  冲击强度: 120,
  综合数据: 100,
};

export const getValidPropertiesCount = (
  properties: Record<string, PropertyValue | unknown> | null | undefined,
): number => {
  if (!properties || typeof properties !== 'object') return 0;
  let count = 0;
  for (const property of Object.values(properties)) {
    const value = property && typeof property === 'object' && 'value' in property
      ? (property as { value: unknown }).value
      : property;
    if (!isPlaceholderValue(value)) count += 1;
  }
  return count;
};

function firstFinitePropertyValue(
  properties: Record<string, PropertyValue>,
  keys: string[],
): number | null {
  for (const key of keys) {
    const raw = properties[key]?.value;
    if (isPlaceholderValue(raw)) continue;
    const numeric = Number(raw);
    if (Number.isFinite(numeric)) return numeric;
  }
  return null;
}

export const getProductValidationWarnings = (
  product: Product,
  translate: (key: string) => string,
): string[] => {
  const warnings: string[] = [];
  const props = product.properties ?? {};

  if (Object.keys(props).length === 0) warnings.push(translate('warnNoProperties'));

  const density = firstFinitePropertyValue(props, ['密度', 'Density']);
  if (density !== null && (density < 0.7 || density >= 2.5)) {
    warnings.push(translate('warnDensityBounds').replace('{d}', String(density)));
  }

  const mfr = firstFinitePropertyValue(props, ['熔体质量流动速率', 'MFR', 'MFI']);
  if (mfr !== null && (mfr <= 0 || mfr > 500)) {
    warnings.push(translate('warnMfrBounds').replace('{m}', String(mfr)));
  }

  const tensile = firstFinitePropertyValue(props, ['拉伸屈服应力', 'Tensile Stress', 'Tensile Strength']);
  if (tensile !== null && (tensile <= 0 || tensile > 500)) {
    warnings.push(translate('warnTensileBounds').replace('{s}', String(tensile)));
  }

  const modulus = firstFinitePropertyValue(props, ['弯曲模量', 'Flexural Modulus']);
  if (modulus !== null && (modulus <= 10 || modulus > 50_000)) {
    warnings.push(translate('warnModulusBounds').replace('{s}', String(modulus)));
  }

  return warnings;
};
