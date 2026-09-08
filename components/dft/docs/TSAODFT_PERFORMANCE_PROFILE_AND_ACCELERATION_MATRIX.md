# TsaoDFT Performance Profile and Acceleration Matrix

**Repository:** `SUNHAOJUN22/TsaoDFT_skill`  
**Purpose:** distinguish implemented repository-level efficiency improvements from profile-gated native work and real external-engine acceleration evidence.  
**Truth boundary:** no row labelled `REAL_EVIDENCE_REQUIRED` is a measured speedup claim. Synthetic and local parser observations, including Phase 10 comparison classifications, remain explicitly ineligible as DFT-engine, GPU or product performance evidence.

## 1. Status vocabulary

- `IMPLEMENTED_VALIDATED`: optimization, profiling/comparison capability or hardening exists and passes permanent CI;
- `ALREADY_NATIVE_LIBRARY`: Python delegates the expensive operation to an optimized compiled library;
- `STREAMING_VALIDATED`: bounded-memory streaming path is implemented and tested;
- `CONTROL_PLANE_ONLY`: repository plans, validates or records acceleration but does not execute the external engine kernel itself;
- `PROFILE_GATED`: representative profiling is required before implementation;
- `REAL_EVIDENCE_REQUIRED`: real hardware/build benchmark is required before any speedup statement;
- `NOT_APPLICABLE`: technology is not a scientifically or architecturally valid route for that workload.

## 2. Repository numerical and data-path matrix

