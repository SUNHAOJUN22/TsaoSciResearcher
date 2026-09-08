import { expect, test, describe, vi, beforeEach } from 'vitest';
import { IndexedDBProductAdapter } from '../../src/lib/adapters/IndexedDBProductAdapter';
import { Product, ProductUpdates } from '../../src/types/index';

describe('🧪 IndexedDBProductAdapter Cache & Index Query Planner Suite', () => {
  let adapter: IndexedDBProductAdapter;
  let mockDB: any;

  const initialProducts: Product[] = [
    {
      id: 'p1',
      gradeName: 'HDPE-5502',
      manufacturer: 'Sinopec',
      manufacturerId: 'm1',
      categoryIds: ['cat_pe', 'sub_hdpe'],
      createdAt: '2026-06-18',
      updatedAt: '2026-06-18',
      properties: {
        '密度': { value: 0.954, unit: 'g/cm³' },
        '熔体质量流动速率': { value: 0.35, unit: 'g/10min' }
      }
    },
    {
      id: 'p2',
      gradeName: 'PP-T30S',
      manufacturer: 'PetroChina',
      manufacturerId: 'm2',
      categoryIds: ['cat_pp', 'sub_pp_homo'],
      createdAt: '2026-06-18',
      updatedAt: '2026-06-18',
      properties: {
        '密度': { value: 0.905, unit: 'g/cm³' },
        '熔体质量流动速率': { value: 3.2, unit: 'g/10min' }
      }
    }
  ];

  beforeEach(() => {
    // Mock global localStorage to avoid storage bridge lookup issues in node/vitest context
    const store: Record<string, string> = {};
    const mockLocalStorage = {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => { store[key] = value; },
      removeItem: (key: string) => { delete store[key]; },
      clear: () => { for (const k in store) delete store[k]; }
    };
    Object.defineProperty(global, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
      configurable: true
    });

    adapter = new IndexedDBProductAdapter();
    
    // Set up mock DB transaction interfaces
    mockDB = {
      get: vi.fn().mockImplementation((storeName, id) => {
        const found = initialProducts.find(p => p.id === id);
        return Promise.resolve(found ? { ...found } : undefined);
      }),
      getAll: vi.fn().mockResolvedValue([...initialProducts]),
      add: vi.fn().mockResolvedValue(undefined),
      put: vi.fn().mockResolvedValue(undefined),
      delete: vi.fn().mockResolvedValue(undefined),
      transaction: vi.fn().mockReturnValue({
        store: {
          get: vi.fn().mockImplementation((id) => {
            const found = initialProducts.find(p => p.id === id);
            return Promise.resolve(found ? { ...found } : undefined);
          }),
          put: vi.fn().mockResolvedValue(undefined),
          add: vi.fn().mockResolvedValue(undefined),
          delete: vi.fn().mockResolvedValue(undefined),
          clear: vi.fn().mockResolvedValue(undefined)
        },
        done: Promise.resolve()
      })
    };

    // Inject mock DB connection resolver
    vi.spyOn(adapter as any, 'getDB').mockResolvedValue(mockDB);
  });

  describe('1. Lazy Loading and Index Building', () => {
    test('Should lazily load products and construct category/property indexes on first search', async () => {
      expect((adapter as any).indicesRebuilt).toBe(false);

      const results = await adapter.search('', null);
      
      expect(results.length).toBe(2);
      expect((adapter as any).indicesRebuilt).toBe(true);
      expect((adapter as any).categoryInvertedIndex.get('cat_pe')).toContain('p1');
      expect((adapter as any).categoryInvertedIndex.get('cat_pp')).toContain('p2');
      
      // Verify property index was sorted
      const densityIdx = (adapter as any).propertyIndex.get('密度');
      expect(densityIdx).toBeDefined();
      expect(densityIdx[0].id).toBe('p2'); // 0.905 < 0.954
      expect(densityIdx[1].id).toBe('p1');
    });
  });

  describe('2. Query Planner Category Index Scans', () => {
    test('Should use inverted category index to filter candidates and skip full table scans', async () => {
      // Warm up cache & indices
      await adapter.search('', null);

      // Search with a specific category
      const results = await adapter.search('', 'sub_hdpe');
      
      expect(results.length).toBe(1);
      expect(results[0].id).toBe('p1');
    });

    test('Should fast-bail with empty array if category index returns zero matches', async () => {
      await adapter.search('', null);

      const results = await adapter.search('', 'sub_ldpe_film'); // Not in catalog
      expect(results).toEqual([]);
      expect(mockDB.getAll).toHaveBeenCalledTimes(1); // Read once only
    });
  });

  describe('3. Incremental Index Maintenance (CRUD)', () => {
    test('Should incrementally index created product', async () => {
      await adapter.search('', null); // Warm up

      const newProduct: Partial<Product> = {
        id: 'p3',
        gradeName: 'LDPE-2426H',
        manufacturer: 'Sinopec',
        categoryIds: ['cat_pe', 'sub_ldpe'],
        properties: {
          '密度': { value: 0.922, unit: 'g/cm³' }
        }
      };

      await adapter.create(newProduct);
      
      // Verify cache has the product
      const all = await adapter.search('', null);
      expect(all.length).toBe(3);
      expect(all.some(x => x.id === 'p3')).toBe(true);

      // Verify category inverted index was updated
      expect((adapter as any).categoryInvertedIndex.get('sub_ldpe')).toContain('p3');
      expect((adapter as any).categoryInvertedIndex.get('cat_pe')).toContain('p3');

      // Verify property index was re-sorted
      const densityIdx = (adapter as any).propertyIndex.get('密度');
      expect(densityIdx.length).toBe(3);
      expect(densityIdx[0].id).toBe('p2'); // 0.905
      expect(densityIdx[1].id).toBe('p3'); // 0.922
      expect(densityIdx[2].id).toBe('p1'); // 0.954
    });

    test('Should incrementally update indices when product is updated', async () => {
      await adapter.search('', null); // Warm up

      const originalProduct = (adapter as any).cachedProducts.find((p: any) => p.id === 'p1');
      const updatedProduct: Product = {
        ...originalProduct,
        categoryIds: ['cat_pe', 'sub_lldpe'], // Changed sub_hdpe to sub_lldpe
        properties: {
          ...originalProduct.properties,
          '密度': { value: 0.918, unit: 'g/cm³' } // Changed density 0.954 to 0.918
        }
      };

      await adapter.update(updatedProduct);

      // Verify old category was removed, new one added
      expect((adapter as any).categoryInvertedIndex.get('sub_hdpe').has('p1')).toBe(false);
      expect((adapter as any).categoryInvertedIndex.get('sub_lldpe')).toContain('p1');

      // Verify density index re-sorted
      const densityIdx = (adapter as any).propertyIndex.get('密度');
      expect(densityIdx[0].id).toBe('p2'); // 0.905
      expect(densityIdx[1].id).toBe('p1'); // 0.918 (used to be 0.954)
    });

    test('Should de-index deleted products', async () => {
      await adapter.search('', null); // Warm up

      await adapter.delete(['p2']);

      const all = await adapter.search('', null);
      expect(all.length).toBe(1);
      expect(all[0].id).toBe('p1');

      // Verify PP category index is empty/cleared of p2
      expect((adapter as any).categoryInvertedIndex.get('cat_pp').has('p2')).toBe(false);

      // Verify p2 is removed from properties index
      const densityIdx = (adapter as any).propertyIndex.get('密度');
      expect(densityIdx.some((x: any) => x.id === 'p2')).toBe(false);
    });

    test('Should apply batch updates incrementally', async () => {
      await adapter.search('', null); // Warm up

      const updates: ProductUpdates = {
        manufacturer: 'Sinopec Allied',
        _propertyUpdates: {
          '密度': 0.910
        }
      };

      // Only update p1, keeping p2 at 0.905
      await adapter.batchUpdate(['p1'], updates);

      const all = await adapter.search('', null);
      expect(all.find(p => p.id === 'p1')?.manufacturer).toBe('Sinopec Allied');

      const densityIdx = (adapter as any).propertyIndex.get('密度');
      expect(densityIdx[0].value).toBe(0.905); // p2 remains 0.905
      expect(densityIdx[1].value).toBe(0.910); // p1 updated to 0.910
    });
  });

  describe('4. Snapshot Restoration', () => {
    test('Should rebuild cache and index set completely on snapshot restore', async () => {
      await adapter.search('', null); // Warm up

      const newSnapshot: Product[] = [
        {
          id: 'p100',
          gradeName: 'ABS-757',
          manufacturer: 'Chimei',
          manufacturerId: 'm3',
          categoryIds: ['ABS'],
          createdAt: '2026-06-18',
          updatedAt: '2026-06-18',
          properties: {
            '密度': { value: 1.05, unit: 'g/cm³' }
          }
        }
      ];

      await adapter.restoreSnapshot(newSnapshot);

      const all = await adapter.search('', null);
      expect(all.length).toBe(1);
      expect(all[0].id).toBe('p100');

      // Verify indexes completely rebuilt from the snapshot
      expect((adapter as any).categoryInvertedIndex.get('ABS')).toContain('p100');
      expect((adapter as any).categoryInvertedIndex.get('cat_pe')).toBeUndefined();
    });
  });
});
