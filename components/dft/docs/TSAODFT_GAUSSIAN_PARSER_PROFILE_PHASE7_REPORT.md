# TsaoDFT Gaussian Parser Profile and Optimization Phase 7 Report

**Program:** `TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_V2`  
**Phase:** 7 — profile-backed Gaussian parser hotspot optimization  
**Starting HEAD:** `84684603a18f4b61e8dd49e1ba95d7ee1eb4ad7f`  
**Validated implementation HEAD:** `755e24af960a6e119b31c319bf3c561df4f4eb60`  
**Validated implementation GitHub Actions run:** `30735755022`  
**Evidence labels:** `SIMULATION_ONLY / NOT_REAL_HARDWARE / NOT_PERFORMANCE_EVIDENCE`  
**External Gaussian execution:** `NO`  
**Public capability boundary:** `L2_VALIDATED_ADAPTER`

## 1. Objective

Previous repository-wide work identified `parse_gaussian.py` as the strongest remaining parser-performance candidate, but correctly left it `PROFILE_GATED` because no representative measurement existed. This phase added a deterministic, explicitly synthetic microprofile, used it to identify a concrete hotspot, rejected a slower attempted rewrite, and accepted only the implementation that preserved parser semantics and improved the scoped hotspot in a same-process A/B comparison.

The phase does not claim Gaussian engine acceleration, GPU acceleration, or target-workstation performance. It measures repository parsing code on GitHub-hosted CPU runners using deterministic synthetic text.

## 2. Added profiling contract

The new profiler is:

`scripts/profile_gaussian_parser.py`

It provides:

- deterministic synthetic Gaussian-like logs;
- configurable optimization blocks, atoms, filler lines and repeats;
- exact positive/non-negative integer CLI contracts;
- full parser result hashing;
- `time.perf_counter` observations;
- `tracemalloc` peak Python allocation observations;
- `cProfile` cumulative-function ranking;
- atomic JSON output;
- same-process legacy/current taxonomy A/B comparison;
- explicit non-qualification and limitation fields.

