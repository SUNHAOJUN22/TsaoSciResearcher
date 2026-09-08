#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { performance } from 'node:perf_hooks';

const root = path.resolve(import.meta.dirname, '..');
const artifacts = path.join(root, 'artifacts');
const policyPath = path.join(root, 'src', 'compute', 'kmeansBackendPolicyConfig.json');
const wasmSourcePath = path.join(root, 'src', 'compute', 'wasm', 'kmeansAssignmentWasm.ts');
const nativeSourcePath = path.join(root, 'native', 'wasm', 'kmeansAssignmentKernel.c');
const policy = JSON.parse(await readFile(policyPath, 'utf8'));
const modeArgumentIndex = process.argv.indexOf('--mode');
const mode = modeArgumentIndex >= 0 ? process.argv[modeArgumentIndex + 1] : 'full';
if (mode !== 'smoke' && mode !== 'full') {
  throw new TypeError('K-Means benchmark mode must be smoke or full');
}

const CASES = {
  smoke: [
    { id: 'small-64x4x3', samples: 64, dimensions: 4, clusters: 3, iterations: 200, warmups: 2, repeats: 5 },
    { id: 'medium-512x8x5', samples: 512, dimensions: 8, clusters: 5, iterations: 40, warmups: 2, repeats: 5 },
    { id: 'large-4096x12x8', samples: 4_096, dimensions: 12, clusters: 8, iterations: 5, warmups: 2, repeats: 5 },
  ],
  full: [
    { id: 'tiny-64x4x3', samples: 64, dimensions: 4, clusters: 3, iterations: 1_000, warmups: 3, repeats: 9 },
    { id: 'small-512x8x5', samples: 512, dimensions: 8, clusters: 5, iterations: 100, warmups: 3, repeats: 9 },
    { id: 'medium-4096x12x8', samples: 4_096, dimensions: 12, clusters: 8, iterations: 10, warmups: 3, repeats: 9 },
    { id: 'large-16384x16x10', samples: 16_384, dimensions: 16, clusters: 10, iterations: 3, warmups: 2, repeats: 9 },
    { id: 'xlarge-65536x16x10', samples: 65_536, dimensions: 16, clusters: 10, iterations: 1, warmups: 2, repeats: 7 },
  ],
};

const SIMD_PROBE_MODULE = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
  0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b,
  0x03, 0x02, 0x01, 0x00,
  0x0a, 0x08, 0x01, 0x06, 0x00, 0x41, 0x00, 0xfd, 0x0f, 0x0b,
]);

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function fnv1a(value) {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function repositorySha() {
  if (process.env.GITHUB_SHA) return process.env.GITHUB_SHA;
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
  } catch {
    return 'local-worktree';
  }
}

function extractWasmBytes(source) {
  const match = source.match(/KMEANS_ASSIGNMENT_WASM_BYTES\s*=\s*new Uint8Array\(\[([\s\S]*?)\]\);/);
  if (!match) throw new Error('Unable to locate embedded K-Means WASM bytes');
  const values = match[1]
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => Number(value));
  if (values.length < 8 || values.some((value) => !Number.isInteger(value) || value < 0 || value > 255)) {
    throw new Error('Embedded K-Means WASM byte list is invalid');
  }
  return new Uint8Array(values);
}

function align(value, alignment) {
  return Math.ceil(value / alignment) * alignment;
}

function ensureMemory(memory, requiredBytes) {
  const pageBytes = 65_536;
  const missingBytes = requiredBytes - memory.buffer.byteLength;
  if (missingBytes > 0) memory.grow(Math.ceil(missingBytes / pageBytes));
}