| Area | Current implementation | Complexity / bottleneck | Implemented improvement | Candidate next acceleration | Required evidence | Status |
|---|---|---|---|---|---|---|
| Eyring/TST scalar rate | log-space Python math with shared SI constants | O(1); correctness dominated | corrected kcal→J unit and stable exponent handling | vector batch only if very large arrays become a workload | batch-size profile and equivalence | `IMPLEMENTED_VALIDATED` |
| Eyring CSV campaign | row-by-row CSV processing | O(rows), previously retained full table | bounded-memory streaming and atomic output | chunk/vector batch for millions of rows | representative campaign profile | `STREAMING_VALIDATED` |
| barrier uncertainty | three log-rate evaluations | O(1) | shared stable TST core | none currently justified | n/a | `IMPLEMENTED_VALIDATED` |
| thermodynamic closure | single pass over reactions | O(reactions) | finite contracts and `math.fsum` | vectorization unlikely to matter | network-size profile | `IMPLEMENTED_VALIDATED` |
| ridge regression | NumPy primal/dual solve | O(min(p³,n³)) dense solve plus products | choose smaller system; direct diagonal regularization; correct intercept | sparse/iterative solver for accepted large sparse data | realistic n×p sparsity and conditioning profile | `ALREADY_NATIVE_LIBRARY` |
| regression metrics | NumPy dot products and reductions | O(n) | direct vector reductions and finite checks | none until metrics dominate | profile | `IMPLEMENTED_VALIDATED` |
| uncertainty RSS/sum | `math.hypot` / `math.fsum` | O(n) | overflow- and cancellation-resistant reductions | NumPy batch only for large arrays | workload profile | `IMPLEMENTED_VALIDATED` |
| convergence analysis | sorted CSV + adjacent differences | O(n log n) due to sorting, O(n) scan | strict parsing, complete-tail rule, pairwise scan | skip sorting only if input-order contract becomes explicit | data-size and order profile | `IMPLEMENTED_VALIDATED` |
| atom mapping displacement | NumPy indexed coordinate differences | O(n) | removed Python per-atom `math.dist` loop | native/OpenMP only for very large accepted mappings | end-to-end conversion-inclusive profile | `IMPLEMENTED_VALIDATED` |
| generic XYZ pair distance | NumPy hypot reductions | per pair O(1); all-pairs caller may be O(n²) | vectorized backend | cell lists / neighbor lists for large periodic systems | accepted periodic workload and reference | `PROFILE_GATED` |
| Gaussian error taxonomy | precomputed casefolded literal-evidence index plus one ordered same-line ECP rule | O(text + evidence_count) normalized lookup; prior path performed nine case-insensitive full-text regex searches | profile-backed replacement; 512 category combinations and shared evidence prove legacy equivalence; slower mega-regex experiment rejected | no further taxonomy implementation justified | representative real logs only for external validity, not current semantic correctness | `IMPLEMENTED_VALIDATED` |
| Gaussian local-log profiling | chunked file read/hash followed by validated text parser; read/decode and parser measurements separated | current parser still requires decoded full text in memory | size/regular-file/mutation guards, source-identity omission, atomic report, result hash, cProfile and taxonomy A/B comparison | run on representative real logs before any parser architecture change | legally usable logs spanning size, job type and failure state | `IMPLEMENTED_VALIDATED` |
| Gaussian multi-log batch profiling | each file uses the validated local profiler; records are hash ordered; cross-file statistics and hotspots are aggregated | O(files × parser cost); optional processes increase throughput but can contend for shared resources | deterministic all-or-nothing batch, duplicate-content accounting, ordinal-only failures, isolated sequential default and explicit process-parallel mode | benchmark batch throughput only on the target machine; use sequential mode for comparable per-file timing | representative multi-category real-log set; repeated sequential and concurrent observations | `IMPLEMENTED_VALIDATED` |
| Gaussian batch-profile comparison | strict baseline/candidate report validation, anonymous record matching, semantic and timing-eligibility gates, hotspot migration analysis | O(records + hotspot functions); comparison cost is small relative to parsing | prevents mismatched input, changed semantics, environment drift, repeat-setting drift or concurrent timing from generating a misleading ratio; atomic private output | apply to one controlled parser candidate after representative baseline profiling | paired isolated reports from identical logs, settings and environment; exact semantic equivalence | `IMPLEMENTED_VALIDATED` |
| energy-profile calculation | finite CSV + `math.fsum` differences | O(states); plotting startup dominates small inputs | validated references and transactional four-file output | plot-process reuse/caching only for large campaigns | campaign-level profile | `IMPLEMENTED_VALIDATED` |
| file hashing | chunked `hashlib.sha256` | O(bytes), bounded memory | streaming; parallel ordered hashing exists in campaign paths | filesystem-aware batching only if hashing dominates | I/O profile | `ALREADY_NATIVE_LIBRARY` |
| evidence canonicalization | deterministic JSON and SHA-256 | O(records × record_size) | content-addressed evidence and ordered output | incremental Merkle-like structures for huge campaigns | record-count/profile evidence | `PROFILE_GATED` |
| performance statistics | median/MAD/IQR on retained values | sorting O(r log r), small r expected | finite gates and robust summaries | selection algorithms unnecessary at normal repeat counts | very large repeat-count profile | `IMPLEMENTED_VALIDATED` |
| job arrays | compact task table and scheduler array | O(tasks) materialization | 1,000-task compaction and deterministic task lookup | larger table indexing only if scheduler campaigns require it | real site scale | `IMPLEMENTED_VALIDATED` |
| environment probes | bounded subprocess probes | process startup per probe | deterministic parallel probe support | cached inventory with invalidation | repeated-workflow profile and privacy review | `PROFILE_GATED` |

## 3. Parser matrix

