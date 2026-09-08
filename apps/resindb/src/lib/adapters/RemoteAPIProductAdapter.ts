import { logger } from '@/lib/logger';
import { IProductAdapter } from '@/lib/adapters/types';
import { Product, ProductUpdates, PropertyValue } from '@/types/index';

const DEFAULT_TIMEOUT_MS = 15_000;

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

const STRING_PROPERTY_FIELDS = ['unit', 'standard', 'temperature', 'referenceId', 'instrument', 'sourceUrl', 'annotation', 'temp', 'load'] as const;
const NUMBER_PROPERTY_FIELDS = ['mean', 'stdDev', 'min', 'max', 'count'] as const;

function isPropertyValue(value: unknown): value is PropertyValue {
  if (!isRecord(value)) return false;
  if (typeof value.value !== 'string' && !(typeof value.value === 'number' && Number.isFinite(value.value))) return false;
  if (STRING_PROPERTY_FIELDS.some((field) => value[field] !== undefined && typeof value[field] !== 'string')) return false;
  if (NUMBER_PROPERTY_FIELDS.some((field) => value[field] !== undefined && !(typeof value[field] === 'number' && Number.isFinite(value[field])))) return false;
  return true;
}

function isIsoDate(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0 && Number.isFinite(Date.parse(value));
}

function parseProductPayload(payload: unknown, context: string): Product {
  if (
    !isRecord(payload) ||
    typeof payload.id !== 'string' || !payload.id.trim() ||
    typeof payload.gradeName !== 'string' || !payload.gradeName.trim() ||
    typeof payload.manufacturerId !== 'string' || !payload.manufacturerId.trim() ||
    typeof payload.manufacturer !== 'string' || !payload.manufacturer.trim() ||
    !Array.isArray(payload.categoryIds) ||
    !payload.categoryIds.every((id) => typeof id === 'string') ||
    !isRecord(payload.properties) ||
    !Object.values(payload.properties).every(isPropertyValue) ||
    !isIsoDate(payload.createdAt) ||
    !isIsoDate(payload.updatedAt) ||
    (payload.isExperimental !== undefined && typeof payload.isExperimental !== 'boolean') ||
    (payload.tags !== undefined && (!Array.isArray(payload.tags) || !payload.tags.every((tag) => typeof tag === 'string'))) ||
    (payload.priority !== undefined && !(typeof payload.priority === 'number' && Number.isFinite(payload.priority)))
  ) {
    throw new Error(`Remote API returned an invalid Product payload for ${context}`);
  }
  return payload as unknown as Product;
}

function parseProductList(payload: unknown, context: string): Product[] {
  if (!Array.isArray(payload)) {
    throw new Error(`Remote API returned a non-array payload for ${context}`);
  }
  return payload.map((item, index) => parseProductPayload(item, `${context}[${index}]`));
}

/**
 * REST-backed product adapter.
 *
 * Read fallback is opt-in because switching data sources changes the meaning of
 * a query. Mutating requests never fall back to IndexedDB: silently applying a
 * write to a different database creates split-brain state and false success.
 */
export class RemoteAPIProductAdapter implements IProductAdapter {
  private readonly apiBaseUrl: string;
  private readonly readFallbackEnabled: boolean;
  private fallbackAdapter: IProductAdapter | null = null;

  constructor(
    apiBaseUrl = import.meta.env.VITE_REMOTE_API_BASE_URL || '/api',
    readFallbackEnabled = import.meta.env.VITE_REMOTE_READ_FALLBACK === 'true',
  ) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '');
    this.readFallbackEnabled = readFallbackEnabled;
  }

  private async getFallback(): Promise<IProductAdapter> {
    if (!this.fallbackAdapter) {
      const { IndexedDBProductAdapter } = await import('./IndexedDBProductAdapter');
      this.fallbackAdapter = new IndexedDBProductAdapter();
    }
    return this.fallbackAdapter;
  }

  private async request(path: string, init?: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

    try {
      const response = await fetch(`${this.apiBaseUrl}${path}`, {
        ...init,
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...init?.headers,
        },
      });

      if (!response.ok) {
        const details = await response.text().catch(() => '');
        throw new Error(
          `Remote API ${init?.method || 'GET'} ${path} failed with HTTP ${response.status}${
            details ? `: ${details.slice(0, 300)}` : ''
          }`,
        );
      }
      return response;
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error(`Remote API request timed out after ${DEFAULT_TIMEOUT_MS} ms`, { cause: error });
      }
      throw error;
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }

  private async withReadFallback<T>(
    operation: () => Promise<T>,
    fallback: (adapter: IProductAdapter) => Promise<T>,
    label: string,
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      if (!this.readFallbackEnabled) throw error;
      logger.warn(`${label}; using explicitly enabled IndexedDB read fallback`, error);
      return fallback(await this.getFallback());
    }
  }

  async search(query: string, categoryId: string | null): Promise<Product[]> {
    return this.withReadFallback(
      async () => {
        const params = new URLSearchParams();
        if (query) params.set('q', query);
        if (categoryId) params.set('categoryId', categoryId);
        const suffix = params.size > 0 ? `?${params.toString()}` : '';
        const response = await this.request(`/products${suffix}`);
        return parseProductList(await response.json(), 'search');
      },
      (adapter) => adapter.search(query, categoryId),
      'Remote product search failed',
    );
  }

  async create(product: Partial<Product>): Promise<Product> {
    try {
      const response = await this.request('/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(product),
      });
      return parseProductPayload(await response.json(), 'create');
    } catch (error) {
      throw new Error(`Remote create failed; no local write was applied: ${describeError(error)}`, { cause: error });
    }
  }

  async update(product: Product): Promise<Product> {
    try {
      const response = await this.request(`/products/${encodeURIComponent(product.id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(product),
      });
      return parseProductPayload(await response.json(), 'update');
    } catch (error) {
      throw new Error(`Remote update failed; no local write was applied: ${describeError(error)}`, { cause: error });
    }
  }

  async batchUpdate(ids: string[], updates: ProductUpdates): Promise<void> {
    if (ids.length === 0) return;
    try {
      await this.request('/products/batch-update', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, updates }),
      });
    } catch (error) {
      throw new Error(`Remote batch update failed; no local write was applied: ${describeError(error)}`, { cause: error });
    }
  }

  async batchCreate(products: Partial<Product>[]): Promise<Product[]> {
    if (products.length === 0) return [];
    try {
      const response = await this.request('/products/batch-create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ products }),
      });
      return parseProductList(await response.json(), 'batch-create');
    } catch (error) {
      throw new Error(`Remote batch create failed; no local write was applied: ${describeError(error)}`, { cause: error });
    }
  }

  async delete(ids: string[]): Promise<void> {
    if (ids.length === 0) return;
    try {
      await this.request('/products/batch-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
    } catch (error) {
      throw new Error(`Remote delete failed; no local write was applied: ${describeError(error)}`, { cause: error });
    }
  }

  async exportReport(products: Product[], format: 'csv' | 'json' | 'xml'): Promise<Blob> {
    return this.withReadFallback(
      async () => {
        const response = await this.request(`/products/export?format=${encodeURIComponent(format)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ products }),
        });
        return response.blob();
      },
      (adapter) => adapter.exportReport(products, format),
      'Remote report export failed',
    );
  }

  async restoreSnapshot(products: Product[]): Promise<void> {
    try {
      await this.request('/products/restore-snapshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ products }),
      });
    } catch (error) {
      throw new Error(`Remote snapshot restore failed; no local write was applied: ${describeError(error)}`, { cause: error });
    }
  }
}
