import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const dataRoot = path.join(root, 'data');
const resinDir = path.join(dataRoot, 'resins');
const ENVELOPE_KEYS = ['data', 'dataKind', 'recordStatus', 'schemaVersion', 'sourceType', 'updatedAt'];
const RECORD_STATUSES = new Set(['demo', 'reference', 'measured', 'imported']);

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};
const isRecord = (value) => typeof value === 'object' && value !== null && !Array.isArray(value);
const isNonEmptyString = (value) => typeof value === 'string' && value.trim().length > 0;
const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value);
const readJson = async (file) => {
  const raw = await readFile(file);
  return { raw, json: JSON.parse(raw.toString('utf8')) };
};

function isIsoDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year
    && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day;
}

function uniqueIds(items, label) {
  assert(Array.isArray(items), `${label} must be an array`);
  const seen = new Set();
  for (const item of items) {
    assert(isRecord(item) && isNonEmptyString(item.id), `${label} contains invalid id`);
    assert(!seen.has(item.id), `Duplicate ${label} id: ${item.id}`);
    seen.add(item.id);
  }
  return seen;
}

function flatten(nodes, stack = new Set(), out = []) {
  assert(Array.isArray(nodes), 'Taxonomy must be an array');
  for (const node of nodes) {
    assert(isRecord(node) && isNonEmptyString(node.id) && isNonEmptyString(node.name), 'Invalid taxonomy node');
    assert(!stack.has(node.id), `Taxonomy cycle: ${node.id}`);
    stack.add(node.id);
    out.push(node);
    if (node.children !== undefined) flatten(node.children, stack, out);
    stack.delete(node.id);
  }
  return out;
}

function envelope(document, kind, file) {
  assert(isRecord(document), `${file} must be object`);
  assert(
    JSON.stringify(Object.keys(document).sort()) === JSON.stringify(ENVELOPE_KEYS),
    `${file} must use the canonical six-field data envelope`,
  );
  assert(document.schemaVersion === '1.0.0', `${file} schemaVersion`);
  assert(document.dataKind === kind, `${file} dataKind`);
  assert(isNonEmptyString(document.sourceType), `${file} sourceType`);
  assert(RECORD_STATUSES.has(document.recordStatus), `${file} recordStatus`);
  assert(isIsoDate(document.updatedAt), `${file} updatedAt`);
  assert('data' in document, `${file} data`);
}

function validateOptionalString(record, key, label) {
  if (record[key] !== undefined) assert(typeof record[key] === 'string', `${label}.${key} must be a string`);
}

function validateOptionalFiniteNumber(record, key, label) {
  if (record[key] !== undefined) assert(isFiniteNumber(record[key]), `${label}.${key} must be finite`);
}

function validatePropertyValue(value, label) {
  assert(isRecord(value), `${label} must be an object`);
  const keys = new Set([
    'value', 'unit', 'standard', 'temperature', 'referenceId', 'instrument', 'sourceUrl',
    'annotation', 'mean', 'stdDev', 'min', 'max', 'count', 'temp', 'load',
  ]);
  for (const key of Object.keys(value)) assert(keys.has(key), `${label} contains unsupported field ${key}`);
  assert('value' in value, `${label}.value is required`);
  assert(
    typeof value.value === 'string' || isFiniteNumber(value.value),
    `${label}.value must be string or finite number`,
  );
  for (const key of ['unit', 'standard', 'referenceId', 'instrument', 'sourceUrl', 'annotation', 'temp', 'load']) {
    validateOptionalString(value, key, label);
  }
  if (value.temperature !== undefined) {
    assert(
      typeof value.temperature === 'string' || isFiniteNumber(value.temperature),
      `${label}.temperature must be string or finite number`,
    );
  }
  for (const key of ['mean', 'stdDev', 'min', 'max']) validateOptionalFiniteNumber(value, key, label);
  if (value.count !== undefined) {
    assert(Number.isInteger(value.count) && value.count >= 0, `${label}.count must be a non-negative integer`);
  }
}

