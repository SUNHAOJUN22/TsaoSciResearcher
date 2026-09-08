import { Product } from '@/types/index';

export interface QualityWorkerMessage {
  type: 'RUN_MONITOR';
  payload: {
    allProducts: Product[];
    options?: {
      zThreshold?: number;             // Standard deviation threshold (default: 3)
      iqrMultiplier?: number;          // Interquartile Range multiplier (default: 1.5)
      importantKeys?: string[];        // Specific core properties to verify completeness
    };
  };
}

export interface OutlierItem {
  productId: string;
  gradeName: string;
  manufacturer: string;
  propertyKey: string;
  value: number;
  stats: {
    mean: number;
    stdDev: number;
    zScore: number;
    q1: number;
    q3: number;
    iqr: number;
    iqrLower: number;
    iqrUpper: number;
    method: 'z-score' | 'iqr' | 'both';
  };
}

export interface MissingValueItem {
  productId: string;
  gradeName: string;
  manufacturer: string;
  propertyKey: string;
  importance: 'critical' | 'high' | 'normal';
}

export interface PropertyQualityStats {
  key: string;
  totalCount: number;
  missingCount: number;
  completenessRate: number; // 0 - 100
  mean: number;
  stdDev: number;
  q1: number;
  q3: number;
  iqr: number;
  min: number;
  max: number;
  outlierCount: number;
}

export interface QualityMonitorResultPayload {
  healthScore: number; // Overall quality index (0 - 100)
  totalValuesChecked: number;
  totalMissingCount: number;
  totalOutliersCount: number;
  outliers: OutlierItem[];
  missing: MissingValueItem[];
  propertyStats: PropertyQualityStats[];
}

export type QualityWorkerResponse =
  | { type: 'QUALITY_MONITOR_RESULT'; payload: QualityMonitorResultPayload }
  | { type: 'ERROR'; payload: { message: string } };

// Simple parsing helper to extract numeric value safely
function parseNumeric(val: unknown): { isNum: boolean; value: number } {
  if (val === undefined || val === null) return { isNum: false, value: 0 };
  const strVal = String(val).trim();
  if (strVal === '') return { isNum: false, value: 0 };
  const parsed = Number(strVal);
  if (!Number.isFinite(parsed)) return { isNum: false, value: 0 };
  return { isNum: true, value: parsed };
}

