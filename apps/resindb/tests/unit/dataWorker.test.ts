import { describe, expect, it, vi } from 'vitest';
import type { ColumnConfig, Product } from '@/types/index';

interface WorkerScope {
  onmessage?: (event: MessageEvent) => void;
  postMessage(value: unknown): void;
}

const products: Product[] = [
  {
    id: 'p1', gradeName: 'PP A', manufacturerId: 'm', manufacturer: 'Maker',
    categoryIds: ['cat_pp'], createdAt: '2026-08-02', updatedAt: '2026-08-02',
    priority: 2,
    properties: { 密度: { value: 0.9 }, 标签值: { value: '12abc' } },
  },
  {
    id: 'p2', gradeName: 'PP B', manufacturerId: 'm', manufacturer: 'Maker',
    categoryIds: ['cat_pp'], createdAt: '2026-08-02', updatedAt: '2026-08-02',
    priority: 1,
    properties: { 密度: { value: 0.92 }, 标签值: { value: 12 } },
  },
];

const columns: ColumnConfig[] = [
  { key: 'gradeName', label: 'Grade', visible: true, type: 'string' },
  { key: '密度', label: 'Density', visible: true, type: 'number' },
  { key: '标签值', label: 'Tag value', visible: true, type: 'number' },
];

describe('data grid worker contract', () => {
  it('initializes, filters and keeps malformed numeric strings out of numerical anomaly parsing', async () => {
    vi.resetModules();
    const replies: unknown[] = [];
    const scope: WorkerScope = { postMessage: (value) => replies.push(value) };
    vi.stubGlobal('self', scope);
    await import('@/workers/dataWorker');

    scope.onmessage!({
      data: { type: 'INIT_DATA', payload: { allProducts: products, formulas: [], columns } },
    } as MessageEvent);
    expect((replies.at(-1) as { type: string }).type).toBe('INIT_SUCCESS');

    scope.onmessage!({
      data: {
        type: 'QUERY',
        payload: {
          activeFilters: [],
          sortConfig: [],
          detectAnomaliesKey: '标签值',
        },
      },
    } as MessageEvent);

    const response = replies.at(-1) as {
      type: string;
      payload: { resultIds: string[]; outliers: string[] };
    };
    expect(response.type).toBe('QUERY_RESULT');
    expect(response.payload.resultIds).toEqual(['p2', 'p1']);
    expect(response.payload.outliers).toEqual([]);
    vi.unstubAllGlobals();
  });
});