| Parser / source | Current data path | Correctness property | Performance assessment | Next route | Status |
|---|---|---|---|---|---|
| VASP | mmap/stream-aware extraction depending adapter path | fatal/late failure must override earlier apparent success; force blocks preserved | already avoids a simple full Python object copy in key path | profile real OUTCAR/vasprun sizes before native work | `STREAMING_VALIDATED` |
| Quantum ESPRESSO | line streaming and last-value extraction | late routine errors win | bounded memory | maintain streaming; optimize regex only if profile identifies hotspot | `STREAMING_VALIDATED` |
| CP2K | line streaming and last-value extraction | late abort wins | bounded memory | maintain streaming; profile large DBCSR-heavy logs only if parsing matters | `STREAMING_VALIDATED` |
| Gaussian taxonomy | one casefold normalization plus indexed evidence membership; one explicit ECP line-order rule | exact legacy category set/order, shared evidence and full parser hash preserved | synthetic same-process A/B observation exists for the isolated taxonomy function; explicitly not product performance evidence | freeze unless real logs reveal a semantic or workload gap | `IMPLEMENTED_VALIDATED` |
| Gaussian local-file profile surface | bounded regular-file read, streamed SHA-256, UTF-8 replacement accounting, repeated parse and cProfile | input mutation, oversize, empty/non-regular file and output collision fail closed; source path/basename/content omitted | execution capability is validated; no representative real log has been measured | run `scripts/profile_gaussian_log.py` on reviewed real logs and compare hotspot rankings | `IMPLEMENTED_VALIDATED` |
| Gaussian multi-file profile surface | isolated sequential or process-parallel independent local profiles followed by deterministic anonymous aggregation | any file failure aborts publication; duplicate contents remain visible; concurrent contention is explicitly labelled | batch measurement and throughput execution capability are validated; no production batch has been measured | run `scripts/profile_gaussian_log_batch.py --workers 1` for cross-log hotspot evidence, then separately evaluate `--workers N` for throughput | `IMPLEMENTED_VALIDATED` |
| Gaussian profile comparison surface | two anonymous Phase 9 reports are revalidated and matched by content hash/occurrence; hotspot aggregates are rebuilt from records | timing is withheld for input mismatch, semantic mismatch, concurrent mode, environment/settings mismatch or non-positive timing | comparison mechanics are validated; no representative paired real report exists | compare a controlled parser candidate against an isolated baseline on the same log multiset | `IMPLEMENTED_VALIDATED` |
| Gaussian broader parser | rich regex/block parsing and several `splitlines()` passes | late Gaussian errors win; TS/minimum fields, coordinates and rich properties validated | synthetic profile places orientation parsing above taxonomy, but representative cross-log distribution and paired comparison remain unavailable | change architecture only after stable cross-log hotspot evidence and a Phase 10-comparable candidate | `PROFILE_GATED` |
| engine parser contract | normalized acceptance and error precedence | missing files and fatal warnings fail closed | trust-boundary cost is small relative to external calculations | no native route justified | `IMPLEMENTED_VALIDATED` |
| benchmark bridge | parser outputs mapped into evidence records | required observables must be present | trust-boundary transformation, not a numerical hotspot | no acceleration without campaign profile | `IMPLEMENTED_VALIDATED` |

## 4. External DFT-engine acceleration matrix

The repository does not implement the expensive electronic-structure kernels. It generates validated plans, manifests, job scripts, environment inventories and evidence records for external engines.

| Engine | CPU reference route | Possible accelerator route | Repository role | Key variables | Claim status |
|---|---|---|---|---|---|
| VASP | licensed CPU build | supported NVIDIA GPU/OpenACC build where available | plan build capability, resource binding, job generation, parser and evidence qualification | VASP version/build, GPU model, ranks/GPU, NCORE/KPAR-equivalent choices, system size | `REAL_EVIDENCE_REQUIRED` |
| Quantum ESPRESSO | CPU MPI/OpenMP build | CUDA or vendor-supported GPU build, depending installation | generate empirically tested decomposition candidates; do not assume universal layout | pw.x build, FFT/diagonalization libraries, k-points, bands, pools, GPUs | `REAL_EVIDENCE_REQUIRED` |
| CP2K | CPU MPI/OpenMP with optimized BLAS/ScaLAPACK/DBCSR | CUDA/HIP/SYCL depending build and solver path | identify compatible provider and solver choices; materialize campaign | CP2K build, DBCSR/DBM, grid levels, basis, system sparsity, ranks/GPU | `REAL_EVIDENCE_REQUIRED` |
| Gaussian | packaged executable as licensed | only capabilities supported by the installed product/build | parse, profile and compare text-output parser observations; these do not change engine execution | installed revision, supported hardware, job type | `REAL_EVIDENCE_REQUIRED` |

No external-engine numerical speedup is recorded for these rows because no qualifying real campaign was available in the current execution environment.

## 5. Accelerator-provider compatibility matrix

