# TsaoDFT Numerical and Performance Risk Register

**Repository:** `SUNHAOJUN22/TsaoDFT_skill`  
**Scope:** scientific formulas, numerical stability, algorithmic scaling, parser behavior, performance evidence and real-acceleration claims  
**Assessment basis:** validated repository state through Phase 10; representative real Gaussian logs, paired real batch-profile comparisons and real external-engine/GPU benchmarks remain unavailable.

## 1. Severity and status definitions

Severity:

- `CRITICAL`: can change scientific conclusions or create false performance qualification;
- `HIGH`: can materially corrupt values, convergence decisions, resource accounting or reproducibility;
- `MEDIUM`: can cause partial outputs, scalability failure, ambiguity or unstructured failure;
- `LOW`: maintainability or evidence-quality issue with limited immediate scientific effect.

Status:

- `RESOLVED`: code and direct tests pass permanent CI;
- `MITIGATED`: current controls reduce the risk, but task-specific evidence is still required;
- `PROFILE_GATED`: no implementation change is justified until representative profiling exists;
- `REAL_EVIDENCE_REQUIRED`: no truthful real-performance conclusion can be made without hardware/build data;
- `OPEN_NONBLOCKING`: remaining issue is documented and does not invalidate the current L2 validated-adapter capability.

## 2. Resolved scientific, numerical and measurement risks

| ID | Severity | Area | Risk and failure mode | Resolution and evidence | Status |
|---|---|---|---|---|---|
| NR-001 | CRITICAL | Eyring/TST | activation barrier labelled kcal/mol was combined with a cal-based gas constant without the required factor, producing rate errors of about 10¹¹ in a representative case | shared SI implementation, kcal→J conversion, log-rate evaluation and independent 15 kcal/mol regression | `RESOLVED` |
| NR-002 | HIGH | ridge regression | intercept based only on target mean while coefficients were fitted to uncentered features; predictions changed under feature translation | centered features/targets, unpenalized intercept `ȳ - x̄ᵀβ`, primal/dual equivalence tests | `RESOLVED` |
| NR-003 | HIGH | uncertainty RSS | direct squaring could overflow even when the mathematical norm was representable | `math.hypot`, tests near 1e308 | `RESOLVED` |
| NR-004 | HIGH | convergence | an undersized requested tail could be treated as converged | complete-tail requirement, sorted finite inputs and negative tests | `RESOLVED` |
| NR-005 | HIGH | thermodynamic closure | bool, NaN/Inf, wrong roots and malformed YAML could crash or yield invalid closure values | finite contracts, exact boolean, `math.fsum`, structured CLI failure | `RESOLVED` |
| NR-006 | HIGH | performance evidence | fractional values could be truncated by `int()` into valid repeat/node/rank/thread counts | exact-integer TypeGuard and direct API tests | `RESOLVED` |
| NR-007 | CRITICAL | performance qualification | NaN/Inf energy, force, stress, property or wall time could enter comparison semantics and potentially bypass ordinary inequalities | finite-real gates before eligibility, summary, equivalence, speedup and qualification | `RESOLVED` |
| NR-008 | HIGH | policy parsing | malformed or non-finite repeat, outlier and tolerance policies could be silently coerced or misapplied | strict mapping/numeric/integer policy contracts and adversarial tests | `RESOLVED` |
| NR-009 | HIGH | speedup/scaling | zero, negative or non-finite medians and GPU counts could generate meaningless speedup or efficiency | finite positive timing checks, topology checks and no-value fallback | `RESOLVED` |
| NR-010 | MEDIUM | profiler adapters | malformed scheduler duration, CPU time or memory strings could enter summaries | range checks, finite checks and explicit NOT_AVAILABLE results | `RESOLVED` |
| NR-011 | HIGH | energy profile | NaN/Inf energies or duplicate labels could create invalid or ambiguous relative profiles | finite CSV contracts, unique labels, explicit reference selection | `RESOLVED` |
| NR-012 | MEDIUM | energy-profile publication | CSV could be written before figures, leaving a partial bundle after plotting failure | same-filesystem staging, staged-file validation and transactional publication | `RESOLVED` |
| NR-013 | MEDIUM | energy subtraction | close large Hartree totals are cancellation-sensitive | `math.fsum((energy, -reference))` and independent value tests | `RESOLVED` |
| NR-014 | MEDIUM | geometry mapping | per-atom Python distance calls limited scalability | NumPy vectorized displacement/RMSD/max reduction and 2,000-atom test | `RESOLVED` |
| NR-015 | MEDIUM | Eyring CSV | complete-table materialization retained O(rows) Python objects and could leave partial output | row streaming and atomic publication | `RESOLVED` |
| NR-016 | MEDIUM | Gaussian error taxonomy | nine independent case-insensitive full-text regex searches dominated the synthetic large-log parser profile; a first mega-regex rewrite was slower despite semantic equivalence | deterministic labeled profiler; slower mega-regex rejected; precomputed casefolded literal index plus preserved `ECP.*not found` semantics; 512 category combinations, shared-evidence tests and unchanged full-parser result hash | `RESOLVED` |
| NR-017 | MEDIUM | Gaussian local profiling | real-log profiling previously required ad hoc script edits and could expose source paths, overwrite inputs, accept mutable/oversized files or produce unlabeled observations | standalone local profiler with chunked hashing, size and regular-file guards, read-time mutation detection, source/output collision refusal, atomic JSON, minimal environment fields and explicit parser-only non-qualification labels | `RESOLVED` |
| NR-018 | MEDIUM | Gaussian batch profiling | multi-log studies previously required manual aggregation, could silently omit failed files, leak calculation identities, lose duplicate-content visibility or mix concurrent throughput timing with isolated per-file timing | standalone batch profiler with ordinal-only failures, all-or-nothing publication, deterministic hash-based ordering, duplicate-content accounting, cross-log hotspot aggregation, isolated sequential default and explicit concurrent-contention labels | `RESOLVED` |
| NR-019 | HIGH | Gaussian batch-profile comparison | manual baseline/candidate comparison could mix different input multisets, different environments, different repeat settings, concurrent and isolated modes, or changed parser semantics while still presenting a timing ratio | strict Phase 9 report validation, anonymous `(input_sha256, occurrence)` matching, semantic-result gate, isolated-mode/environment/settings gate, positive timing requirement, fail-closed status ordering, hotspot migration analysis and explicit non-product/non-engine labels | `RESOLVED` |

