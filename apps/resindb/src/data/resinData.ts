import type { Category, Manufacturer, Product, Reference } from '@/types/index';
import type { MaterialRecord } from '@/lib/adapters/types';
import {
  isNonEmptyString,
  isProductRecord,
  isRecord,
  validateVersionedDataDocument,
  type VersionedDataDocument,
} from './dataContract';

export type { VersionedDataDocument } from './dataContract';

export interface ResinNetworkNode {
  id: string;
  group: 'chemical' | 'resin';
  radius?: number;
  desc?: string;
  formula?: string;
  cas?: string;
}

export interface ResinNetworkLink { source: string; target: string; value?: number }
export interface CategoryAlias { categoryId: string; canonicalName: string; aliases: string[] }

export interface ResinDataFailure { asset: string; message: string }
export interface ResinDataStatus {
  baseUrl: string;
  loadedAt: string;
  usingFallback: boolean;
  failures: ResinDataFailure[];
}

export interface ResinDataCatalog {
  categoryTree: Category[];
  propertyGroups: Record<string, string[]>;
  manufacturers: Manufacturer[];
  references: Reference[];
  productCatalog: Product[];
  labRecords: MaterialRecord[];
  openMarketRecords: MaterialRecord[];
  network: { nodes: ResinNetworkNode[]; links: ResinNetworkLink[] };
  categoryAliases: CategoryAlias[];
}

const NORMALIZED_BASE_URL = `${import.meta.env.BASE_URL.replace(/\/?$/, '/') }data/resins`;

export function validateDocument<T>(
  raw: unknown,
  kind: string,
  validateData: (value: unknown) => value is T,
): VersionedDataDocument<T> {
  return validateVersionedDataDocument(raw, kind, validateData);
}

const isArray = (value: unknown): value is unknown[] => Array.isArray(value);
const isCategoryArray = (value: unknown): value is Category[] =>
  Array.isArray(value) && value.every((item) => isRecord(item) && isNonEmptyString(item.id) && isNonEmptyString(item.name));
const isProductArray = (value: unknown): value is Product[] =>
  Array.isArray(value) && value.every(isProductRecord);
const isMaterialRecordArray = (value: unknown): value is MaterialRecord[] =>
  Array.isArray(value) && value.every((item) => isRecord(item) && typeof item.id === 'string' && typeof item.grade === 'string' && isRecord(item.properties));

function assertUniqueIds(items: Array<{ id: string }>, label: string): void {
  const seen = new Set<string>();
  for (const item of items) {
    if (seen.has(item.id)) throw new Error(`Duplicate ${label} id: ${item.id}`);
    seen.add(item.id);
  }
}

function flattenCategories(tree: Category[], stack = new Set<string>(), out: Category[] = []): Category[] {
  for (const node of tree) {
    if (stack.has(node.id)) throw new Error(`Category cycle detected at ${node.id}`);
    stack.add(node.id);
    out.push(node);
    if (node.children) flattenCategories(node.children, stack, out);
    stack.delete(node.id);
  }
  return out;
}

const fallbackCategoryTree: Category[] = [
  { id: 'root_plastic', name: '树脂数据暂不可用 (Data unavailable)', children: [] },
];

const fallbackProducts: Product[] = [
  {
    id: 'demo-fallback-hdpe',
    gradeName: 'HDPE Demo Fallback',
    manufacturerId: 'demo-manufacturer',
    manufacturer: 'Deterministic fallback dataset',
    categoryIds: ['root_plastic'],
    createdAt: '2026-07-25',
    updatedAt: '2026-07-25',
    properties: {
      密度: {
        value: 0.95,
        unit: 'g/cm³',
        annotation: 'External data assets failed to load; not a manufacturer specification.',
      },
      典型应用: { value: 'Runtime recovery record only' },
    },
  },
];

