import { createHash } from 'node:crypto';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const dataRoot = path.join(root, 'data');
const resinDir = path.join(dataRoot, 'resins');
const files = (await readdir(resinDir)).filter((file) => file.endsWith('.json') && file !== 'manifest.json').sort();
const assets = [];
for (const file of files) {
  const raw = await readFile(path.join(resinDir, file));
  const document = JSON.parse(raw.toString('utf8'));
  const payload = document.data;
  const recordCount = Array.isArray(payload) ? payload.length : payload && Array.isArray(payload.nodes) ? payload.nodes.length : payload && typeof payload === 'object' ? Object.keys(payload).length : null;
  assets.push({ file, dataKind: document.dataKind, recordStatus: document.recordStatus, recordCount, bytes: raw.byteLength, sha256: createHash('sha256').update(raw).digest('hex') });
}
const resinManifest = { schemaVersion:'1.0.0', dataKind:'resin-data-manifest', sourceType:'generated-index', recordStatus:'reference', updatedAt:'2026-07-28', data:{ basePath:'/data/resins', assets } };
await writeFile(path.join(resinDir, 'manifest.json'), `${JSON.stringify(resinManifest, null, 2)}\n`);
const governed = [];
for (const relative of ['version.json','metadata.json','schemas/resin-data-document.schema.json','schemas/resin-product.schema.json','resins/manifest.json', ...assets.map(({file}) => `resins/${file}`)]) {
  const raw = await readFile(path.join(dataRoot, relative));
  governed.push({ file: relative, bytes: raw.byteLength, sha256: createHash('sha256').update(raw).digest('hex') });
}
const rootManifest = { schemaVersion:'1.0.0', dataKind:'governed-data-manifest', sourceType:'generated-index', recordStatus:'reference', updatedAt:'2026-07-28', data:{ release:'3.2.0', assets:governed } };
await writeFile(path.join(dataRoot, 'manifest.json'), `${JSON.stringify(rootManifest, null, 2)}\n`);
console.log(`Generated governed manifest for ${governed.length} files and ${assets.length} resin documents.`);
