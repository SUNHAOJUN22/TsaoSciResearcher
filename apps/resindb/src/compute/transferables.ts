export interface CollectTransferablesOptions {
  maxDepth?: number;
}

function transferableFromValue(value: unknown): Transferable | null {
  if (value instanceof ArrayBuffer) return value;
  if (ArrayBuffer.isView(value) && value.buffer instanceof ArrayBuffer) return value.buffer;

  const constructors: Array<new (...args: never[]) => object> = [];
  if (typeof MessagePort !== 'undefined') constructors.push(MessagePort);
  if (typeof ImageBitmap !== 'undefined') constructors.push(ImageBitmap);
  if (typeof OffscreenCanvas !== 'undefined') constructors.push(OffscreenCanvas);

  for (const Constructor of constructors) {
    if (value instanceof Constructor) return value as Transferable;
  }
  return null;
}

export function collectTransferables(
  value: unknown,
  options: CollectTransferablesOptions = {},
): Transferable[] {
  const maxDepth = options.maxDepth ?? 6;
  if (!Number.isInteger(maxDepth) || maxDepth < 0) {
    throw new RangeError('maxDepth must be a non-negative integer');
  }

  const transferables = new Set<Transferable>();
  const visited = new WeakSet<object>();

  const visit = (candidate: unknown, depth: number): void => {
    const transferable = transferableFromValue(candidate);
    if (transferable) {
      transferables.add(transferable);
      return;
    }
    if (depth >= maxDepth || !candidate || typeof candidate !== 'object') return;
    if (visited.has(candidate)) return;
    visited.add(candidate);

    if (Array.isArray(candidate)) {
      for (const item of candidate) visit(item, depth + 1);
      return;
    }
    for (const item of Object.values(candidate as Record<string, unknown>)) {
      visit(item, depth + 1);
    }
  };

  visit(value, 0);
  return [...transferables];
}