function createWasmHarness(bytes, matrix, samples, dimensions, maxClusters) {
  if (!WebAssembly.validate(bytes)) throw new Error('Embedded K-Means WASM binary is invalid');
  const module = new WebAssembly.Module(bytes);
  const instance = new WebAssembly.Instance(module, {});
  const exports = instance.exports;
  const heapBase = Number(exports.__heap_base.value);
  let pointer = align(heapBase, Float64Array.BYTES_PER_ELEMENT);
  const matrixPointer = pointer;
  pointer += matrix.byteLength;
  pointer = align(pointer, Float64Array.BYTES_PER_ELEMENT);
  const centroidPointer = pointer;
  pointer += maxClusters * dimensions * Float64Array.BYTES_PER_ELEMENT;
  pointer = align(pointer, Int32Array.BYTES_PER_ELEMENT);
  const assignmentPointer = pointer;
  pointer += samples * Int32Array.BYTES_PER_ELEMENT;
  pointer = align(pointer, Float64Array.BYTES_PER_ELEMENT);
  const sumPointer = pointer;
  pointer += maxClusters * dimensions * Float64Array.BYTES_PER_ELEMENT;
  pointer = align(pointer, Uint32Array.BYTES_PER_ELEMENT);
  const countPointer = pointer;
  pointer += maxClusters * Uint32Array.BYTES_PER_ELEMENT;
  ensureMemory(exports.memory, pointer);
  new Float64Array(exports.memory.buffer, matrixPointer, matrix.length).set(matrix);

  return {
    memoryBytes: exports.memory.buffer.byteLength,
    assign(centroids, clusters, assignments, sums, counts) {
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
        dimensions,
        clusters,
      );
      assignments.set(assignmentView);
      sums.set(sumView);
      counts.set(countView);
      return changed;
    },
  };
}

function assignTypeScript(matrix, samples, dimensions, centroids, clusters, assignments, sums, counts) {
  sums.fill(0);
  counts.fill(0);
  let changed = 0;
  for (let sample = 0; sample < samples; sample += 1) {
    const sampleOffset = sample * dimensions;
    let bestCluster = 0;
    let minimumDistance = 0;
    for (let dimension = 0; dimension < dimensions; dimension += 1) {
      const difference = matrix[sampleOffset + dimension] - centroids[dimension];
      minimumDistance += difference * difference;
    }
    for (let cluster = 1; cluster < clusters; cluster += 1) {
      const centroidOffset = cluster * dimensions;
      let distance = 0;
      for (let dimension = 0; dimension < dimensions; dimension += 1) {
        const difference = matrix[sampleOffset + dimension]
          - centroids[centroidOffset + dimension];
        distance += difference * difference;
      }
      if (distance < minimumDistance) {
        minimumDistance = distance;
        bestCluster = cluster;
      }
    }
    if (assignments[sample] !== bestCluster) {
      assignments[sample] = bestCluster;
      changed += 1;
    }
    counts[bestCluster] += 1;
    const sumOffset = bestCluster * dimensions;
    for (let dimension = 0; dimension < dimensions; dimension += 1) {
      sums[sumOffset + dimension] += matrix[sampleOffset + dimension];
    }
  }
  return changed;
}

function hashSeed(value) {
  return Number.parseInt(fnv1a(value), 16) >>> 0;
}

function createRandom(seed) {
  let state = seed || 0x9e3779b9;
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return (state >>> 0) / 0x1_0000_0000;
  };
}

function createCaseData(definition) {
  const random = createRandom(hashSeed(definition.id));
  const matrix = new Float64Array(definition.samples * definition.dimensions);
  for (let sample = 0; sample < definition.samples; sample += 1) {
    const cluster = sample % definition.clusters;
    const offset = sample * definition.dimensions;
    for (let dimension = 0; dimension < definition.dimensions; dimension += 1) {
      const center = cluster * 5 + dimension * 0.125;
      matrix[offset + dimension] = center + (random() - 0.5) * 0.8;
    }
  }
  const centroids = new Float64Array(definition.clusters * definition.dimensions);
  for (let cluster = 0; cluster < definition.clusters; cluster += 1) {
    const sample = cluster;
    centroids.set(
      matrix.subarray(
        sample * definition.dimensions,
        (sample + 1) * definition.dimensions,
      ),
      cluster * definition.dimensions,
    );
  }
  return { matrix, centroids };
}

function createState(definition) {
  const assignments = new Int32Array(definition.samples);
  assignments.fill(-1);
  return {
    assignments,
    sums: new Float64Array(definition.clusters * definition.dimensions),
    counts: new Uint32Array(definition.clusters),
  };
}