function validateProduct(product, manufacturerIds, categoryIds) {
  const allowed = new Set([
    'id', 'gradeName', 'manufacturerId', 'manufacturer', 'categoryIds', 'properties',
    'createdAt', 'updatedAt', 'isExperimental', 'tags', 'priority',
  ]);
  for (const key of Object.keys(product)) assert(allowed.has(key), `${product.id} contains unsupported field ${key}`);
  assert(isNonEmptyString(product.id), 'Product id is required');
  assert(isNonEmptyString(product.gradeName), `${product.id} gradeName`);
  assert(isNonEmptyString(product.manufacturerId), `${product.id} manufacturerId`);
  assert(isNonEmptyString(product.manufacturer), `${product.id} manufacturer`);
  assert(manufacturerIds.has(product.manufacturerId), `${product.id} manufacturer`);
  assert(Array.isArray(product.categoryIds) && product.categoryIds.length > 0, `${product.id} categoryIds`);
  assert(new Set(product.categoryIds).size === product.categoryIds.length, `${product.id} duplicate categoryIds`);
  for (const id of product.categoryIds) {
    assert(isNonEmptyString(id) && categoryIds.has(id), `${product.id} category ${id}`);
  }
  assert(isIsoDate(product.createdAt), `${product.id} createdAt`);
  assert(isIsoDate(product.updatedAt), `${product.id} updatedAt`);
  assert(isRecord(product.properties) && Object.keys(product.properties).length >= 1, `${product.id} properties`);
  for (const [name, value] of Object.entries(product.properties)) {
    assert(name.trim().length > 0, `${product.id} contains blank property name`);
    validatePropertyValue(value, `${product.id}.properties.${name}`);
  }
  if (product.isExperimental !== undefined) assert(typeof product.isExperimental === 'boolean', `${product.id} isExperimental`);
  if (product.tags !== undefined) {
    assert(Array.isArray(product.tags) && product.tags.every(isNonEmptyString), `${product.id} tags`);
    assert(new Set(product.tags).size === product.tags.length, `${product.id} duplicate tags`);
  }
  if (product.priority !== undefined) assert(isFiniteNumber(product.priority), `${product.id} priority`);
}

const { json: documentSchema } = await readJson(path.join(dataRoot, 'schemas/resin-data-document.schema.json'));
assert(documentSchema.additionalProperties === false, 'Data envelope schema must reject unknown top-level fields');
assert(documentSchema.properties?.schemaVersion?.const === '1.0.0', 'Data envelope schema version drift');

const { json: productSchema } = await readJson(path.join(dataRoot, 'schemas/resin-product.schema.json'));
assert(productSchema.additionalProperties === false, 'Product schema must reject unknown top-level fields');
assert(productSchema.$defs?.propertyValue?.additionalProperties === false, 'Property schema must reject unknown fields');
assert(
  JSON.stringify(productSchema.$defs?.propertyValue?.properties?.value?.type) === JSON.stringify(['string', 'number']),
  'Product schema value type must match TypeScript string | number contract',
);

const { json: version } = await readJson(path.join(dataRoot, 'version.json'));
envelope(version, 'resin-data-version', 'version.json');
assert(version.data.release === '3.2.0', 'Data release must be 3.2.0');

const { json: metadata } = await readJson(path.join(dataRoot, 'metadata.json'));
envelope(metadata, 'resin-data-metadata', 'metadata.json');

const { json: rootManifest } = await readJson(path.join(dataRoot, 'manifest.json'));
envelope(rootManifest, 'governed-data-manifest', 'manifest.json');
for (const entry of rootManifest.data.assets) {
  const raw = await readFile(path.join(dataRoot, entry.file));
  assert(raw.byteLength === entry.bytes, `${entry.file} bytes`);
  assert(createHash('sha256').update(raw).digest('hex') === entry.sha256, `${entry.file} SHA-256`);
}

const { json: manifest } = await readJson(path.join(resinDir, 'manifest.json'));
envelope(manifest, 'resin-data-manifest', 'resins/manifest.json');
assert(manifest.data.basePath === '/data/resins', 'Runtime base path');

const documents = new Map();
for (const entry of manifest.data.assets) {
  const { raw, json } = await readJson(path.join(resinDir, entry.file));
  assert(raw.byteLength === entry.bytes, `${entry.file} bytes`);
  assert(createHash('sha256').update(raw).digest('hex') === entry.sha256, `${entry.file} SHA-256`);
  envelope(json, entry.dataKind, entry.file);
  documents.set(entry.dataKind, json.data);
}

const categories = flatten(documents.get('resin-taxonomy'));
const categoryIds = uniqueIds(categories, 'category');
const manufacturerIds = uniqueIds(documents.get('resin-manufacturers'), 'manufacturer');
uniqueIds(documents.get('resin-references'), 'reference');

const products = documents.get('resin-seed-products');
uniqueIds(products, 'product');
for (const product of products) validateProduct(product, manufacturerIds, categoryIds);

uniqueIds(documents.get('laboratory-material-records'), 'laboratory record');
uniqueIds(documents.get('market-material-records'), 'market record');

const network = documents.get('resin-reaction-network');
const nodeIds = uniqueIds(network.nodes, 'network node');
for (const link of network.links) {
  assert(nodeIds.has(String(link.source)), `Unknown source ${link.source}`);
  assert(nodeIds.has(String(link.target)), `Unknown target ${link.target}`);
}
for (const alias of documents.get('resin-category-aliases')) {
  assert(categoryIds.has(alias.categoryId), `Unknown alias category ${alias.categoryId}`);
}

console.log(
  `Data validation passed: canonical JSON envelope, ${rootManifest.data.assets.length} governed files, `
  + `${manifest.data.assets.length} resin assets, ${categories.length} categories, ${products.length} products, `
  + `${network.nodes.length} network nodes.`,
);
