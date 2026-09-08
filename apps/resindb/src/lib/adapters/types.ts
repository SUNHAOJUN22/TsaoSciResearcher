import type {
  DataGovernanceMetadata,
  Product,
  ProductUpdates,
  QuantityRecord,
} from '@/types/index';

export interface MaterialPropertyValue {
  value: unknown;
  unit?: string;
  standard?: string;
  method?: string;
  temp?: string | number;
  temperature?: string | number;
  load?: string | number;
  sampleId?: string;
  batchId?: string;
  referenceId?: string;
  sourceUrl?: string;
  raw?: QuantityRecord['raw'];
  canonical?: QuantityRecord['canonical'];
  status?: QuantityRecord['status'];
  reasonCodes?: string[];
  provenanceRefs?: string[];
}

export interface MaterialPhysicsSpecs {
  density?: MaterialPropertyValue;
  mfr?: MaterialPropertyValue;
  tensileYield?: MaterialPropertyValue;
  flexuralModulus?: MaterialPropertyValue;
  izodImpact?: MaterialPropertyValue;
  [property: string]: MaterialPropertyValue | undefined;
}

export interface MaterialRecord {
  id: string;
  source: 'open_market' | 'my_lab';
  batchNo?: string;
  category: string;
  grade: string;
  manufacturer: string;
  description?: string;
  properties: MaterialPhysicsSpecs;
  timestamp: number;
  governance?: DataGovernanceMetadata;
  validationStatus?: 'VALID' | 'HOLD' | 'INVALID';
  validationReasonCodes?: string[];
}

export interface HistoryRecord {
  id: string;
  timestamp: number;
  description: string;
  snapshot: Product[];
}

export interface IProductAdapter {
  search(query: string, categoryId: string | null): Promise<Product[]>;
  create(product: Partial<Product>): Promise<Product>;
  update(product: Product): Promise<Product>;
  batchUpdate(ids: string[], updates: ProductUpdates): Promise<void>;
  batchCreate(products: Partial<Product>[]): Promise<Product[]>;
  delete(ids: string[]): Promise<void>;
  exportReport(products: Product[], format: 'csv' | 'json' | 'xml'): Promise<Blob>;
  restoreSnapshot(products: Product[]): Promise<void>;
}