| Provider / library | Valid use boundary | Invalid interpretation | Current repository state |
|---|---|---|---|
| CUDA | engine-native or repository-native NVIDIA GPU code with compatible build | GPU presence alone proves acceleration | hardware-aware planning and evidence schema; real benchmark absent |
| HIP/ROCm | engine-native or repository-native AMD GPU code with compatible build | CUDA plan can be relabelled HIP without build evidence | provider-specific planning; real benchmark absent |
| SYCL/oneAPI | supported Intel accelerator path or accepted native module | any Intel GPU automatically makes an engine SYCL-capable | provider-specific planning; real benchmark absent |
| Metal | edge/surrogate inference on supported Apple devices | production Kohn–Sham DFT is locally replaced | remote DFT fallback contract; real edge benchmark absent |
| cuBLAS/cuSOLVER | dense/sparse operations in a build that explicitly links them | repository Python control plane gains speed automatically | external build capability only |
| cuFFT | FFT hotspot in a compatible engine build | generic parser or scheduler acceleration | external engine boundary |
| cuTENSOR | explicit profiled tensor contractions with known data layout | generic drop-in switch for VASP/QE/CP2K/Gaussian | `NOT_APPLICABLE` without an accepted contraction workload |
| cuEquivariance | accepted equivariant ML models such as MACE/NequIP/e3nn | Kohn–Sham DFT accelerator | ML-only recommendation gate; real workload absent |
| Kokkos | portable native repository kernel after profile and build support | add portability layer before identifying a hotspot | `PROFILE_GATED` |
| OpenMP | CPU-native loop with sufficient granularity and no better library route | parallelize small Python orchestration | `PROFILE_GATED` |

## 6. Benchmark-campaign matrix

| Campaign | Scientific reference | Candidates | Required outputs | Current readiness |
|---|---|---|---|---|
| single-node CPU scaling | one accepted CPU configuration | rank/thread layouts | wall/CPU time, memory, iterations, equivalence | control plane ready; real runs absent |
| CPU vs single GPU | accepted CPU reference | one engine-native GPU candidate | build/hardware fingerprints, repeats, energy/force/stress/property deviations | control plane ready; real runs absent |
| multi-GPU strong scaling | compatible single-GPU baseline | 2/4/8 GPU layouts where site permits | speedup, efficiency, topology, binding, profiler evidence | schema/math ready; real runs absent |
| cross-provider comparison | same scientific identity | CUDA/HIP/SYCL only where engine builds exist | separate build identities and no mixed-topology aggregation | planning ready; real runs absent |
| edge surrogate | remote DFT reference and accepted model | CPU/GPU/NPU inference candidates | calibration, OOD gate, latency/energy, fallback trace | policy concept ready; accepted model/hardware absent |
| Gaussian synthetic parser microprofile | deterministic synthetic reference and full result hash | legacy taxonomy vs current taxonomy | labels, exact equality, wall-time observations, peak traced allocation and cProfile | implemented and CI-validated; explicitly not eligible as performance evidence |
| Gaussian single local-log profile | reviewed local text log and private source SHA-256 | current parser on representative job/failure classes | read/decode time, parser time, peak traced allocation, cProfile, result hash and privacy labels | executable and CI-validated; representative real logs not yet supplied |
| Gaussian cross-log isolated study | representative private log collection | current parser with `--workers 1` | deterministic records, status/size/timing/memory summaries and stable hotspot prevalence | executable and CI-validated; representative real batch absent |
| Gaussian batch-throughput study | the same reviewed log collection | `--workers 1` versus explicit process counts | batch elapsed time collected externally, worker/mode/contention metadata and identical result hashes | execution route ready; no target-machine throughput result exists |
| Gaussian paired parser comparison | identical private log multiset and isolated environment/settings | baseline parser versus one controlled candidate | exact record semantics, comparable timing gate, per-record ratios/deltas, memory change and hotspot migration | comparator implemented and CI-validated; representative paired reports absent |
| Gaussian parser architecture benchmark | reviewed real-log reference set | current versus future parser architecture | exact normalized output, wall time, peak RSS, file size and late-failure behavior | remains gated on representative batch-profile and paired-comparison results |

## 7. Native-extension decision matrix

A native module may proceed only when all boxes are satisfied.

| Gate | Required result | Current general state |
|---|---|---|
| representative profile | target path is a material end-to-end hotspot | synthetic taxonomy hotspot closed; single-/multi-log profiling and strict comparison tools ready; remaining real-log hotspot not established |
| reference implementation | deterministic CPU/Python result | available for existing numerical modules |
| equivalence | normal, extreme and adversarial tests | available for current Python improvements; Phase 10 can enforce paired parser semantic identity; absent for hypothetical native kernels |
| conversion overhead | included in benchmark | not measured |
| platform support | Windows core and Python 3.10/3.12/3.13 retained | must be designed |
| fallback | safe behavior when compiler/runtime unavailable | not implemented because no native module admitted |
| security | no downloaded executable or opaque binary path | required |
| measured benefit | repeatable end-to-end improvement from comparable isolated reports | not available for a native candidate |

Decision: no new native extension is currently justified.

