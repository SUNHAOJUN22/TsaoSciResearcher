/** tsao.c14n/1 typed binary64 identity. This is not RFC 8785 canonicalization. */
export function canonicalBytes(value: unknown): Uint8Array {
  const active = new Set<object>();
  let count = 0;
  const encoder = new TextEncoder();
  function compare(left: string, right: string): number {
    const a = encoder.encode(left); const b = encoder.encode(right);
    for (let i = 0; i < Math.min(a.length, b.length); i++) { if (a[i] !== b[i]) return a[i] - b[i]; }
    return a.length - b.length;
  }
  function typed(item: unknown, depth: number): unknown[] {
    count++;
    if (depth > 64 || count > 100_000) throw new Error('JSON structure exceeds its budget');
    if (item === null) return ['null'];
    if (typeof item === 'boolean') return ['bool', item];
    if (typeof item === 'string') {
      if (/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(item)) throw new Error('unpaired surrogate');
      return ['str', item];
    }
    if (typeof item === 'number') {
      if (!Number.isFinite(item)) throw new Error('number must be finite');
      const buffer = new ArrayBuffer(8);
      new DataView(buffer).setFloat64(0, item === 0 ? 0 : item, false);
      return ['number', [...new Uint8Array(buffer)].map((x) => x.toString(16).padStart(2, '0')).join('')];
    }
    if (typeof item !== 'object' || item === null) throw new Error('only JSON values are accepted');
    if (active.has(item)) throw new Error('cyclic object');
    active.add(item);
    let result: unknown[];
    if (Array.isArray(item)) result = ['array', item.map((child) => typed(child, depth + 1))];
    else {
      const record = item as Record<string, unknown>;
      result = ['object', Object.keys(record).sort(compare).map((key) => [key, typed(record[key], depth + 1)])];
    }
    active.delete(item);
    return result;
  }
  return encoder.encode(JSON.stringify(['tsao.c14n/1', typed(value, 0)]));
}
