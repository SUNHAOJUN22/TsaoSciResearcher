export const SEEDED_RANDOM_ALGORITHM = 'xoshiro128**';
export const SEEDED_RANDOM_ALGORITHM_VERSION = '1.0.0';
export const SEEDED_RANDOM_ALGORITHM_ID = `${SEEDED_RANDOM_ALGORITHM}-${SEEDED_RANDOM_ALGORITHM_VERSION}`;

export type RandomSeed = string | number;

export interface SeededRandom {
  readonly seed: string;
  readonly algorithm: typeof SEEDED_RANDOM_ALGORITHM;
  readonly algorithmVersion: typeof SEEDED_RANDOM_ALGORITHM_VERSION;
  nextUint32(): number;
  next(): number;
  nextOpen(): number;
  normal(mean?: number, standardDeviation?: number): number;
}

function stableSerialize(value: unknown, seen: WeakSet<object>): string {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (Number.isNaN(value)) return '"NaN"';
    if (value === Infinity) return '"Infinity"';
    if (value === -Infinity) return '"-Infinity"';
    if (Object.is(value, -0)) return '0';
    return String(value);
  }
  if (typeof value === 'bigint') return `"${value.toString()}n"`;
  if (typeof value === 'undefined') return '"undefined"';
  if (ArrayBuffer.isView(value)) {
    return `[${Array.from(value as unknown as ArrayLike<number>).map((item) => stableSerialize(item, seen)).join(',')}]`;
  }
  if (value instanceof ArrayBuffer) {
    return `[${Array.from(new Uint8Array(value)).join(',')}]`;
  }
  if (Array.isArray(value)) {
    if (seen.has(value)) throw new TypeError('Cannot derive a seed from cyclic data');
    seen.add(value);
    const serialized = `[${value.map((item) => stableSerialize(item, seen)).join(',')}]`;
    seen.delete(value);
    return serialized;
  }
  if (typeof value === 'object') {
    if (seen.has(value)) throw new TypeError('Cannot derive a seed from cyclic data');
    seen.add(value);
    const record = value as Record<string, unknown>;
    const serialized = `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stableSerialize(record[key], seen)}`).join(',')}}`;
    seen.delete(value);
    return serialized;
  }
  return JSON.stringify(String(value));
}

function fnv1a32(text: string): number {
  let hash = 0x811c9dc5;
  for (let index = 0; index < text.length; index++) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

function createStateGenerator(seed: string): () => number {
  let state = 1779033703 ^ seed.length;
  for (let index = 0; index < seed.length; index++) {
    state = Math.imul(state ^ seed.charCodeAt(index), 3432918353);
    state = (state << 13) | (state >>> 19);
  }
  return () => {
    state = Math.imul(state ^ (state >>> 16), 2246822507);
    state = Math.imul(state ^ (state >>> 13), 3266489909);
    return (state ^= state >>> 16) >>> 0;
  };
}

function rotateLeft(value: number, shift: number): number {
  return ((value << shift) | (value >>> (32 - shift))) >>> 0;
}

export function normalizeRandomSeed(seed: RandomSeed): string {
  if (typeof seed === 'number') {
    if (!Number.isFinite(seed)) throw new TypeError('Random seed must be finite');
    return Object.is(seed, -0) ? '0' : String(seed);
  }
  const normalized = seed.trim();
  if (!normalized) throw new TypeError('Random seed must be a non-empty string or finite number');
  return normalized;
}

export function deriveRandomSeed(namespace: string, value: unknown): string {
  const normalizedNamespace = namespace.trim();
  if (!normalizedNamespace) throw new TypeError('Seed namespace must be non-empty');
  const serialized = stableSerialize(value, new WeakSet<object>());
  return `resindb:${normalizedNamespace}:fnv1a32-${fnv1a32(serialized).toString(16).padStart(8, '0')}`;
}

export function createSeededRandom(seed: RandomSeed): SeededRandom {
  const normalizedSeed = normalizeRandomSeed(seed);
  const generateState = createStateGenerator(normalizedSeed);
  let state0 = generateState();
  let state1 = generateState();
  let state2 = generateState();
  let state3 = generateState();
  if ((state0 | state1 | state2 | state3) === 0) state0 = 1;
  let spareNormal: number | undefined;

  const nextUint32 = () => {
    const result = Math.imul(rotateLeft(Math.imul(state1, 5) >>> 0, 7), 9) >>> 0;
    const temporary = (state1 << 9) >>> 0;
    state2 = (state2 ^ state0) >>> 0;
    state3 = (state3 ^ state1) >>> 0;
    state1 = (state1 ^ state2) >>> 0;
    state0 = (state0 ^ state3) >>> 0;
    state2 = (state2 ^ temporary) >>> 0;
    state3 = rotateLeft(state3, 11);
    return result;
  };

  const next = () => nextUint32() / 0x100000000;
  const nextOpen = () => (nextUint32() + 0.5) / 0x100000000;
  const normal = (mean = 0, standardDeviation = 1) => {
    if (!Number.isFinite(mean)) throw new TypeError('Normal mean must be finite');
    if (!Number.isFinite(standardDeviation) || standardDeviation < 0) {
      throw new TypeError('Normal standard deviation must be a non-negative finite number');
    }
    if (standardDeviation === 0) return mean;
    if (spareNormal !== undefined) {
      const value = spareNormal;
      spareNormal = undefined;
      return mean + value * standardDeviation;
    }
    const radius = Math.sqrt(-2 * Math.log(nextOpen()));
    const angle = 2 * Math.PI * nextOpen();
    spareNormal = radius * Math.sin(angle);
    return mean + radius * Math.cos(angle) * standardDeviation;
  };

  return {
    seed: normalizedSeed,
    algorithm: SEEDED_RANDOM_ALGORITHM,
    algorithmVersion: SEEDED_RANDOM_ALGORITHM_VERSION,
    nextUint32,
    next,
    nextOpen,
    normal,
  };
}

export interface NumericBounds {
  min?: number;
  max?: number;
}

export function sampleNormalWithinBounds(
  random: SeededRandom,
  mean: number,
  standardDeviation: number,
  bounds?: NumericBounds,
  maximumAttempts = 10_000,
): number {
  if (!Number.isInteger(maximumAttempts) || maximumAttempts < 1) {
    throw new RangeError('maximumAttempts must be a positive integer');
  }
  const minimum = bounds?.min ?? -Infinity;
  const maximum = bounds?.max ?? Infinity;
  if (Number.isNaN(minimum) || Number.isNaN(maximum) || minimum >= maximum) {
    throw new RangeError('Normal sampling bounds must satisfy min < max');
  }
  if (mean < minimum || mean > maximum) {
    throw new RangeError('Normal sampling mean must lie within the requested bounds');
  }
  if (standardDeviation === 0) return mean;
  for (let attempt = 0; attempt < maximumAttempts; attempt++) {
    const sample = random.normal(mean, standardDeviation);
    if (sample >= minimum && sample <= maximum) return sample;
  }
  throw new Error(`Unable to sample within bounds after ${maximumAttempts} attempts`);
}
