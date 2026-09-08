import { describe, expect, it } from 'vitest';
import {
  CATEGORY_TREE, MANUFACTURERS, REFERENCES, PRODUCT_CATALOG,
  LAB_RECORDS, OPEN_MARKET_RECORDS, RESIN_NETWORK,
  CATEGORY_ALIASES, categoryIdFromText, categoryNameFromId,
  validateDocument, loadResinDataCatalog,
} from '@/data/resinData';

type TaxonomyNode = { id: string; children?: TaxonomyNode[] };
const flatten = (nodes: TaxonomyNode[]): TaxonomyNode[] =>
  nodes.flatMap((node) => [node, ...flatten(node.children ?? [])]);

describe('versioned resin data assets',()=>{
  it('loads a non-empty, acyclic taxonomy with unique ids',()=>{
    const all=flatten(CATEGORY_TREE); expect(all.length).toBeGreaterThan(20);
    expect(new Set(all.map((x)=>x.id)).size).toBe(all.length);
  });
  it('loads directories and deterministic product records',()=>{
    expect(MANUFACTURERS.length).toBeGreaterThan(10);expect(REFERENCES.length).toBeGreaterThan(5);expect(PRODUCT_CATALOG.length).toBeGreaterThan(5);
    expect(new Set(PRODUCT_CATALOG.map((x)=>x.id)).size).toBe(PRODUCT_CATALOG.length);
  });
  it('loads lab and market demo records',()=>{expect(LAB_RECORDS.length).toBeGreaterThan(0);expect(OPEN_MARKET_RECORDS.length).toBeGreaterThan(0);});
  it('loads a clickable network dataset',()=>{expect(RESIN_NETWORK.nodes.length).toBeGreaterThan(10);expect(RESIN_NETWORK.links.length).toBeGreaterThan(10);});
  it('keeps category aliases outside UI code',()=>{expect(CATEGORY_ALIASES.length).toBeGreaterThan(8);expect(categoryIdFromText('random copolymer PP')).toBe('sub_pp_rand');expect(categoryNameFromId('cat_abs')).toBe('ABS');});
  it('does not classify longer acronyms through short substring aliases',()=>{
    expect(categoryIdFromText('TPE elastomer')).not.toBe('cat_pe');
    expect(categoryIdFromText('PPR random copolymer')).not.toBe('cat_pp');
    expect(categoryIdFromText('PE resin')).toBe('cat_pe');
  });

  it('keeps the governed data release and root manifest aligned', async()=>{
    const { readFile } = await import('node:fs/promises');
    const version = JSON.parse(await readFile('data/version.json','utf8'));
    const manifest = JSON.parse(await readFile('data/manifest.json','utf8'));
    expect(version.data.release).toBe('3.2.0');
    expect(manifest.data.release).toBe('3.2.0');
    expect((manifest.data.assets as Array<{ file: string }>).some((entry) => entry.file === 'resins/manifest.json')).toBe(true);
  });
  it('reports a coherent deterministic fallback when runtime assets fail', async()=>{
    const failingFetch = (async()=>{ throw new Error('offline'); }) as typeof fetch;
    const result = await loadResinDataCatalog(failingFetch, '/data/resins');
    expect(result.status.usingFallback).toBe(true);
    expect(result.status.failures).toHaveLength(9);
    expect(result.catalog.categoryTree[0].id).toBe('root_plastic');
  });
  it('rejects an incompatible schema version',()=>{expect(()=>validateDocument({schemaVersion:'9',dataKind:'x',data:[]},'x',(x):x is unknown[]=>Array.isArray(x))).toThrow(/Invalid or unsupported/);});
});