function executeIterations(run, definition, centroids) {
  const state = createState(definition);
  let changedChecksum = 0;
  for (let iteration = 0; iteration < definition.iterations; iteration += 1) {
    changedChecksum += run(
      centroids,
      definition.clusters,
      state.assignments,
      state.sums,
      state.counts,
    );
  }
  return { ...state, changedChecksum };
}

function equalTyped(left, right) {
  if (left.length !== right.length) return false;
  for (let index = 0; index < left.length; index += 1) {
    if (!Object.is(left[index], right[index])) return false;
  }
  return true;
}

function assertEquivalent(reference, candidate, caseId) {
  const equivalent = reference.changedChecksum === candidate.changedChecksum
    && equalTyped(reference.assignments, candidate.assignments)
    && equalTyped(reference.sums, candidate.sums)
    && equalTyped(reference.counts, candidate.counts);
  if (!equivalent) throw new Error(`K-Means benchmark equivalence failed for ${caseId}`);
  return true;
}

function measure(run, definition, centroids) {
  const startedAt = performance.now();
  const output = executeIterations(run, definition, centroids);
  const durationMs = performance.now() - startedAt;
  const checksum = output.changedChecksum
    + output.assignments[0]
    + output.sums[0]
    + output.counts[0];
  if (!Number.isFinite(checksum)) throw new Error('K-Means benchmark checksum is non-finite');
  return durationMs;
}

