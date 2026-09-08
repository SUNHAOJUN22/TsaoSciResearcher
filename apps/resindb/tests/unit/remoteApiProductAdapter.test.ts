import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Product } from '@/types/index';
import { RemoteAPIProductAdapter } from '@/lib/adapters/RemoteAPIProductAdapter';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p-1',
    gradeName: 'PP-R1',
    manufacturerId: 'm-1',
    manufacturer: 'Maker',
    categoryIds: ['cat_pp'],
    properties: { Density: { value: 0.9 } },
    createdAt: '2026-07-28',
    updatedAt: '2026-07-28',
    ...overrides,
  };
}

const response = (body: unknown, init: ResponseInit = {}) => new Response(
  typeof body === 'string' ? body : JSON.stringify(body),
  { status: 200, headers: { 'Content-Type': 'application/json' }, ...init },
);

describe('RemoteAPIProductAdapter runtime boundary', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => vi.unstubAllGlobals());

  it('encodes search parameters and validates a Product array', async () => {
    vi.mocked(fetch).mockResolvedValue(response([product()]));
    const adapter = new RemoteAPIProductAdapter('https://api.example.test/v1');
    await expect(adapter.search('PP R1', 'cat_pp')).resolves.toEqual([product()]);
    expect(fetch).toHaveBeenCalledWith(
      'https://api.example.test/v1/products?q=PP+R1&categoryId=cat_pp',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('rejects a JSON object where a Product array is required', async () => {
    vi.mocked(fetch).mockResolvedValue(response({ products: [product()] }));
    await expect(new RemoteAPIProductAdapter('https://api.example.test').search('', null))
      .rejects.toThrow(/non-array payload/);
  });

  it('rejects malformed Product property envelopes', async () => {
    vi.mocked(fetch).mockResolvedValue(response([product({
      properties: { Density: { value: null as unknown as number } },
    })]));
    await expect(new RemoteAPIProductAdapter('https://api.example.test').search('', null))
      .rejects.toThrow(/invalid Product payload/);
  });

  it('includes bounded remote error details without applying a local write', async () => {
    vi.mocked(fetch).mockResolvedValue(response('upstream failed', { status: 503 }));
    await expect(new RemoteAPIProductAdapter('https://api.example.test').create({ gradeName: 'X' }))
      .rejects.toThrow(/Remote create failed; no local write was applied.*503.*upstream failed/);
  });

  it('validates create and update response payloads', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response(product()));
    const adapter = new RemoteAPIProductAdapter('https://api.example.test/');
    await expect(adapter.create({ gradeName: 'PP-R1' })).resolves.toEqual(product());

    vi.mocked(fetch).mockResolvedValueOnce(response({ ok: true }));
    await expect(adapter.update(product())).rejects.toThrow(/invalid Product payload/);
  });

  it('skips empty mutation batches without issuing HTTP requests', async () => {
    const adapter = new RemoteAPIProductAdapter('https://api.example.test');
    await adapter.batchUpdate([], {});
    await expect(adapter.batchCreate([])).resolves.toEqual([]);
    await adapter.delete([]);
    expect(fetch).not.toHaveBeenCalled();
  });
});