## 3. Mitigated risks requiring task-specific scientific judgment

| ID | Severity | Area | Remaining risk | Current mitigation | Required next evidence | Status |
|---|---|---|---|---|---|---|
| NR-101 | HIGH | numerical equivalence | generic absolute tolerances may be inappropriate for a specific material, molecule or observable | tolerance table is explicit, finite, non-negative and bound to policy ID | domain-reviewed tolerances for each benchmark campaign | `MITIGATED` |
| NR-102 | HIGH | higher-order kinetics | rate units depend on activities and standard-state conventions, not only molecularity | output explicitly states convention requirement | declared solution/gas/surface standard state and activity model | `REAL_EVIDENCE_REQUIRED` |
| NR-103 | HIGH | uncertainty | RSS assumes independence and does not represent correlated model errors | aggregation rule is explicit; separate reporting supported | covariance/correlation model or empirical uncertainty calibration | `MITIGATED` |
| NR-104 | MEDIUM | convergence | absolute adjacent difference may not establish full scientific convergence for all observables | rule and threshold are explicit; incomplete tail fails | task-specific multi-observable and relative convergence study | `MITIGATED` |
| NR-105 | MEDIUM | RMSD | mapped-coordinate RMSD is not automatically rotationally aligned | scope is documented and mapping is explicit | alignment contract when structural superposition is required | `OPEN_NONBLOCKING` |
| NR-106 | MEDIUM | energy profile | Hartree-to-kcal conversion is correct, but combining energies from inconsistent methods remains scientifically invalid | surrounding manifests carry method fingerprints | method-identity enforcement at every profile ingestion route | `MITIGATED` |
| NR-107 | MEDIUM | performance outliers | MAD-based outlier flags do not explain root cause and must not justify deletion | outliers are counted and retained | profiler traces and operational review | `MITIGATED` |
| NR-108 | HIGH | benchmark topology | apparently identical GPU counts can conceal different CPU, interconnect or binding topology | hardware and GPU identities are recorded and compared | complete real-site topology fingerprint | `REAL_EVIDENCE_REQUIRED` |
| NR-109 | MEDIUM | local-log privacy | input SHA-256 is retained for auditability and can still be a sensitive identifier | path, basename, contents, hostname, username and home directory are omitted; disclosure warning is explicit | user data-governance review before sharing profile or comparison JSON outside the trusted environment | `MITIGATED` |
| NR-110 | MEDIUM | concurrent parser profiling | process-parallel profiling can reduce batch completion time but shared CPU, storage, cache and memory contention can distort individual file timings | sequential mode is the default; requested/used workers, mode and contention possibility are recorded; Phase 10 rejects concurrent reports for per-file timing classification | repeat sequential and concurrent studies on the target machine and interpret concurrent mode as throughput evidence only | `MITIGATED` |
| NR-111 | MEDIUM | local timing reproducibility | matching environment fingerprints and settings do not eliminate background load, thermal throttling, filesystem cache or runtime noise | repeat medians, explicit observed-language, configurable regression tolerance and no CI speed threshold | controlled repeated baseline/candidate campaigns and operational review | `MITIGATED` |