function quantile(sorted, probability) {
  if (sorted.length === 1) return sorted[0];
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  const weight = position - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

function statistics(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const median = quantile(sorted, 0.5);
  const q1 = quantile(sorted, 0.25);
  const q3 = quantile(sorted, 0.75);
  const iqr = q3 - q1;
  const absoluteDeviations = sorted
    .map((value) => Math.abs(value - median))
    .sort((left, right) => left - right);
  const mad = quantile(absoluteDeviations, 0.5);
  return {
    samples: sorted,
    sampleCount: sorted.length,
    minimumMs: sorted[0],
    q1Ms: q1,
    medianMs: median,
    q3Ms: q3,
    maximumMs: sorted.at(-1),
    iqrMs: iqr,
    madMs: mad,
    relativeIqr: median > 0 ? iqr / median : Number.POSITIVE_INFINITY,
  };
}

function environmentFingerprint(identity) {
  return `kmeans-env-${fnv1a(JSON.stringify(identity))}`;
}

function currentEnvironment() {
  const cpus = os.cpus();
  const identity = {
    runtime: 'node',
    runtimeVersion: process.version,
    platform: process.platform,
    architecture: process.arch,
    logicalCores: cpus.length || 1,
    wasm: typeof WebAssembly !== 'undefined',
    wasmSimd: typeof WebAssembly !== 'undefined' && WebAssembly.validate(SIMD_PROBE_MODULE),
    wasmThreads: false,
  };
  return {
    ...identity,
    fingerprint: environmentFingerprint(identity),
    operatingSystemRelease: os.release(),
    cpuModel: cpus[0]?.model ?? 'unknown',
    totalMemoryBytes: os.totalmem(),
    v8Version: process.versions.v8,
  };
}

function analyzeCrossover(cases) {
  const minimumImprovementRatio = Number(policy.minimumImprovementRatio);
  const maximumRelativeIqr = Number(policy.maximumRelativeIqr);
  const requiredConsecutiveWins = Number(policy.requiredConsecutiveWins);
  const qualifies = cases.map((entry) => (
    entry.equivalence === 'PASS'
    && entry.speedRatio >= minimumImprovementRatio
    && entry.typescript.relativeIqr <= maximumRelativeIqr
    && entry.wasm.relativeIqr <= maximumRelativeIqr
  ));
  for (let start = 0; start <= cases.length - requiredConsecutiveWins; start += 1) {
    let consecutive = true;
    for (let offset = 0; offset < requiredConsecutiveWins; offset += 1) {
      if (!qualifies[start + offset]) {
        consecutive = false;
        break;
      }
    }
    if (consecutive) {
      return {
        status: 'wasm-beneficial',
        crossoverWorkloadOperations: cases[start].workloadOperations,
        qualifyingCaseIds: cases
          .filter((_, index) => qualifies[index])
          .map((entry) => entry.id),
        reason: `${requiredConsecutiveWins} consecutive stable cases met the minimum improvement ratio`,
      };
    }
  }
  const stable = cases.filter((entry) => (
    entry.equivalence === 'PASS'
    && entry.typescript.relativeIqr <= maximumRelativeIqr
    && entry.wasm.relativeIqr <= maximumRelativeIqr
  ));
  if (
    stable.length >= requiredConsecutiveWins
    && stable.every((entry) => entry.speedRatio <= 1 / minimumImprovementRatio)
  ) {
    return {
      status: 'typescript-preferred',
      crossoverWorkloadOperations: null,
      qualifyingCaseIds: [],
      reason: 'All stable measured cases favored TypeScript by the policy margin',
    };
  }
  return {
    status: 'insufficient-evidence',
    crossoverWorkloadOperations: null,
    qualifyingCaseIds: [],
    reason: 'Measured cases did not establish a stable consecutive crossover',
  };
}

const wasmSource = await readFile(wasmSourcePath, 'utf8');
const nativeSource = await readFile(nativeSourcePath, 'utf8');
const wasmBytes = extractWasmBytes(wasmSource);
const environment = currentEnvironment();
const cases = [];

for (const definition of CASES[mode]) {
  const { matrix, centroids } = createCaseData(definition);
  const wasm = createWasmHarness(
    wasmBytes,
    matrix,
    definition.samples,
    definition.dimensions,
    definition.clusters,
  );
  const runTypeScript = (nextCentroids, clusters, assignments, sums, counts) => (
    assignTypeScript(
      matrix,
      definition.samples,
      definition.dimensions,
      nextCentroids,
      clusters,
      assignments,
      sums,
      counts,
    )
  );
  const runWasm = (nextCentroids, clusters, assignments, sums, counts) => (
    wasm.assign(nextCentroids, clusters, assignments, sums, counts)
  );

  for (let warmup = 0; warmup < definition.warmups; warmup += 1) {
    executeIterations(runTypeScript, definition, centroids);
    executeIterations(runWasm, definition, centroids);
  }

  const typescriptDurations = [];
  const wasmDurations = [];
  for (let repeat = 0; repeat < definition.repeats; repeat += 1) {
    const reference = executeIterations(runTypeScript, definition, centroids);
    const candidate = executeIterations(runWasm, definition, centroids);
    assertEquivalent(reference, candidate, definition.id);
    if (repeat % 2 === 0) {
      typescriptDurations.push(measure(runTypeScript, definition, centroids));
      wasmDurations.push(measure(runWasm, definition, centroids));
    } else {
      wasmDurations.push(measure(runWasm, definition, centroids));
      typescriptDurations.push(measure(runTypeScript, definition, centroids));
    }
  }

  const typescript = statistics(typescriptDurations);
  const wasmStats = statistics(wasmDurations);
  const workloadOperations = definition.samples * definition.dimensions * definition.clusters;
  cases.push({
    ...definition,
    workloadOperations,
    numericInputBytes: matrix.byteLength,
    equivalence: 'PASS',
    typescript: {
      ...typescript,
      medianPerCallMs: typescript.medianMs / definition.iterations,
    },
    wasm: {
      ...wasmStats,
      medianPerCallMs: wasmStats.medianMs / definition.iterations,
      memoryBytes: wasm.memoryBytes,
    },
    speedRatio: typescript.medianMs / wasmStats.medianMs,
    absoluteMedianDifferenceMs: typescript.medianMs - wasmStats.medianMs,
  });
}

const analysis = analyzeCrossover(cases);
const generatedAt = new Date();
const source = process.env.CI ? 'shared-ci-benchmark' : 'device-local-benchmark';
const reportCore = {
  schemaVersion: policy.reportSchemaVersion,
  generatedAt: generatedAt.toISOString(),
  repository: process.env.GITHUB_REPOSITORY ?? 'SUNHAOJUN22/ResinDB-Pro-by-SunHJ',
  sha: repositorySha(),
  mode,
  benchmarkRuntime: 'node-wasm',
  timingGate: 'informational-only',
  environment,
  kernel: {
    id: policy.kernel,
    version: policy.kernelVersion,
    protocolVersion: policy.protocolVersion,
    precision: 'f64',
    wasmBinarySha256: sha256(wasmBytes),
    nativeSourceSha256: sha256(nativeSource),
  },
  policy: {
    schemaVersion: policy.schemaVersion,
    policyVersion: policy.policyVersion,
    minimumImprovementRatio: Number(policy.minimumImprovementRatio),
    maximumRelativeIqr: Number(policy.maximumRelativeIqr),
    requiredConsecutiveWins: Number(policy.requiredConsecutiveWins),
  },
  equivalence: {
    status: cases.every((entry) => entry.equivalence === 'PASS') ? 'PASS' : 'FAIL',
    caseCount: cases.length,
  },
  cases,
  crossoverAnalysis: analysis,
};
const reportDigest = sha256(JSON.stringify(reportCore));
const report = { ...reportCore, reportDigest };
const expiresAt = new Date(
  generatedAt.getTime() + Number(policy.profileMaxAgeDays) * 24 * 60 * 60 * 1_000,
);
const profile = {
  schemaVersion: policy.profileSchemaVersion,
  policyVersion: policy.policyVersion,
  kernel: policy.kernel,
  kernelVersion: policy.kernelVersion,
  protocolVersion: policy.protocolVersion,
  generatedAt: generatedAt.toISOString(),
  expiresAt: expiresAt.toISOString(),
  environmentFingerprint: environment.fingerprint,
  source,
  eligibleForRuntimeAutoSelection: source === 'device-local-benchmark'
    && report.equivalence.status === 'PASS',
  status: analysis.status,
  crossoverWorkloadOperations: analysis.crossoverWorkloadOperations,
  minimumImprovementRatio: Number(policy.minimumImprovementRatio),
  maximumRelativeIqr: Number(policy.maximumRelativeIqr),
  requiredConsecutiveWins: Number(policy.requiredConsecutiveWins),
  benchmarkReportDigest: reportDigest,
};

const markdownRows = cases.map((entry) => (
  `| ${entry.id} | ${entry.workloadOperations} | ${entry.typescript.medianPerCallMs.toFixed(6)} | ${entry.wasm.medianPerCallMs.toFixed(6)} | ${entry.speedRatio.toFixed(3)} | ${entry.typescript.relativeIqr.toFixed(3)} | ${entry.wasm.relativeIqr.toFixed(3)} | ${entry.equivalence} |`
)).join('\n');
const markdown = `# K-Means FP64 backend benchmark\n\n`
  + `- Generated: ${report.generatedAt}\n`
  + `- Exact tree: \`${report.sha}\`\n`
  + `- Mode: \`${mode}\`\n`
  + `- Runtime: Node WebAssembly\n`
  + `- Environment fingerprint: \`${environment.fingerprint}\`\n`
  + `- Timing status: informational only; shared CI timing never gates acceptance\n`
  + `- Equivalence: **${report.equivalence.status}**\n`
  + `- Crossover analysis: **${analysis.status}**\n`
  + `- Reason: ${analysis.reason}\n`
  + `- Runtime-profile eligible: **${profile.eligibleForRuntimeAutoSelection}**\n\n`
  + `| Case | N×K×D operations | TypeScript median/call (ms) | WASM median/call (ms) | TS/WASM ratio | TS rel. IQR | WASM rel. IQR | Equivalent |\n`
  + `|---|---:|---:|---:|---:|---:|---:|---|\n${markdownRows}\n\n`
  + `The generated profile is device-scoped. A shared-CI profile is evidence only and cannot control browser runtime auto-selection.\n`;

await mkdir(artifacts, { recursive: true });
await Promise.all([
  writeFile(path.join(artifacts, 'kmeans-backend-benchmark.json'), `${JSON.stringify(report, null, 2)}\n`),
  writeFile(path.join(artifacts, 'kmeans-backend-benchmark.md'), markdown),
  writeFile(path.join(artifacts, 'kmeans-backend-profile.json'), `${JSON.stringify(profile, null, 2)}\n`),
  writeFile(path.join(artifacts, 'kmeans-backend-environment.json'), `${JSON.stringify(environment, null, 2)}\n`),
]);

console.log(`K-Means backend benchmark: ${report.equivalence.status}, ${analysis.status}, ${cases.length} case(s)`);
if (report.equivalence.status !== 'PASS') process.exitCode = 1;
