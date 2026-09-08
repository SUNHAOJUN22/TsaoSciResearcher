import { logger } from '@/lib/logger';
import { buildSpearmanPayload } from '@/lib/spearmanPayload';
import React, { useEffect, useState, useRef } from 'react';
import type { SpearmanMessage, SpearmanResponse } from '@/workers/spearmanWorker';
import { Loader2 } from 'lucide-react';
import { Product } from '@/types/index';

interface CorrelationMatrixProps {
  data: Product[];
  keys: string[];
}

export const CorrelationMatrix: React.FC<CorrelationMatrixProps> = ({ data, keys }) => {
  const [matrix, setMatrix] = useState<number[][]>([]);
  const [loading, setLoading] = useState(false);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    const worker = new Worker(new URL('../../workers/spearmanWorker.ts', import.meta.url), { type: 'module' });
    workerRef.current = worker;

    worker.onmessage = (e: MessageEvent<SpearmanResponse>) => {
      const res = e.data;
      if (res.type === 'SPEARMAN_RESULT') {
        setMatrix(res.payload.matrix);
        setLoading(false);
      } else if (res.type === 'ERROR') {
        setLoading(false);
        logger.error(res.payload.message);
      }
    };

    return () => worker.terminate();
  }, []);

  useEffect(() => {
    if (data.length === 0 || keys.length < 2 || !workerRef.current) return;
    setLoading(true);

    workerRef.current.postMessage({
      type: 'COMPUTE_SPEARMAN',
      payload: { data: buildSpearmanPayload(data, keys), keys }
    } as SpearmanMessage);

  }, [data, keys]);

  if (loading) {
     return <div className="flex items-center justify-center p-12 text-slate-400 gap-2"><Loader2 className="animate-spin" size={20}/> Computing Spearman Rank Correlation...</div>;
  }

  if (matrix.length === 0) return null;

  const getColor = (val: number) => {
     // Red for positive (+1), Blue for negative (-1), White/transparent for 0
     if (val > 0) {
        return `rgba(239, 68, 68, ${val * 0.9})`; // rose-500
     } else if (val < 0) {
        return `rgba(59, 130, 246, ${Math.abs(val) * 0.9})`; // blue-500
     }
     return 'transparent';
  };

  return (
    <div className="w-full overflow-auto custom-scrollbar relative p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
      <div className="flex mb-2">
         <div className="w-24 shrink-0" />
         {keys.map((k) => (
             <div key={k} className="w-12 h-24 shrink-0 relative">
                <span className="absolute bottom-2 left-1/2 -translate-x-1/2 rotate-[-45deg] origin-bottom-left text-[10px] font-mono text-slate-600 dark:text-slate-400 whitespace-nowrap">
                  {k.length > 8 ? k.substring(0,8) + '..' : k}
                </span>
             </div>
         ))}
      </div>
      {keys.map((rowKey, i) => (
         <div key={rowKey} className="flex">
            <div className="w-24 shrink-0 flex items-center justify-end pr-3 text-[10px] font-mono text-slate-600 dark:text-slate-400 text-right truncate">
              {rowKey.length > 12 ? rowKey.substring(0, 12) + '..' : rowKey}
            </div>
            {keys.map((colKey, j) => (
               <div 
                 key={`${rowKey}-${colKey}`}
                 className="w-12 h-12 shrink-0 border border-slate-100 dark:border-slate-800 flex items-center justify-center group relative cursor-crosshair transition-transform hover:z-10 hover:scale-110 hover:shadow-lg rounded-sm"
                 style={{ backgroundColor: getColor(matrix[i][j]) }}
               >
                  <span className="opacity-0 group-hover:opacity-100 text-[9px] font-black pointer-events-none drop-shadow-md text-slate-900 dark:text-white mix-blend-overlay">
                    {matrix[i][j].toFixed(2)}
                  </span>
               </div>
            ))}
         </div>
      ))}
      <div className="mt-6 flex items-center gap-4 text-[10px] font-mono text-slate-500 justify-center">
         <div className="flex items-center gap-1"><div className="w-3 h-3 bg-blue-500 rounded-sm" /> -1 (Inverse)</div>
         <div className="flex items-center gap-1"><div className="w-3 h-3 bg-slate-100 dark:bg-slate-800 rounded-sm border" /> 0</div>
         <div className="flex items-center gap-1"><div className="w-3 h-3 bg-rose-500 rounded-sm" /> +1 (Direct)</div>
      </div>
    </div>
  );
};
