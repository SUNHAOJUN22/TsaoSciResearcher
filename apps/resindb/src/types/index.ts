export type Language = 'zh' | 'en';

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  avatar?: string;
}

export interface Category {
  id: string;
  name: string;
  nameEn?: string;
  children?: Category[];
}

export interface Reference {
  id: string;
  name: string;
  author?: string;
  year?: string;
}

export interface Manufacturer {
  id: string;
  name: string;
  website?: string;
  description?: string;
  country?: string;
}

export type QuantityStatus = 'VALID' | 'UNKNOWN' | 'INVALID';

export interface RawQuantity {
  value: unknown;
  unit?: string;
  method?: string;
  standard?: string;
  conditions?: Record<string, unknown>;
  temperature?: string | number;
  temp?: string | number;
  load?: string | number;
  sampleId?: string;
  batchId?: string;
  referenceId?: string;
  sourceUrl?: string;
}

export interface CanonicalQuantity {
  value: number;
  unit: string;
  dimension: string;
}

export interface QuantityRecord {
  raw: RawQuantity;
  canonical?: CanonicalQuantity;
  status: QuantityStatus;
  reasonCodes: string[];
  provenanceRefs: string[];
}

export type ResinSourceType =
  | 'DEMO'
  | 'SYNTHETIC'
  | 'REFERENCE'
  | 'MEASURED'
  | 'IMPORTED'
  | 'UNKNOWN';

export type ResinGovernedRecordStatus =
  | 'DEMO'
  | 'SYNTHETIC'
  | 'REFERENCE'
  | 'MEASURED'
  | 'IMPORTED'
  | 'NOT_FOR_RELEASE'
  | 'UNKNOWN';

export type ResinConfidentiality = 'PUBLIC' | 'INTERNAL' | 'RESTRICTED' | 'UNKNOWN';

export interface DataGovernanceMetadata {
  sourceType: ResinSourceType;
  recordStatus: ResinGovernedRecordStatus;
  confidentiality: ResinConfidentiality;
  license: string;
  provenanceRefs: string[];
  lastVerifiedAt?: string;
}

export interface PropertyValue {
  value: string | number;
  unit?: string;
  method?: string;
  sampleId?: string;
  batchId?: string;
  provenanceRefs?: string[];
  quantity?: QuantityRecord;
  standard?: string;
  temperature?: string | number;
  referenceId?: string;
  instrument?: string;
  sourceUrl?: string;
  annotation?: string;
  mean?: number;
  stdDev?: number;
  min?: number;
  max?: number;
  count?: number;
  temp?: string;
  load?: string | number;
}

export interface Product {
  id: string;
  gradeName: string;
  manufacturerId: string;
  manufacturer: string;
  categoryIds: string[];
  properties: Record<string, PropertyValue>;
  createdAt: string;
  updatedAt: string;
  isExperimental?: boolean;
  tags?: string[];
  priority?: number;
  governance?: DataGovernanceMetadata;
}

export type ViewMode = 'grid' | 'chart';
export type AppView = 'dashboard' | 'analytics' | 'pivot' | 'dependencies' | 'settings' | 'beta-sandbox';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

export interface FormulaHistory {
  date: string;
  expression: string;
  name: string;
  unit?: string;
  description?: string;
}

export interface FormulaConfig {
  id: string;
  name: string;
  expression: string;
  unit?: string;
  description?: string;
  history?: FormulaHistory[];
}

export interface TemplateParameter {
  key: string;
  label: string;
  type: 'number' | 'text';
  defaultValue: string | number;
  placeholder?: string;
  unit?: string;
  description?: string;
}

export interface FormulaTemplate {
  id: string;
  name: string;
  description: string;
  unit: string;
  baseExpression: string;
  parameters: TemplateParameter[];
  category: string;
  isCustom?: boolean;
  createdAt?: string;
}

export interface ColumnConfig {
  key: string;
  label: string;
  visible: boolean;
  isSystem?: boolean;
  isComputed?: boolean;
  type?: 'string' | 'number';
  formulaId?: string;
  unit?: string;
  isPinned?: boolean;
}

export interface SortConfig {
  key: string;
  direction: 'asc' | 'desc';
}

export type FilterOperator =
  | 'contains'
  | 'equals'
  | 'startsWith'
  | 'endsWith'
  | 'gt'
  | 'lt'
  | 'gte'
  | 'lte'
  | 'isEmpty'
  | 'isNotEmpty';

export interface FilterCondition {
  id: string;
  field: string;
  operator: FilterOperator;
  value: unknown;
}

export interface FilterGroup {
  id: string;
  type: 'group';
  logic: 'AND' | 'OR';
  conditions: (FilterCondition | FilterGroup)[];
}

export interface PropertyUpdate {
  [key: string]: string | number | PropertyValue;
}

export interface ProductUpdates extends Partial<Product> {
  _propertyUpdates?: PropertyUpdate;
}

export interface AiAction {
  type: string;
  payload: Product | string[] | BatchUpdateResult | Record<string, unknown> | unknown;
  label: string;
}

export interface BatchUpdateResult {
  ids: string[];
  updates: ProductUpdates;
}

export interface FilterItem {
  id: string;
  label: string;
  type: 'search' | 'category' | 'numeric' | 'advanced';
  onRemove: () => void;
}

export interface SavedView {
  id: string;
  name: string;
  query: string;
  filters: FilterGroup | null;
  columns: ColumnConfig[];
}

export interface SyncEvent {
  id: string;
  timestamp: number;
  status: 'success' | 'error';
  message: string;
}
