import type { DataGovernanceMetadata, Product, PropertyValue, QuantityRecord } from '@/types/index';
import {
  LAB_RECORDS,
  OPEN_MARKET_RECORDS,
  PRODUCT_CATALOG,
  categoryIdFromText,
  categoryNameFromId,
} from '@/data/resinData';
import { PolymerDataValidator } from './PolymerDataValidator';
import type { MaterialPropertyValue, MaterialRecord, MaterialPhysicsSpecs } from './types';

function normalizedRecordKey(record: Pick<MaterialRecord, 'grade' | 'manufacturer'>): string {
  return `${record.grade.trim().toLowerCase()}::${record.manufacturer.trim().toLowerCase()}`;
}

function finiteDisplayValue(value: unknown): string | number {
  if (typeof value === 'number') return Number.isFinite(value) ? value : 'UNKNOWN';
  if (typeof value === 'string') return value;
  return 'UNKNOWN';
}

function conservativeGovernance(record: MaterialRecord): DataGovernanceMetadata {
  if (record.governance) {
    return {
      ...record.governance,
      provenanceRefs: [...record.governance.provenanceRefs],
    };
  }
  return {
    sourceType: 'UNKNOWN',
    recordStatus: 'UNKNOWN',
    confidentiality: 'UNKNOWN',
    license: 'UNSPECIFIED',
    provenanceRefs: [],
  };
}

function quantityFromMaterialProperty(property: MaterialPropertyValue): QuantityRecord {
  return {
    raw: property.raw ?? {
      value: property.value,
      unit: property.unit,
      method: property.method,
      standard: property.standard,
      temperature: property.temperature,
      temp: property.temp,
      load: property.load,
      sampleId: property.sampleId,
      batchId: property.batchId,
      referenceId: property.referenceId,
      sourceUrl: property.sourceUrl,
    },
    canonical: property.canonical,
    status: property.status ?? 'UNKNOWN',
    reasonCodes: [...(property.reasonCodes ?? ['UNVALIDATED_LEGACY_PROPERTY'])],
    provenanceRefs: [...(property.provenanceRefs ?? [])],
  };
}

function materialToProductProperty(property: MaterialPropertyValue): PropertyValue {
  const quantity = quantityFromMaterialProperty(property);
  const displayValue = quantity.status === 'VALID' && quantity.canonical
    ? quantity.canonical.value
    : finiteDisplayValue(quantity.raw.value);
  return {
    value: displayValue,
    unit: quantity.canonical?.unit ?? quantity.raw.unit,
    method: quantity.raw.method,
    standard: quantity.raw.standard,
    temperature: quantity.raw.temperature ?? quantity.raw.temp,
    temp: typeof quantity.raw.temp === 'string' ? quantity.raw.temp : undefined,
    load: quantity.raw.load,
    sampleId: quantity.raw.sampleId,
    batchId: quantity.raw.batchId,
    referenceId: quantity.raw.referenceId,
    sourceUrl: quantity.raw.sourceUrl,
    provenanceRefs: quantity.provenanceRefs,
    quantity,
  };
}

function productToMaterialProperty(property: PropertyValue): MaterialPropertyValue {
  const quantity = property.quantity;
  if (quantity) {
    return {
      value: quantity.raw.value,
      unit: quantity.raw.unit,
      method: quantity.raw.method,
      standard: quantity.raw.standard,
      temperature: quantity.raw.temperature,
      temp: quantity.raw.temp,
      load: quantity.raw.load,
      sampleId: quantity.raw.sampleId,
      batchId: quantity.raw.batchId,
      referenceId: quantity.raw.referenceId,
      sourceUrl: quantity.raw.sourceUrl,
      raw: { ...quantity.raw, conditions: quantity.raw.conditions ? { ...quantity.raw.conditions } : undefined },
      canonical: quantity.canonical ? { ...quantity.canonical } : undefined,
      status: quantity.status,
      reasonCodes: [...quantity.reasonCodes],
      provenanceRefs: [...quantity.provenanceRefs],
    };
  }
  return {
    value: property.value,
    unit: property.unit,
    method: property.method,
    standard: property.standard,
    temperature: property.temperature,
    temp: property.temp,
    load: property.load,
    sampleId: property.sampleId,
    batchId: property.batchId,
    referenceId: property.referenceId,
    sourceUrl: property.sourceUrl,
    raw: {
      value: property.value,
      unit: property.unit,
      method: property.method,
      standard: property.standard,
      temperature: property.temperature,
      temp: property.temp,
      load: property.load,
      sampleId: property.sampleId,
      batchId: property.batchId,
      referenceId: property.referenceId,
      sourceUrl: property.sourceUrl,
    },
    status: 'UNKNOWN',
    reasonCodes: ['UNVALIDATED_LEGACY_PROPERTY'],
    provenanceRefs: [...(property.provenanceRefs ?? [])],
  };
}