## 8. Prioritized acceleration roadmap

### Priority 1 — Real engine evidence campaign

Choose one licensed engine/build and one scientifically accepted input. Capture a CPU reference and one accelerator candidate with complete fingerprints and at least the policy repeat count. This is the shortest path to a truthful real DFT acceleration statement.

### Priority 2 — Gaussian representative baseline and paired comparison

First create an isolated baseline on reviewed logs:

```text
python scripts/profile_gaussian_log_batch.py <log1> <log2> <log3> --iterations 3 --taxonomy-iterations 5 --workers 1 --out <baseline.json>
```

Use small, medium and operationally large logs across successful minimum/frequency, TS, IRC, rich-property, incomplete and late-error jobs. Then apply exactly one controlled parser candidate and produce the candidate report on the same machine, inputs and settings:

```text
python scripts/profile_gaussian_log_batch.py <same logs> --iterations 3 --taxonomy-iterations 5 --workers 1 --out <candidate.json>
```

Compare them:

```text
python scripts/compare_gaussian_batch_profiles.py <baseline.json> <candidate.json> --max-regression-percent 10 --out <comparison.json>
```

Only admit an architectural change when:

- anonymous input multisets match;
- all normalized parser outputs are semantically equivalent;
- environment fingerprints and repeat settings match;
- both reports are isolated sequential;
- the comparison is timing-eligible;
- hotspot movement supports the intended change;
- repeated end-to-end observations show a material benefit.

For batch throughput, run a separate study with explicit worker counts. Concurrent per-file timing remains ineligible for isolated parser comparison.

### Priority 3 — Periodic high-volume geometry

When accepted trajectory/neighbor workloads exist, compare:

- NumPy broadcast reference;
- chunked pair blocks;
- cell list;
- optional OpenMP/Kokkos backend.

Include periodic minimum-image equivalence and memory limits.

### Priority 4 — Equivariant ML

Only after an accepted MACE/NequIP/e3nn workload is present, benchmark baseline PyTorch operations against supported cuEquivariance paths with identical model outputs and uncertainty behavior.

## 9. Matrix conclusion

```text
REPOSITORY_NUMERICAL_ACCELERATION: IMPLEMENTED_FOR_SCOPED_HOTSPOTS
STREAMING_PATHS: IMPLEMENTED_FOR_EYRING_QE_CP2K_AND_SELECTED_VASP_WORKFLOWS
GAUSSIAN_ERROR_TAXONOMY_OPTIMIZATION: IMPLEMENTED_VALIDATED
GAUSSIAN_SINGLE_LOCAL_LOG_PROFILING: IMPLEMENTED_VALIDATED
GAUSSIAN_MULTI_LOG_BATCH_PROFILING: IMPLEMENTED_VALIDATED
GAUSSIAN_PROCESS_PARALLEL_BATCH_MODE: IMPLEMENTED_VALIDATED
GAUSSIAN_BATCH_PROFILE_COMPARATOR: IMPLEMENTED_VALIDATED
INPUT_MULTISET_EQUIVALENCE_GATE: IMPLEMENTED_VALIDATED
PARSER_SEMANTIC_EQUIVALENCE_GATE: IMPLEMENTED_VALIDATED
ISOLATED_TIMING_COMPARABILITY_GATE: IMPLEMENTED_VALIDATED
HOTSPOT_MIGRATION_ANALYSIS: IMPLEMENTED_VALIDATED
CONCURRENT_PER_FILE_TIMING_EQUIVALENCE: NOT_ASSUMED
REPRESENTATIVE_REAL_GAUSSIAN_BATCH_PROFILE: NOT_AVAILABLE
REPRESENTATIVE_REAL_GAUSSIAN_BATCH_COMPARISON: NOT_AVAILABLE
GAUSSIAN_BROADER_REAL_LOG_OPTIMIZATION: PROFILE_GATED
PERFORMANCE_EVIDENCE_MATH: VALIDATED
EXTERNAL_DFT_ENGINE_ACCELERATION: CONTROL_PLANE_READY_ONLY
REAL_CPU_ACCELERATION_EVIDENCE: NOT_AVAILABLE
REAL_GPU_ACCELERATION_EVIDENCE: NOT_AVAILABLE
NATIVE_EXTENSION: NOT_ADMITTED_WITHOUT_PROFILE
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
```
