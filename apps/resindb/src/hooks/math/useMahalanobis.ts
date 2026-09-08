import { useState, useCallback, useEffect } from 'react';
import { Product } from '@/types/index';
import { useToasts } from '@/contexts/ToastContext';
import { useMahalanobisWorker as useWorker } from '@/hooks/workers/useMahalanobisWorker';

export function useMahalanobisWorker() {
  const [outlierResults, setOutlierResults] = useState<Record<string, { isOutlier: boolean; distance: number; contributingFeatures: string[] }>>({});
  const { isCalculating: isDetecting, result, runAnalysis } = useWorker();
  const { addToast } = useToasts();

  useEffect(() => {
    if (result) {
       const mapped: Record<string, { isOutlier: boolean; distance: number; contributingFeatures: string[] }> = {};
       let count = 0;
       result.distances.forEach(d => {
           mapped[d.id] = { isOutlier: d.isOutlier, distance: d.distance, contributingFeatures: [] };
           if(d.isOutlier) count++;
       });
       setOutlierResults(mapped);
       if(count > 0) addToast('error', `Identified ${count} anomalous data points using Mahalanobis distance.`);
       else addToast('success', "Data distribution conforms to expected structural limits.");
    }
  }, [result, addToast]);

  const detectOutliers = useCallback((products: Product[], features: string[]) => {
      if (products.length <= features.length) {
         addToast("error", "For Mahalanobis detection, the number of records must strictly exceed the number of features.");
         return;
      }
      const dataRecord = products.map(p => {
          const m = { _id: p.id, name: p.gradeName } as Record<string, number> & { _id: string, name: string };
          features.forEach(f => {
              const val = parseFloat(String(p.properties[f]?.value));
              m[f] = isNaN(val) ? 0 : val;
          });
          return m;
      });
      runAnalysis(dataRecord, features, 0.05); // using 0.05 alpha instead of raw threshold
  }, [addToast, runAnalysis]);

  const clearOutliers = useCallback(() => {
    setOutlierResults({});
  }, []);

  return {
    outlierResults,
    isDetecting,
    detectOutliers,
    clearOutliers
  };
}
