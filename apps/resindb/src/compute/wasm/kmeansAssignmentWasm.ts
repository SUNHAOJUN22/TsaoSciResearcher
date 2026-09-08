export const KMEANS_ASSIGNMENT_WASM_BINARY_VERSION = 'kmeans-assignment-wasm-f64-1.0.0';

const WASM_PAGE_BYTES = 65_536;

const KMEANS_ASSIGNMENT_WASM_BYTES = new Uint8Array([
  0, 97, 115, 109, 1, 0, 0, 0, 1, 13, 1, 96, 8, 127, 127, 127, 127, 127, 127, 127,
  127, 1, 127, 3, 2, 1, 0, 4, 5, 1, 112, 1, 1, 1, 5, 5, 1, 1, 2, 128,
  32, 6, 15, 2, 127, 1, 65, 128, 136, 4, 11, 127, 0, 65, 128, 136, 4, 11, 7, 44,
  3, 6, 109, 101, 109, 111, 114, 121, 2, 0, 17, 97, 115, 115, 105, 103, 110, 95, 97, 99,
  99, 117, 109, 117, 108, 97, 116, 101, 0, 0, 11, 95, 95, 104, 101, 97, 112, 95, 98, 97,
  115, 101, 3, 1, 10, 190, 3, 1, 187, 3, 4, 7, 127, 1, 124, 3, 127, 2, 124, 65,
  0, 33, 8, 32, 5, 65, 0, 32, 5, 65, 0, 74, 27, 33, 9, 32, 7, 65, 1, 32,
  7, 65, 1, 74, 27, 33, 10, 32, 6, 65, 0, 32, 6, 65, 0, 74, 27, 33, 11, 32,
  1, 32, 6, 65, 3, 116, 34, 12, 106, 33, 13, 65, 0, 33, 14, 2, 64, 3, 64, 32,
  8, 32, 9, 70, 13, 1, 68, 0, 0, 0, 0, 0, 0, 0, 0, 33, 15, 32, 1, 33,
  7, 32, 0, 33, 16, 32, 11, 33, 5, 3, 64, 2, 64, 32, 5, 13, 0, 65, 0, 33,
  17, 65, 1, 33, 18, 32, 13, 33, 16, 2, 64, 3, 64, 2, 64, 32, 18, 32, 10, 71,
  13, 0, 2, 64, 32, 2, 32, 8, 65, 2, 116, 106, 34, 5, 40, 2, 0, 32, 17, 70,
  13, 0, 32, 5, 32, 17, 54, 2, 0, 32, 14, 65, 1, 106, 33, 14, 11, 32, 4, 32,
  17, 65, 2, 116, 106, 34, 5, 32, 5, 40, 2, 0, 65, 1, 106, 54, 2, 0, 32, 3,
  32, 17, 32, 6, 108, 65, 3, 116, 106, 33, 18, 65, 0, 33, 5, 32, 11, 33, 7, 12,
  2, 11, 68, 0, 0, 0, 0, 0, 0, 0, 0, 33, 19, 65, 0, 33, 5, 32, 11, 33,
  7, 3, 64, 2, 64, 32, 7, 13, 0, 32, 18, 32, 17, 32, 19, 32, 15, 99, 34, 5,
  27, 33, 17, 32, 19, 32, 15, 32, 5, 27, 33, 15, 32, 16, 32, 12, 106, 33, 16, 32,
  18, 65, 1, 106, 33, 18, 12, 2, 11, 32, 0, 32, 5, 106, 43, 3, 0, 32, 16, 32,
  5, 106, 43, 3, 0, 161, 34, 20, 32, 20, 162, 32, 19, 160, 33, 19, 32, 5, 65, 8,
  106, 33, 5, 32, 7, 65, 127, 106, 33, 7, 12, 0, 11, 11, 11, 2, 64, 3, 64, 32,
  7, 69, 13, 1, 32, 18, 32, 5, 106, 34, 16, 32, 0, 32, 5, 106, 43, 3, 0, 32,
  16, 43, 3, 0, 160, 57, 3, 0, 32, 5, 65, 8, 106, 33, 5, 32, 7, 65, 127, 106,
  33, 7, 12, 0, 11, 11, 32, 0, 32, 12, 106, 33, 0, 32, 8, 65, 1, 106, 33, 8,
  12, 2, 11, 32, 5, 65, 127, 106, 33, 5, 32, 16, 43, 3, 0, 32, 7, 43, 3, 0,
  161, 34, 19, 32, 19, 162, 32, 15, 160, 33, 15, 32, 7, 65, 8, 106, 33, 7, 32, 16,
  65, 8, 106, 33, 16, 12, 0, 11, 11, 11, 32, 14, 11,
]);

interface KMeansAssignmentWasmExports extends WebAssembly.Exports {
  memory: WebAssembly.Memory;
  assign_accumulate(
    matrixPointer: number,
    centroidPointer: number,
    assignmentPointer: number,
    sumPointer: number,
    countPointer: number,
    samples: number,
    dimensions: number,
    clusters: number,
  ): number;
  __heap_base: WebAssembly.Global;
}

export interface KMeansAssignmentWasmSession {
  readonly memoryBytes: number;
  assignAndAccumulate(
    centroids: Float64Array,
    clusterCount: number,
    assignments: Int32Array,
    sums: Float64Array,
    counts: Uint32Array,
  ): number;
}

function align(value: number, alignment: number): number {
  return Math.ceil(value / alignment) * alignment;
}