## 4. Profile-gated performance and scalability risks

| ID | Severity | Candidate area | Current concern | Why no blind implementation was made | Profiling/acceptance requirement | Status |
|---|---|---|---|---|---|---|
| PR-201 | MEDIUM | Gaussian parser beyond error taxonomy | the synthetic hotspot is closed and single-/multi-log profilers plus a strict comparator are executable, but no representative real baseline/candidate pair has established whether orientation parsing, repeated line splitting or another path dominates across job categories | accepted changes are limited to a measured synthetic hotspot and validated measurement/comparison tools; the slower mega-regex experiment was rejected; no native or broad parser rewrite was added | run `profile_gaussian_log_batch.py --workers 1` before and after one controlled candidate on legally usable successful, rich-output, incomplete and late-failure logs; require Phase 10 input, semantic, environment and timing gates to pass and inspect cross-log hotspot migration | `PROFILE_GATED` |
| PR-202 | MEDIUM | trajectory processing | future multi-frame geometry and neighbor-list work may become O(frames × atoms²) | no accepted large trajectory workload currently defines the boundary | representative frames/atoms/cell; memory and pair-count profile | `PROFILE_GATED` |
| PR-203 | MEDIUM | periodic neighbor lists | naïve full pair matrices can exceed memory | no current repository hotspot justifies a new native backend | cell-list/reference implementation and periodic-equivalence tests | `PROFILE_GATED` |
| PR-204 | LOW | energy-profile plots | Matplotlib startup dominates small tables | output generation is not established as an end-to-end hotspot | campaign-scale profile before caching or alternate renderer | `PROFILE_GATED` |
| PR-205 | LOW | hashing | streaming hashlib is already native and memory-bounded | custom C++ would duplicate optimized library code | profile showing hashing dominates end-to-end time | `PROFILE_GATED` |
| PR-206 | MEDIUM | ridge solver | BLAS/LAPACK performance depends on linked implementation and matrix shape | NumPy already delegates to native libraries | realistic dataset shapes and BLAS environment benchmark | `PROFILE_GATED` |
| PR-207 | MEDIUM | control-plane JSON/YAML | repeated canonicalization could matter in very large evidence campaigns | present campaigns are not shown to be serialization-bound | record-count/profile evidence and content-addressing cost breakdown | `PROFILE_GATED` |
| PR-208 | MEDIUM | environment probes | subprocess probe startup may dominate short local commands | probes are bounded and correctness-sensitive | representative repeated workflow profile; safe cache invalidation design | `PROFILE_GATED` |

## 5. Real-acceleration evidence risks

| ID | Severity | Claim surface | Risk | Required evidence before claim | Status |
|---|---|---|---|---|---|
| AR-301 | CRITICAL | VASP GPU speedup | control-plane support may be mistaken for measured VASP acceleration | real VASP GPU build, immutable input, CPU reference, repeats, scientific equivalence and signed evidence bundle | `REAL_EVIDENCE_REQUIRED` |
| AR-302 | CRITICAL | QE GPU speedup | backend recommendation does not prove the installed QE build supports or benefits from it | real build capabilities, decomposition sweep and measured topology | `REAL_EVIDENCE_REQUIRED` |
| AR-303 | CRITICAL | CP2K GPU speedup | CUDA/HIP/SYCL route depends on build, solver and workload | real CP2K build, DBM/DBCSR/solver profile, reference outputs | `REAL_EVIDENCE_REQUIRED` |
| AR-304 | CRITICAL | Gaussian acceleration | repository parser profiling, comparison or optimization can be mistaken for accelerating the externally packaged Gaussian electronic-structure engine | supported executable/build evidence and real engine run comparison; parser-only observations must remain separately labelled | `REAL_EVIDENCE_REQUIRED` |
| AR-305 | HIGH | multi-GPU scaling | speedup can appear from incomparable topology or insufficient single-GPU baseline | compatible single-GPU and N-GPU runs, bindings, interconnect and strong-scaling math | `REAL_EVIDENCE_REQUIRED` |
| AR-306 | HIGH | edge inference | a surrogate could be presented as replacing DFT validation | accepted model, calibration, OOD/uncertainty gate and remote DFT fallback | `REAL_EVIDENCE_REQUIRED` |
| AR-307 | HIGH | cuEquivariance | library may be incorrectly presented as a Kohn–Sham DFT accelerator | accepted equivariant ML workload such as MACE/NequIP/e3nn and measured inference/training | `REAL_EVIDENCE_REQUIRED` |
| AR-308 | HIGH | cuTENSOR | library may be treated as a generic packaged-engine switch | explicit tensor contraction hotspot, data-layout design, equivalence and real benchmark | `REAL_EVIDENCE_REQUIRED` |

## 6. Repository and quality risks