export async function loadResinDataCatalog(
  fetcher: typeof fetch = globalThis.fetch.bind(globalThis),
  baseUrl = NORMALIZED_BASE_URL,
): Promise<{ catalog: ResinDataCatalog; status: ResinDataStatus }> {
  const failures: ResinDataFailure[] = [];

  async function load<T>(
    asset: string,
    kind: string,
    validateData: (value: unknown) => value is T,
    fallback: T,
  ): Promise<T> {
    try {
      const response = await fetcher(`${baseUrl}/${asset}`, {
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(12_000),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
      const raw: unknown = await response.json();
      return validateDocument(raw, kind, validateData).data;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      failures.push({ asset, message });
      console.warn(`[ResinDB external data fallback] ${asset}: ${message}`);
      return fallback;
    }
  }

  const [
    categoryTree,
    propertyGroups,
    manufacturers,
    references,
    productCatalog,
    labRecords,
    openMarketRecords,
    network,
    categoryAliases,
  ] = await Promise.all([
    load('resin-taxonomy.json', 'resin-taxonomy', isCategoryArray, fallbackCategoryTree),
    load('resin-property-groups.json', 'resin-property-groups', (value): value is Record<string, string[]> => isRecord(value) && Object.values(value).every((entry) => Array.isArray(entry) && entry.every((item) => typeof item === 'string')), {}),
    load('resin-manufacturers.json', 'resin-manufacturers', (value): value is Manufacturer[] => Array.isArray(value) && value.every((item) => isRecord(item) && isNonEmptyString(item.id) && isNonEmptyString(item.name)), []),
    load('resin-references.json', 'resin-references', (value): value is Reference[] => Array.isArray(value) && value.every((item) => isRecord(item) && isNonEmptyString(item.id) && isNonEmptyString(item.name)), []),
    load('polymerDatabase.json', 'resin-seed-products', isProductArray, fallbackProducts),
    load('myLabUniverse.json', 'laboratory-material-records', isMaterialRecordArray, []),
    load('openMarketUniverse.json', 'market-material-records', isMaterialRecordArray, []),
    load('resin-network.json', 'resin-reaction-network', (value): value is { nodes: ResinNetworkNode[]; links: ResinNetworkLink[] } => isRecord(value) && isArray(value.nodes) && isArray(value.links), { nodes: [], links: [] }),
    load('resin-category-aliases.json', 'resin-category-aliases', (value): value is CategoryAlias[] => Array.isArray(value) && value.every((item) => isRecord(item) && typeof item.categoryId === 'string' && typeof item.canonicalName === 'string' && Array.isArray(item.aliases)), []),
  ]);

  const flatCategories = flattenCategories(categoryTree);
  assertUniqueIds(flatCategories, 'category');
  assertUniqueIds(manufacturers, 'manufacturer');
  assertUniqueIds(references, 'reference');
  assertUniqueIds(productCatalog, 'product');
  assertUniqueIds(labRecords, 'laboratory record');
  assertUniqueIds(openMarketRecords, 'market record');
  assertUniqueIds(network.nodes, 'network node');

  return {
    catalog: {
      categoryTree,
      propertyGroups,
      manufacturers,
      references,
      productCatalog,
      labRecords,
      openMarketRecords,
      network,
      categoryAliases,
    },
    status: {
      baseUrl,
      loadedAt: new Date().toISOString(),
      usingFallback: failures.length > 0,
      failures,
    },
  };
}

const runtimeData = await loadResinDataCatalog();

export const CATEGORY_TREE = runtimeData.catalog.categoryTree;
export const PROPERTY_GROUPS = runtimeData.catalog.propertyGroups;
export const MANUFACTURERS = runtimeData.catalog.manufacturers;
export const REFERENCES = runtimeData.catalog.references;
export const PRODUCT_CATALOG = runtimeData.catalog.productCatalog;
export const LAB_RECORDS = runtimeData.catalog.labRecords;
export const OPEN_MARKET_RECORDS = runtimeData.catalog.openMarketRecords;
export const RESIN_NETWORK = runtimeData.catalog.network;
export const CATEGORY_ALIASES = runtimeData.catalog.categoryAliases;
export const RESIN_DATA_STATUS = runtimeData.status;

const flatCategories = flattenCategories(CATEGORY_TREE);

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function matchesCategoryAlias(normalizedText: string, rawAlias: string): boolean {
  const alias = rawAlias.trim().toLowerCase();
  if (!alias) return false;
  if (normalizedText === alias) return true;

  // Short ASCII aliases such as PE/PP/PC must match a complete token. Using a
  // raw substring would incorrectly classify TPE as PE and PPR as PP.
  if (/^[a-z0-9-]{1,3}$/.test(alias)) {
    return new RegExp(`(^|[^a-z0-9])${escapeRegExp(alias)}([^a-z0-9]|$)`, 'i').test(normalizedText);
  }
  return normalizedText.includes(alias);
}

export function categoryIdFromText(text: string): string {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return 'root_plastic';

  const aliases = CATEGORY_ALIASES.flatMap((entry) =>
    entry.aliases.map((alias) => ({ entry, alias })),
  ).sort((a, b) => b.alias.length - a.alias.length);
  return aliases.find(({ alias }) => matchesCategoryAlias(normalized, alias))?.entry.categoryId ?? 'root_plastic';
}

export function categoryNameFromId(id: string): string {
  return CATEGORY_ALIASES.find((entry) => entry.categoryId === id)?.canonicalName ??
    flatCategories.find((entry) => entry.id === id)?.name ??
    'Resin';
}