function ensureMemory(memory: WebAssembly.Memory, requiredBytes: number): void {
  const missingBytes = requiredBytes - memory.buffer.byteLength;
  if (missingBytes <= 0) return;
  memory.grow(Math.ceil(missingBytes / WASM_PAGE_BYTES));
}

function validatePositiveInteger(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 1) {
    throw new RangeError(`${name} must be a positive integer`);
  }
  return value;
}

export function supportsKMeansAssignmentWasm(
  webAssembly: typeof WebAssembly | undefined = typeof WebAssembly === 'undefined' ? undefined : WebAssembly,
): boolean {
  if (!webAssembly) return false;
  try {
    return webAssembly.validate(KMEANS_ASSIGNMENT_WASM_BYTES);
  } catch {
    return false;
  }
}

export function createKMeansAssignmentWasmSession(
  matrix: Float64Array,
  sampleCount: number,
  dimensions: number,
  maxClusters: number,
  webAssembly: typeof WebAssembly | undefined = typeof WebAssembly === 'undefined' ? undefined : WebAssembly,
): KMeansAssignmentWasmSession {
  const samples = validatePositiveInteger(sampleCount, 'sampleCount');
  const dimensionCount = validatePositiveInteger(dimensions, 'dimensions');
  const clusterCapacity = validatePositiveInteger(maxClusters, 'maxClusters');
  if (matrix.length !== samples * dimensionCount) {
    throw new RangeError('matrix length must equal sampleCount times dimensions');
  }
  if (!webAssembly || !supportsKMeansAssignmentWasm(webAssembly)) {
    throw new Error('FP64 K-Means WebAssembly kernel is unavailable');
  }

  const module = new webAssembly.Module(KMEANS_ASSIGNMENT_WASM_BYTES);
  const instance = new webAssembly.Instance(module, {});
  const exports = instance.exports as KMeansAssignmentWasmExports;
  const heapBase = Number(exports.__heap_base.value);
  if (!Number.isInteger(heapBase) || heapBase < 0) {
    throw new Error('WebAssembly heap base is invalid');
  }

  let pointer = align(heapBase, Float64Array.BYTES_PER_ELEMENT);
  const matrixPointer = pointer;
  pointer += matrix.byteLength;
  pointer = align(pointer, Float64Array.BYTES_PER_ELEMENT);
  const centroidPointer = pointer;
  pointer += clusterCapacity * dimensionCount * Float64Array.BYTES_PER_ELEMENT;
  pointer = align(pointer, Int32Array.BYTES_PER_ELEMENT);
  const assignmentPointer = pointer;
  pointer += samples * Int32Array.BYTES_PER_ELEMENT;
  pointer = align(pointer, Float64Array.BYTES_PER_ELEMENT);
  const sumPointer = pointer;
  pointer += clusterCapacity * dimensionCount * Float64Array.BYTES_PER_ELEMENT;
  pointer = align(pointer, Uint32Array.BYTES_PER_ELEMENT);
  const countPointer = pointer;
  pointer += clusterCapacity * Uint32Array.BYTES_PER_ELEMENT;

  ensureMemory(exports.memory, pointer);
  new Float64Array(exports.memory.buffer, matrixPointer, matrix.length).set(matrix);

  return {
    get memoryBytes() {
      return exports.memory.buffer.byteLength;
    },
    assignAndAccumulate(centroids, clusterCount, assignments, sums, counts) {
      const clusters = validatePositiveInteger(clusterCount, 'clusterCount');
      if (clusters > clusterCapacity) throw new RangeError('clusterCount exceeds session capacity');
      if (centroids.length !== clusters * dimensionCount) {
        throw new RangeError('centroids length must equal clusterCount times dimensions');
      }
      if (assignments.length !== samples) {
        throw new RangeError('assignments length must equal sampleCount');
      }
      if (sums.length !== clusters * dimensionCount) {
        throw new RangeError('sums length must equal clusterCount times dimensions');
      }
      if (counts.length !== clusters) {
        throw new RangeError('counts length must equal clusterCount');
      }

      const centroidView = new Float64Array(
        exports.memory.buffer,
        centroidPointer,
        centroids.length,
      );
      const assignmentView = new Int32Array(
        exports.memory.buffer,
        assignmentPointer,
        assignments.length,
      );
      const sumView = new Float64Array(exports.memory.buffer, sumPointer, sums.length);
      const countView = new Uint32Array(exports.memory.buffer, countPointer, counts.length);
      centroidView.set(centroids);
      assignmentView.set(assignments);
      sumView.fill(0);
      countView.fill(0);

      const changed = exports.assign_accumulate(
        matrixPointer,
        centroidPointer,
        assignmentPointer,
        sumPointer,
        countPointer,
        samples,
        dimensionCount,
        clusters,
      );
      if (!Number.isInteger(changed) || changed < 0 || changed > samples) {
        throw new Error('WebAssembly assignment kernel returned an invalid change count');
      }

      assignments.set(assignmentView);
      sums.set(sumView);
      counts.set(countView);
      let assignedSamples = 0;
      for (const count of counts) assignedSamples += count;
      if (assignedSamples !== samples) {
        throw new Error('WebAssembly assignment kernel returned inconsistent cluster counts');
      }
      for (const assignment of assignments) {
        if (assignment < 0 || assignment >= clusters) {
          throw new Error('WebAssembly assignment kernel returned an invalid cluster index');
        }
      }
      for (const value of sums) {
        if (!Number.isFinite(value)) {
          throw new Error('WebAssembly assignment kernel returned a non-finite centroid sum');
        }
      }
      return changed;
    },
  };
}