| ID | Severity | Risk | Current control | Status |
|---|---|---|---|---|
| QR-401 | HIGH | concurrent main writes overwrite new work | re-read HEAD and content SHA before every write; GitHub 409 protection | `MITIGATED` |
| QR-402 | HIGH | old CI result incorrectly attributed to latest commit | exact final HEAD combined status, jobs and logs checked | `MITIGATED` |
| QR-403 | HIGH | coverage improvement through denominator manipulation | permanent coverage inventory and no exclusion/gate changes | `MITIGATED` |
| QR-404 | HIGH | trust-boundary regression | six core modules tracked separately; strict mypy and adversarial tests | `MITIGATED` |
| QR-405 | MEDIUM | flaky timing benchmarks block CI | correctness and evidence invariants are gates; parser timings remain observations rather than pass thresholds | `MITIGATED` |
| QR-406 | HIGH | simulated or local parser observations presented as engine evidence | explicit source kinds, evidence labels, `NOT_ELIGIBLE` qualification and L2-only capability boundary | `MITIGATED` |
| QR-407 | HIGH | local profiling leaks confidential calculation identity | successful and failed reports omit source path/basename/content; minimal environment contract and direct non-disclosure tests | `MITIGATED` |
| QR-408 | HIGH | a failed file is silently dropped from a batch report | any child failure aborts publication; existing output remains unchanged; failure identifies only the ordinal | `MITIGATED` |
| QR-409 | HIGH | concurrent batch timing is misrepresented as isolated speedup | execution mode and contention flag are mandatory; Phase 10 comparison refuses concurrent timing classification | `MITIGATED` |
| QR-410 | HIGH | incomparable or semantically changed batch reports produce a speedup/regression label | anonymous input multiset, normalized parser results, environment fingerprints, repeat settings and isolated mode must all match before timing observations are classified | `MITIGATED` |
| QR-411 | HIGH | comparison output leaks baseline/candidate report identity | report paths, basenames and source-log identities are excluded from success and failure documents; output/input collision is rejected and publication is atomic | `MITIGATED` |

## 7. Priority order for future work

1. Run the validated batch profiler in isolated sequential mode on a legally usable representative Gaussian log set to create a baseline report.
2. Apply one controlled parser candidate, repeat the same batch on the same environment and settings, and run `compare_gaussian_batch_profiles.py`.
3. Admit broader Gaussian parser redesign only when the Phase 10 input, semantic, environment and timing gates pass and hotspot migration is stable across job categories.
4. Define one real, licensed and reproducible VASP/QE/CP2K benchmark campaign with CPU reference and complete hardware/build fingerprints.
5. Review task-specific scientific-equivalence tolerances before any real performance qualification.
6. Add periodic trajectory/neighbor-list work only when an accepted workload demonstrates a scaling bottleneck.
7. Consider native or GPU code only after end-to-end profiling includes data conversion, file I/O and launch overhead.

## 8. Current residual-risk conclusion

```text
OPEN_CRITICAL_STATIC_NUMERICAL_DEFECTS_IN_SCOPED_MODULES: NONE_IDENTIFIED
OPEN_CRITICAL_REAL_ACCELERATION_CLAIMS: BLOCKED_BY_MISSING_REAL_EVIDENCE
PERFORMANCE_EVIDENCE_NONFINITE_BYPASS: CLOSED
LOSSY_INTEGER_BYPASS: CLOSED
PARTIAL_ENERGY_PROFILE_PUBLICATION: CLOSED
GAUSSIAN_ERROR_TAXONOMY_HOTSPOT: RESOLVED_WITH_SYNTHETIC_PROFILE
GAUSSIAN_SINGLE_LOCAL_LOG_PROFILING_TOOL: IMPLEMENTED_VALIDATED
GAUSSIAN_MULTI_LOG_BATCH_PROFILING_TOOL: IMPLEMENTED_VALIDATED
GAUSSIAN_BATCH_PROFILE_COMPARATOR: IMPLEMENTED_VALIDATED
INPUT_MULTISET_EQUIVALENCE_GATE: ENFORCED
PARSER_SEMANTIC_EQUIVALENCE_GATE: ENFORCED
ISOLATED_TIMING_COMPARABILITY_GATE: ENFORCED
CONCURRENT_BATCH_CONTENTION_LABEL: ENFORCED
PARTIAL_GAUSSIAN_BATCH_OR_COMPARISON_PUBLICATION: BLOCKED
REPRESENTATIVE_REAL_GAUSSIAN_BATCH_PROFILE: NOT_AVAILABLE
REPRESENTATIVE_REAL_GAUSSIAN_BATCH_COMPARISON: NOT_AVAILABLE
GAUSSIAN_BROADER_REAL_LOG_OPTIMIZATION: PROFILE_GATED
NATIVE_CPU_OR_GPU_EXTENSION: PROFILE_GATED
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
```