Every report includes:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
external_dft_engine_invoked = false
scientific_acceptance = NOT_EVALUATED
performance_qualification = NOT_ELIGIBLE
```

## 3. Baseline synthetic profile

The first accepted profiler implementation ran on commit:

`f7f0097562add3ae89a11f07ab893dca4bf97c15`

GitHub Actions run:

`30735158730`

Workload:

| Field | Value |
|---|---:|
| Optimization/frequency blocks | 120 |
| Atoms per orientation block | 18 |
| Filler lines per block | 24 |
| Input bytes | 397,901 |
| Input lines | 6,870 |
| Input SHA-256 | `aa33472cefe2110c4be130ad04fafad7f0971f5f4f86935370bace02c031ec9a` |

Parser result:

| Field | Value |
|---|---:|
| Status | `TS_CANDIDATE` |
| SCF energies | 120 |
| Frequencies | 360 |
| Orientation blocks | 120 |
| Result SHA-256 | `e44eabaa5cb182ea76fb547d1027fa41754230d0bfe159f7b224d58706748edd` |

Observed baseline values on that hosted runner:

| Measurement | Observation |
|---|---:|
| Full parser median | 0.192036309 s |
| Peak traced Python allocation | 1.560780525 MiB |
| `parse_log` cProfile cumulative | 0.132564905 s |
| `_error_taxonomy` cumulative | 0.081728902 s |
| `_orientation_blocks` cumulative | 0.021471576 s |

`_error_taxonomy` accounted for approximately 61.7% of the profiled `parse_log` cumulative time in this synthetic workload. The old implementation ran nine independent case-insensitive regular-expression searches over the complete text.

## 4. Rejected optimization experiment

A first rewrite combined all taxonomy alternatives into one named-group mega-regex. It passed semantic tests and permanent CI at commit:

`39e6e30900647732b1ce0d696959b0e990399cc7`

Run:

`30735420868`

However, the same synthetic workload observed:

- full parser median: 0.423803230 s;
- `_error_taxonomy` cumulative: 0.266458483 s.

This was a material performance regression. The implementation was not accepted as the final optimization even though it was functionally correct and CI-green. The phase therefore demonstrates that code complexity or a nominal “single scan” design was not treated as proof of speed.

## 5. Accepted taxonomy implementation

The final implementation uses a precomputed taxonomy index:

1. the declared taxonomy rule table remains the output and compatibility authority;
2. literal ASCII evidence alternatives are normalized once at import;
3. the input text is `casefold()`-normalized once per taxonomy call;
4. normalized literal evidence uses substring membership;
5. the only non-literal rule, `ECP.*not found`, retains same-line, forward-order semantics;
6. shared evidence still activates every applicable category;
7. output order remains the original taxonomy-rule order.

Shared-evidence semantics preserved include:

- `Erroneous write` → `MEMORY` and `DISK_OR_IO`;
- `FileIO operation on non-existent file` → `DISK_OR_IO` and `CHECKPOINT`.

The final parser result SHA-256 for the deterministic synthetic workload remains:

`e44eabaa5cb182ea76fb547d1027fa41754230d0bfe159f7b224d58706748edd`

## 6. Semantic-equivalence evidence

The dedicated taxonomy regression suite covers:

- all 512 on/off combinations of the nine taxonomy categories;
- independent legacy-algorithm comparison;
- shared evidence and overlapping categories;
- case-insensitive evidence;
- taxonomy output order independent of evidence order;
- unique-evidence index coverage;
- empty and unrelated text;
- a guard that prevents fallback to per-rule `re.search` inside the new taxonomy function.

The profiler also performs same-process result equality before reporting A/B observations. Any mismatch raises an error rather than producing a performance record.

## 7. Final synthetic observation

Validated final implementation:

`755e24af960a6e119b31c319bf3c561df4f4eb60`

Run:

`30735755022`

The final run used the same deterministic workload and input hash as the baseline.

Full-parser observation on the final hosted runner:

| Measurement | Observation |
|---|---:|
| Full parser median | 0.165083315 s |
| Peak traced Python allocation | 1.560780525 MiB |
| `parse_log` cProfile cumulative | 0.079052147 s |
| `_orientation_blocks` cumulative | 0.027451060 s |

`_error_taxonomy` no longer appears among the twelve highest cumulative functions.

The same-process taxonomy A/B comparison used five alternating-order iterations:

| Measurement | Observation |
|---|---:|
| Legacy median | 0.100938047 s |
| Current median | 0.004073546 s |
| Legacy/current observed ratio | 24.778914× |
| Semantic equality | PASS |

This 24.778914× value is a same-process micro-observation for the isolated synthetic taxonomy function. It is not a product performance claim, not a full-parser guaranteed speedup, and not Gaussian engine acceleration.

Cross-run full-parser times are reported as observations only because hosted runners, regions and contention can differ between workflow runs.

## 8. Permanent quality-gate result

The validated implementation HEAD passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint and format;
- mypy across 18 isolated targets;
- strict trust-boundary mypy across 4 targets;
- Bandit;
- strict repository audit;
- CodeQL Python analysis;
- runtime, development and exact locked-environment dependency audits;
- CycloneDX SBOM generation;
- all unit and integration suites.

Final metrics:

| Metric | Phase 6 final documentation baseline | Phase 7 validated implementation |
|---|---:|---:|
| Tests | 450 | **465** |
| Suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 94.09% | **94.17%** |
| Branch coverage | 83.47% | **83.69%** |

Trust-core coverage remains:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

Coverage artifact:

- artifact ID: `8829520557`;
- SHA-256 digest: `d5732ffe0638caf3b2ef54ebba64d9c1620e9cd215de2ec6928156ad057a1e26`.

## 9. Remaining profile boundary

This phase closes one proven hotspot: Gaussian error-taxonomy classification on large text.

It does not establish that the entire parser is fully optimized. The final cProfile now places orientation-block parsing as the largest repository-specific helper in the synthetic workload. Broader parser changes remain gated by representative real Gaussian logs because synthetic text cannot reproduce every Gaussian revision, Link1 layout, binary/text artifact, malformed block or operational file-size distribution.

Remaining work:

1. collect legally usable representative Gaussian logs spanning successful, incomplete and late-failure jobs;
2. profile small, medium and large real logs;
3. verify exact normalized output against the current parser;
4. assess repeated `splitlines()` and orientation parsing only if real-log profile confirms material end-to-end cost;
5. retain late-error-wins semantics;
6. do not add native code unless conversion-inclusive end-to-end benefit is demonstrated.

## 10. Status

```text
GAUSSIAN_SYNTHETIC_PROFILE: COMPLETE
PROFILE_LABELS: SIMULATION_ONLY / NOT_REAL_HARDWARE / NOT_PERFORMANCE_EVIDENCE
INITIAL_HOTSPOT_IDENTIFIED: ERROR_TAXONOMY
MEGA_REGEX_EXPERIMENT: REJECTED_FOR_PERFORMANCE_REGRESSION
FINAL_TAXONOMY_IMPLEMENTATION: VALIDATED
TAXONOMY_512_COMBINATION_EQUIVALENCE: PASS
SHARED_EVIDENCE_EQUIVALENCE: PASS
FULL_PARSER_RESULT_HASH: UNCHANGED
SAME_PROCESS_TAXONOMY_OBSERVED_RATIO: 24.778914X
FULL_PARSER_PRODUCT_SPEEDUP_CLAIM: NO
REAL_GAUSSIAN_LOG_PROFILE: NOT_AVAILABLE
REAL_GAUSSIAN_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
VALIDATED_IMPLEMENTATION_CI: PASS
TESTS: 465
STATEMENT_COVERAGE: 94.17%
BRANCH_COVERAGE: 83.69%
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
BRANCH_CREATED: NO
PULL_REQUEST_CREATED: NO
FORCE_PUSH: NO
HISTORY_REWRITE: NO
QUALITY_GATE_REDUCTION: NO
TEST_DELETION: NO
FABRICATED_PERFORMANCE_CLAIM: NO
```
