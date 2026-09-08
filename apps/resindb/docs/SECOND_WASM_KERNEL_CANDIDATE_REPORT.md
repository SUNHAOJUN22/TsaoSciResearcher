# SECOND_WASM_KERNEL_CANDIDATE_REPORT

## 1. Decision

```text
reportVersion: second-wasm-kernel-candidate-report-1.0.0
phase: 2J
status: insufficient-evidence
productionMigrationAuthorized: false
preferredFutureCandidate: kde-separable-row-accumulation
```

This phase evaluates candidates only. It does not add, retain, export, or activate a second production WebAssembly kernel.

The previously introduced intermediate KDE WebAssembly implementation was removed with forward commits because Phase 2J explicitly requires candidate evaluation without migration. The production KDE Worker remains the validated TypeScript FP64 separable implementation from Phase 2I.

## 2. Evaluation criteria

Each candidate was reviewed against:

1. hotspot call frequency and operation count;
2. compatibility with `row-major-float64-1.0.0` or an equivalent flat FP64 layout;
3. difficulty of exact or bounded numerical equivalence;
4. safe-fallback complexity;
5. scientific interpretation risk;
6. maturity of existing TypeScript reference tests;
7. availability of target-browser crossover evidence.

Scores use 1 as favourable/low difficulty and 5 as unfavourable/high difficulty.

| Candidate | Hotspot opportunity | FP64 memory readiness | Equivalence difficulty | Fallback complexity | Scientific risk | Phase 2J disposition |
|---|---:|---:|---:|---:|---:|---|
| KDE separable row accumulation | 5 | 5 | 2 | 2 | 2 | preferred future candidate; not implemented |
| Gaussian-process batch prediction | 5 | 5 | 4 | 3 | 4 | second priority; benchmark and variance gates required |
| RSM QR/SVD solve | 2 | 3 | 5 | 5 | 5 | defer |
| Sobol/Jansen sampling and hybrid evaluation | 4 | 4 | 5 | 4 | 5 | defer |

## 3. Candidate A: KDE separable row accumulation

### Current TypeScript reference

`src/workers/kdeWorker.ts` already uses the mathematically equivalent product-Gaussian separable form:

1. precompute `xKernel[observation, column]`;
2. compute one `yWeight[observation]` vector per grid row;
3. accumulate `sum(xKernel * yWeight)` for each column;
4. apply the unchanged normalization factor.

The direct-density equivalence test remains in `tests/science/kdeAcceleration.test.ts`.

### Opportunity

The row-accumulation loop performs approximately:

```text
observations × gridSize × gridSize
```

FP64 multiply-add operations after the exponential terms have already been reduced to `2 × observations × gridSize`.

### Why it ranks first

- flat `Float64Array` inputs are already available;
- no random-number consumption is involved;
- no matrix factorization, pivoting, rank decision, or adaptive jitter is involved;
- the TypeScript loop provides a simple authoritative reference;
- fallback can recompute the current row without altering model semantics;
- output can be compared element-by-element before normalization.

### Remaining evidence gaps

- no target-browser benchmark profile exists for this kernel;
- no stable crossover interval has been established;
- no device-local policy/schema exists for KDE backend selection;
- no browser lifecycle, cancellation, memory-pressure, or runtime-failure UAT has been completed;
- summation-order tolerance must be defined before any SIMD or parallel form is considered.

### Phase 2J conclusion

```text
candidateStatus: preferred-future-candidate
implementationStatus: not-implemented
releaseStatus: insufficient-evidence
```

## 4. Candidate B: Gaussian-process batch prediction

### Current TypeScript reference

`src/compute/gaussianProcess.ts` stores inputs, Cholesky factors, kernel scratch, forward-solve scratch, and alpha vectors as FP64 arrays.

Each prediction performs:

1. RBF kernel evaluation against every training row;
2. mean accumulation;
3. a forward triangular solve;
4. variance reconstruction and minimum-variance clamping.

Bayesian and multi-objective workers may evaluate many candidates against one shared factorization, so the call frequency can be high.

### Advantages

- input and factorization memory are already flat FP64;
- repeated prediction calls can amortize one memory copy;
- batch prediction is a clearer boundary than native factorization.

### Scientific and equivalence risks

- `Math.exp` implementation differences can accumulate in the mean;
- triangular-solve order affects variance;
- variance uses a physical/numerical floor;
- Cholesky jitter and factorization remain coupled scientific evidence;
- mean-only acceleration would create a partial backend whose evidence must not imply variance acceleration.

### Phase 2J conclusion

GP batch prediction is the second-ranked future candidate, but requires separate mean/variance tolerances, batch-size benchmarks, and factorization-identity evidence.

## 5. Candidate C: RSM QR/SVD

### Current TypeScript reference

`src/workers/rsmWorker.ts` builds a six-column quadratic design and calls `solveLeastSquares`, whose diagnostics distinguish QR from Jacobi-SVD fallback, rank, condition state, tolerance, residual norm, and singular values.

### Risks

- QR/SVD migration changes a solver, not merely a multiply-add loop;
- rank decisions depend on tolerances and column scaling;
- singular-vector signs and rotation order may differ while representing the same solution;
- underdetermined, rank-deficient, and ill-conditioned cases need independent gates;
- diagnostics are part of the scientific output contract;
- fallback must preserve solver identity and evidence, not merely coefficients.

### Phase 2J conclusion

RSM native solving is deferred. Grid evaluation alone is lower risk, but its typical workload is bounded by `gridSize²` and does not currently justify a second backend before KDE or GP.

## 6. Candidate D: Sobol/Jansen sampling core

### Current TypeScript reference

`src/workers/sobolWorker.ts` uses:

- versioned seeded pseudorandom normal sampling;
- optional truncated-normal rejection;
- flat FP64 A/B matrices;
- a reusable formula property dictionary;
- streamed hybrid evaluations;
- Jansen first-order and total-effect estimators.

### Risks

- bounded rejection sampling consumes a variable number of random values;
- changing random-consumption order breaks exact reproducibility;
- the formula evaluator remains JavaScript and may dominate runtime;
- moving only sampling to WASM may add transfer cost without material gain;
- moving formula execution requires a separate AST/register execution project;
- estimator accumulation order affects small sensitivity indices.

### Phase 2J conclusion

Sobol/Jansen is deferred. A future compact numeric formula plan should be benchmarked before considering a native sampling or estimator kernel.

## 7. Required gates before a second kernel

A future phase may implement KDE row accumulation only after all of the following are available:

1. an explicit kernel/version/protocol contract;
2. TypeScript FP64 authoritative output;
3. browser-worker exact or declared-tolerance equivalence;
4. NaN, infinity, zero-bandwidth, single-point, large-grid, memory-growth, trap, and cancellation tests;
5. safe per-call fallback without partial-output exposure;
6. fixed-environment and device-local benchmark profiles;
7. stable consecutive crossover evidence rather than one fast sample;
8. evidence fields that distinguish capability from actual backend use;
9. no FP32, hidden approximation, SIMD, threads, or `fast-math` claims without separate proof;
10. final exact-tree CI and browser UAT.

## 8. Final Phase 2J boundary

```text
SECOND_WASM_KERNEL_CANDIDATE_REPORT = COMPLETE
SECOND_WASM_KERNEL_IMPLEMENTATION = NOT_AUTHORIZED
SECOND_WASM_KERNEL_PRODUCTION_USE = FALSE
CURRENT_SECOND_KERNEL_EVIDENCE = INSUFFICIENT
```