export class UniversalStorageBridge {
  private static readonly LAB_STORAGE_KEY = 'resindb_pro_my_lab_data';
  private static readonly OPEN_STORAGE_KEY = 'resindb_pro_open_market_data';

  public static getLabRecords(): MaterialRecord[] {
    try {
      const data = localStorage.getItem(this.LAB_STORAGE_KEY);
      const records: MaterialRecord[] = data ? JSON.parse(data) : LAB_RECORDS;
      const cleaned = PolymerDataValidator.cleanBatch(records);
      localStorage.setItem(this.LAB_STORAGE_KEY, JSON.stringify(cleaned));
      return cleaned;
    } catch (error) {
      console.error('Failed to read lab records from storage:', error);
      return PolymerDataValidator.cleanBatch(LAB_RECORDS);
    }
  }

  public static saveLabRecord(record: MaterialRecord): void {
    const validated = PolymerDataValidator.validateAndClean(record);
    if (!validated) throw new Error('INVALID_MATERIAL_RECORD');
    const records = this.getLabRecords();
    const index = records.findIndex((candidate) => candidate.id === validated.id);
    if (index >= 0) records[index] = validated;
    else records.push(validated);
    localStorage.setItem(this.LAB_STORAGE_KEY, JSON.stringify(records));
  }

  public static deleteLabRecord(id: string): void {
    try {
      const records = this.getLabRecords();
      localStorage.setItem(
        this.LAB_STORAGE_KEY,
        JSON.stringify(records.filter((record) => record.id !== id)),
      );
    } catch (error) {
      console.error('Failed to delete lab record:', error);
    }
  }

  public static getOpenMarketRecords(): MaterialRecord[] {
    try {
      const data = localStorage.getItem(this.OPEN_STORAGE_KEY);
      let records: MaterialRecord[];
      if (data) {
        records = JSON.parse(data);
      } else {
        const merged: MaterialRecord[] = [];
        const seen = new Set<string>();
        for (const sourceRecord of OPEN_MARKET_RECORDS) {
          const key = normalizedRecordKey(sourceRecord);
          if (!seen.has(key)) {
            merged.push(sourceRecord);
            seen.add(key);
          }
        }
        for (const catalogRecord of PRODUCT_CATALOG.map((product) =>
          this.productToRecord(product, 'open_market'),
        )) {
          const key = normalizedRecordKey(catalogRecord);
          if (!seen.has(key)) {
            merged.push(catalogRecord);
            seen.add(key);
          }
        }
        records = merged;
      }
      const cleaned = PolymerDataValidator.cleanBatch(records);
      localStorage.setItem(this.OPEN_STORAGE_KEY, JSON.stringify(cleaned));
      return cleaned;
    } catch (error) {
      console.error('Failed to read open market records from storage:', error);
      return PolymerDataValidator.cleanBatch(OPEN_MARKET_RECORDS);
    }
  }

  public static saveOpenMarketRecord(record: MaterialRecord): void {
    const validated = PolymerDataValidator.validateAndClean(record);
    if (!validated) throw new Error('INVALID_MATERIAL_RECORD');
    const records = this.getOpenMarketRecords();
    const key = normalizedRecordKey(validated);
    const index = records.findIndex((candidate) =>
      candidate.id === validated.id || normalizedRecordKey(candidate) === key,
    );
    if (index >= 0) records[index] = validated;
    else records.push(validated);
    localStorage.setItem(this.OPEN_STORAGE_KEY, JSON.stringify(records));
  }