self.onmessage = (e: MessageEvent<QualityWorkerMessage>) => {
  try {
    const { allProducts, options = {} } = e.data.payload;
    const zThreshold = options.zThreshold ?? 3;
    const iqrMultiplier = options.iqrMultiplier ?? 1.5;
    
    // Core property registry to track critical missing indicators
    const criticalKeys = ['密度', 'Density', '熔体质量流动速率', 'MFR', 'MFI', '熔融指数', '拉伸强度', 'Tensile Strength', '拉伸屈服应力', '弯曲模量', 'Flexural Modulus', '缺口冲击强度', 'Impact Strength'];
    const highKeys = ['弯曲强度', 'Flexural Strength', '断烈伸长率', 'Elongation', '维卡软化温度', 'Vicat Softening', '热变形温度', 'HDT', '邵氏硬度', 'Hardness'];

    if (!allProducts || allProducts.length === 0) {
      self.postMessage({
        type: 'QUALITY_MONITOR_RESULT',
        payload: {
          healthScore: 100,
          totalValuesChecked: 0,
          totalMissingCount: 0,
          totalOutliersCount: 0,
          outliers: [],
          missing: [],
          propertyStats: []
        }
      });
      return;
    }

    // 1. Collect all property keys dynamically across the dataset
    const allPropertyKeys = new Set<string>();
    allProducts.forEach(p => {
      if (p.properties) {
        Object.keys(p.properties).forEach(key => {
          allPropertyKeys.add(key);
        });
      }
    });

    const keyList = Array.from(allPropertyKeys);

    // 2. Perform baseline profiling & statistical aggregation for each property key
    const propertyStats: PropertyQualityStats[] = [];
    const outliers: OutlierItem[] = [];
    const missing: MissingValueItem[] = [];

    let totalValuesChecked = 0;
    let totalMissingCount = 0;

    keyList.forEach(key => {
      const numbers: { id: string; val: number; product: Product }[] = [];
      let missingCountForProp = 0;

      allProducts.forEach(product => {
        const prop = product.properties?.[key];
        const valObj = prop ? parseNumeric(prop.value) : { isNum: false, value: 0 };

        if (valObj.isNum) {
          numbers.push({ id: product.id, val: valObj.value, product });
          totalValuesChecked++;
        } else {
          missingCountForProp++;
          totalMissingCount++;
          
          let importance: 'critical' | 'high' | 'normal' = 'normal';
          if (criticalKeys.some(ck => ck.toLowerCase() === key.toLowerCase())) {
            importance = 'critical';
          } else if (highKeys.some(hk => hk.toLowerCase() === key.toLowerCase())) {
            importance = 'high';
          }
          
          missing.push({
            productId: product.id,
            gradeName: product.gradeName,
            manufacturer: product.manufacturer,
            propertyKey: key,
            importance
          });
        }
      });

      const totalCount = allProducts.length;
      const completenessRate = totalCount > 0 ? ((totalCount - missingCountForProp) / totalCount) * 100 : 0;

      // Calculate statistics if we have numeric observations
      let mean = 0;
      let stdDev = 0;
      let q1 = 0;
      let q3 = 0;
      let iqr = 0;
      let min = 0;
      let max = 0;
      let outlierCount = 0;

      if (numbers.length > 0) {
        // Sort values to calculate percentiles
        numbers.sort((a, b) => a.val - b.val);
        min = numbers[0].val;
        max = numbers[numbers.length - 1].val;

        // Mean
        const sum = numbers.reduce((acc, curr) => acc + curr.val, 0);
        mean = sum / numbers.length;

        // Standard Deviation
        const squaredDiffs = numbers.reduce((acc, curr) => acc + Math.pow(curr.val - mean, 2), 0);
        stdDev = Math.sqrt(Math.max(0, squaredDiffs / numbers.length));

        // Percentiles (Q1, Q3) and IQR
        const getPercentile = (p: number) => {
          const idx = (numbers.length - 1) * p;
          const base = Math.floor(idx);
          const rest = idx - base;
          if (numbers[base + 1] !== undefined) {
            return numbers[base].val + rest * (numbers[base + 1].val - numbers[base].val);
          }
          return numbers[base].val;
        };

        q1 = getPercentile(0.25);
        q3 = getPercentile(0.75);
        iqr = q3 - q1;

        const iqrLower = q1 - iqrMultiplier * iqr;
         const iqrUpper = q3 + iqrMultiplier * iqr;

         // Flag outliers based on combined or singular metrics
         numbers.forEach(item => {
           let isOutlierZ = false;
           let isOutlierIQR = false;
           const zScore = stdDev > 0 ? (item.val - mean) / stdDev : 0;

           if (stdDev > 0 && Math.abs(zScore) > zThreshold) {
             isOutlierZ = true;
           }

           if (iqr > 0 && (item.val < iqrLower || item.val > iqrUpper)) {
             isOutlierIQR = true;
           }

           // If standard deviation is extremely small, IQR is safer; use combining heuristic
           if (isOutlierZ || isOutlierIQR) {
             outlierCount++;
             const method = isOutlierZ && isOutlierIQR ? 'both' : isOutlierZ ? 'z-score' : 'iqr';
             
             outliers.push({
               productId: item.id,
               gradeName: item.product.gradeName,
               manufacturer: item.product.manufacturer,
               propertyKey: key,
               value: item.val,
               stats: {
                 mean,
                 stdDev,
                 zScore,
                 q1,
                 q3,
                 iqr,
                 iqrLower,
                 iqrUpper,
                 method
               }
             });
           }
         });
      }

      propertyStats.push({
        key,
        totalCount,
        missingCount: missingCountForProp,
        completenessRate,
        mean,
        stdDev,
        q1,
        q3,
        iqr,
        min,
        max,
        outlierCount
      });
    });

    // 3. Calculate Overall Scientific Health Score (0 - 100)
    // - Starts at 100
    // - Deductions: completeness score penalty (average missing percent weighted)
    // - Deductions: outliers percentage penalty
    const averageCompleteness = propertyStats.length > 0 ? (propertyStats.reduce((acc, stat) => acc + stat.completenessRate, 0) / propertyStats.length) : 100;
    const outlierRatio = totalValuesChecked > 0 ? (outliers.length / totalValuesChecked) : 0;
    
    // Custom formula: Health Score leans heavily on completeness and flags outlier rate
    let healthScore = (averageCompleteness * 0.7) + (Math.max(0, 1 - outlierRatio * 3) * 30);
    healthScore = Math.max(0, Math.min(100, Math.round(healthScore)));

    // Sort observations for clean tables
    propertyStats.sort((a, b) => a.completenessRate - b.completenessRate); // Lowest completeness first
    outliers.sort((a, b) => Math.abs(b.stats.zScore) - Math.abs(a.stats.zScore)); // Highest deviation first

    self.postMessage({
      type: 'QUALITY_MONITOR_RESULT',
      payload: {
        healthScore,
        totalValuesChecked,
        totalMissingCount: totalMissingCount,
        totalOutliersCount: outliers.length,
        outliers,
        missing,
        propertyStats
      }
    } as QualityWorkerResponse);

  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: {
        message: error instanceof Error ? error.message : String(error)
      }
    } as QualityWorkerResponse);
  }
};