  public static findOpenMarketGrade(category: string, grade: string): MaterialRecord | null {
    const normalizedGrade = grade.toLowerCase().trim();
    if (!normalizedGrade) return null;
    const list = this.getOpenMarketRecords();
    const normalizedCategory = category.toLowerCase().trim();
    if (normalizedCategory) {
      const exactCategoryMatch = list.find(
        (record) =>
          record.grade.toLowerCase() === normalizedGrade &&
          record.category.toLowerCase() === normalizedCategory,
      );
      if (exactCategoryMatch) return exactCategoryMatch;
    }
    const exactGradeMatch = list.find((record) => record.grade.toLowerCase() === normalizedGrade);
    if (exactGradeMatch) return exactGradeMatch;
    return list.find((record) => {
      const candidate = record.grade.toLowerCase();
      return candidate.includes(normalizedGrade) || normalizedGrade.includes(candidate);
    }) ?? null;
  }

  public static recordToProduct(record: MaterialRecord): Product {
    const governed = PolymerDataValidator.validateAndClean(record) ?? record;
    const timestamp = Number.isFinite(governed.timestamp) ? governed.timestamp : Date.now();
    const date = new Date(timestamp).toISOString().split('T')[0];
    const properties: Record<string, PropertyValue> = {};
    const specs = governed.properties;
    if (specs.density) properties['密度'] = materialToProductProperty(specs.density);
    if (specs.mfr) properties['熔体质量流动速率'] = materialToProductProperty(specs.mfr);
    if (specs.tensileYield) properties['拉伸屈服应力'] = materialToProductProperty(specs.tensileYield);
    if (specs.flexuralModulus) properties['弯曲模量'] = materialToProductProperty(specs.flexuralModulus);
    if (specs.izodImpact) properties['悬臂梁缺口冲击强度'] = materialToProductProperty(specs.izodImpact);
    return {
      id: governed.id,
      gradeName: governed.grade,
      manufacturer: governed.manufacturer,
      manufacturerId: governed.source === 'my_lab' ? 'm-exp-lab' : 'm-open-market',
      categoryIds: [categoryIdFromText(governed.category)],
      properties,
      createdAt: date,
      updatedAt: date,
      isExperimental: governed.source === 'my_lab',
      governance: conservativeGovernance(governed),
    };
  }

  public static productToRecord(
    product: Product,
    defaultSource: 'open_market' | 'my_lab' = 'open_market',
  ): MaterialRecord {
    const props = product.properties ?? {};
    const density = props['密度'] || props.Density;
    const mfr = props['熔体质量流动速率'] || props.MFR;
    const tensile = props['拉伸屈服应力'] || props.Tensile;
    const modulus = props['弯曲模量'] || props.Modulus;
    const impact = props['悬臂梁缺口冲击强度'] || props['简支梁缺口冲击强度'] || props['Izod Impact'];
    const specs: MaterialPhysicsSpecs = {};
    if (density) specs.density = productToMaterialProperty(density);
    if (mfr) specs.mfr = productToMaterialProperty(mfr);
    if (tensile) specs.tensileYield = productToMaterialProperty(tensile);
    if (modulus) specs.flexuralModulus = productToMaterialProperty(modulus);
    if (impact) specs.izodImpact = productToMaterialProperty(impact);

    const createdTimestamp = product.createdAt ? Date.parse(product.createdAt) : Number.NaN;
    const source = product.isExperimental ? 'my_lab' : defaultSource;
    return {
      id: product.id,
      source,
      category: categoryNameFromId(product.categoryIds?.[0] || 'root_plastic'),
      grade: product.gradeName,
      manufacturer: product.manufacturer,
      properties: specs,
      timestamp: Number.isFinite(createdTimestamp) ? createdTimestamp : Date.now(),
      governance: product.governance
        ? { ...product.governance, provenanceRefs: [...product.governance.provenanceRefs] }
        : {
            sourceType: 'UNKNOWN',
            recordStatus: 'UNKNOWN',
            confidentiality: 'UNKNOWN',
            license: 'UNSPECIFIED',
            provenanceRefs: [],
          },
    };
  }
}
