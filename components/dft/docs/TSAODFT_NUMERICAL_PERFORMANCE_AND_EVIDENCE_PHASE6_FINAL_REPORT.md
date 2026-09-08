# TsaoDFT Numerical Performance and Evidence Phase 6 Final Report

**Program:** `TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_V2`  
**Phase:** 6 — performance-evidence numerical trust boundary and atomic energy-profile generation  
**Starting HEAD:** `2d1f3e67ca3bad3bddea0c759386b1c22ec02b33`  
**Validated implementation HEAD:** `3157c5863fa7ca8ab79cf9592562e91bfe280d5a`  
**Validated implementation GitHub Actions run:** `30713615964`  
**Reusable master prompt:** `docs/TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_MASTER_PROMPT_V2.md`  
**Evidence boundary:** `NOT_REAL_DFT_BENCHMARK / NOT_REAL_GPU_BENCHMARK / NOT_REAL_EDGE_BENCHMARK`

## 1. Phase objective

Phase 5 corrected the most serious scientific and numerical defects in Eyring/TST, ridge regression, uncertainty aggregation, convergence decisions, thermodynamic closure and geometry reductions. Phase 6 continued from that validated baseline rather than restarting the repository audit.

The two highest-priority remaining scopes were:

1. preventing non-finite, lossy or malformed values from entering performance qualification and producing false speedup or scaling evidence;
2. preventing energy-profile generation from accepting invalid scientific values or publishing partial output bundles.

The phase did not attempt native or GPU implementation merely to increase the apparent acceleration surface. Profile-backed end-to-end evidence remains a prerequisite for C++, OpenMP, Kokkos, CUDA, HIP or SYCL additions.

## 2. Change inventory

From Phase 5 final HEAD to the validated Phase 6 implementation HEAD:

- **10 sequential fast-forward commits**;
- **4 changed paths**;
- no branch;
- no pull request;
- no force push;
- no history rewrite.

Changed paths:

1. `skills/tsao-dft-hpc-provenance/scripts/performance_evidence.py`
2. `skills/tsao-dft-hpc-provenance/tests/test_performance_evidence_numerics.py`
3. `skills/tsao-dft-researcher/scripts/build_energy_profile.py`
4. `skills/tsao-dft-researcher/tests/test_build_energy_profile.py`

The implementation diff contains:

- 174 additions / 84 deletions in `performance_evidence.py`;
- 243 lines in the new performance-numerics test module;
- 149 additions / 53 deletions in `build_energy_profile.py`;
- 137 additions / 9 deletions in its test module.

## 3. Performance-evidence numerical trust boundary

### 3.1 Lossy integer coercion closed

The prior direct programmatic path used `int(value)` in several integer contracts. Although schema-facing routes already rejected many invalid values, direct calls could still allow values such as `1.5` to be truncated to `1`.

The implementation now distinguishes:

- an exact integer: Python `int`, excluding `bool`;
- a finite real: `int` or `float`, excluding `bool`, with `math.isfinite` required.

The following are rejected for integer fields:

- `1.5`;
- `1.0`;
- `"1"`;
- `True` and `False`.

This applies to repeat indices, exit status, nodes, ranks, threads, SCF iterations, I/O byte counts and policy repeat counts.

### 3.2 NaN and infinity gates

Non-finite values are now rejected before validation eligibility, statistics, numerical equivalence or qualification.

Covered scientific fields include:

- total energy;
- forces;
- stress;
- task-specific properties;
- convergence thresholds.

Covered performance and resource fields include:

- wall time;
- CPU time;
- host/device memory;
- utilization;
- energy consumption;
- node/rank/thread topology;
- repeat and iteration counts.

A record containing NaN or infinity cannot be counted as an eligible successful run and therefore cannot produce a speedup.

### 3.3 Strict policy contracts

Performance and numerical-equivalence policies now fail closed when explicitly malformed.

The implementation rejects:

- fractional or non-integer minimum repeat counts;
- zero or negative repeat requirements;
- non-mapping performance policy sections;
- non-mapping numerical-equivalence sections;
- non-mapping per-property tolerance tables;
- NaN/Inf tolerances;
- negative absolute tolerances;
- non-positive outlier thresholds.

An absent optional section may still use its declared default. An explicitly provided, non-empty malformed section is not silently converted to a default.

### 3.4 Finite statistics and speedup

The following helpers now enforce finite numeric inputs:

- percentile interpolation;
- median/MAD/IQR summaries;
- performance-field extraction;
- vector deviation;
- reference observable aggregation;
- numerical equivalence;
- speedup and strong-scaling calculations.

CPU-to-candidate speedup is calculated only when:

- reference median is finite and greater than zero;
- candidate median is finite and greater than zero;
- the minimum repeat gate passes;
- numerical equivalence passes.

A NaN speedup cannot pass qualification through Python comparison semantics.

### 3.5 Resource topology and profiler adapters

Resource counting no longer performs lossy coercion. Invalid or incomplete topology produces zero usable CPU-core resources rather than a fabricated allocation.

Duration and memory adapters were hardened to reject:

- NaN and infinity;
- negative components;
- invalid minute or second ranges;
- malformed day prefixes;
- non-numeric CPU times;
- overflowing memory values.

These values are reported as unavailable rather than entering benchmark summaries.

## 4. Performance-evidence regression tests

A dedicated test module now exercises direct Python API and integrated evidence-flow paths.

The tests cover:

- fractional integers;
- numeric strings;
- bool-as-number;
- NaN/Inf scientific observables;
- non-finite summary values;
- malformed percentiles;
- non-finite candidate energies, forces and properties;
- invalid wall time and resource topology;
- NaN speedup qualification attempts;
- invalid duration and memory strings;
- malformed policy mappings;
- negative/non-finite tolerances;
- empty and invalid resource sets;
- malformed direct qualification policies.

The coverage target was not met by excluding new code. Business-meaningful branches were added until statement and branch coverage both exceeded the Phase 5 baseline.

## 5. Energy-profile scientific input contracts

`build_energy_profile.py` now validates the energy table before producing any output.

It rejects:

- missing or blank energy-column names;
- missing `label` or energy columns;
- missing row values;
- extra unnamed CSV fields;
- blank labels;
- duplicate labels;
- non-numeric energies;
- NaN and infinity;
- empty tables;
- missing reference labels;
- non-finite reference energies.

Duplicate labels are rejected because a label-selected reference would otherwise be ambiguous.

## 6. Energy reference and numerical subtraction

Valid reference modes remain:

- `first`;
- `min`;
- an explicit label.

Relative energy remains:

```text
relative_kcal_mol = (energy_hartree - reference_hartree) × 627.5094740631
```

The subtraction is now expressed through `math.fsum((energy, -reference))` to reduce cancellation error when two large Hartree totals are close.

Tests independently verify the relative values and each reference-selection route.

## 7. Transactional energy-profile output

The command produces a four-file bundle:

- CSV;
- SVG;
- PDF;
- 600 dpi PNG.

The previous implementation wrote the CSV before plotting. A later plotting failure could leave a partial bundle.

The new path performs:

```text
validate input
→ compute normalized rows
→ create same-filesystem staging directory
→ write staged CSV
→ render staged SVG/PDF/PNG
→ verify every staged file exists and is non-empty
→ validate target paths
→ publish the complete bundle
```

If rendering fails before publication:

- no new formal output is published;
- existing formal outputs remain unchanged;
- the staging directory is removed.

During publication, existing regular files are temporarily backed up. If a replacement fails, already-published new files are removed and backups are restored.

A target path that already exists as a directory or another non-regular object is rejected before publication.

## 8. Energy-profile regression tests

The tests cover:

- valid CSV and all three figure formats;
- exact label order;
- expected relative-energy values;
- first/min/explicit-label references;
- compensated subtraction;
- NaN/Inf energies;
- duplicate and blank labels;
- non-numeric values;
- missing columns;
- empty input;
- extra fields;
- rendering failure with preservation of old outputs;
- temporary-directory cleanup;
- output-directory collision.

The tests do not rely on fragile wall-clock timing.

## 9. Validated implementation quality results

The validated implementation commit `3157c5863fa7ca8ab79cf9592562e91bfe280d5a` passed run `30713615964`.

| Metric | Phase 5 baseline | Phase 6 validated implementation |
|---|---:|---:|
| Tests | 434 | **450** |
| Isolated suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 93.98% | **94.13%** |
| Branch coverage | 83.22% | **83.42%** |

The six execution/trust cores remain unchanged:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

The coverage artifact for the validated implementation is:

- artifact ID: `8822743852`;
- SHA-256 digest: `f7f8b30c679119550bef0f031e2d68506ddeb723396c93a85c24f292c5769a0c`.

## 10. Permanent quality gate

The validated implementation passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint;
- Ruff formatting;
- mypy across 18 isolated targets;
- strict trust-boundary mypy across 4 targets;
- 450 tests across 9 suites;
- statement and branch coverage;
- Bandit production audit;
- strict repository audit;
- CodeQL Python analysis;
- runtime dependency audit;
- development dependency audit;
- exact locked-environment audit;
- CycloneDX SBOM generation and upload.

## 11. Acceleration scope and remaining profile-gated work

This phase improved trustworthiness and data-path robustness. It did not produce a real DFT-engine speedup measurement.

Still profile-gated:

1. representative large Gaussian-log parsing;
2. trajectory and neighbor-list workloads at realistic structure sizes;
3. C++/OpenMP/Kokkos boundaries for geometry only if conversion costs are outweighed;
4. CUDA/HIP/SYCL paths only on available real hardware;
5. real VASP/QE/CP2K build and topology benchmark campaigns;
6. accepted equivariant-ML workloads before considering cuEquivariance;
7. explicit tensor-contraction workloads before considering cuTENSOR.

The external compiled engines remain responsible for Kohn–Sham, FFT, diagonalization, integral and sparse-solver kernels. The repository continues to provide validated adapters, control-plane generation, parsers, scientific checks and evidence qualification.

## 12. Reusable continuation protocol

The new master prompt is stored at:

`docs/TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_MASTER_PROMPT_V2.md`

It requires future executions to:

- start from the latest `main`;
- inventory all executable code;
- build a formula/unit/reference-state ledger;
- close exact-type and non-finite gates;
- audit numerical stability before acceleration;
- record complexity changes;
- require profile evidence for native/GPU code;
- distinguish simulation, repository CPU measurement, real GPU measurement and external DFT-engine measurement;
- pass every stage's own permanent CI before continuing.

## 13. Evidence and repository-operation confirmation

```text
PHASE_6_PERFORMANCE_EVIDENCE_NUMERICS: COMPLETE
LOSSY_INTEGER_COERCION: CLOSED
NONFINITE_SCIENTIFIC_OBSERVABLES: FAIL_CLOSED
NONFINITE_PERFORMANCE_STATISTICS: FAIL_CLOSED
NONFINITE_SPEEDUP_QUALIFICATION: BLOCKED
ENERGY_PROFILE_FINITE_VALUE_GATE: PASS
ENERGY_PROFILE_REFERENCE_STATE_GATE: PASS
ENERGY_PROFILE_ATOMIC_BUNDLE_OUTPUT: IMPLEMENTED
VALIDATED_IMPLEMENTATION_CI: PASS
TESTS: 450
STATEMENT_COVERAGE: 94.13%
BRANCH_COVERAGE: 83.42%
REAL_DFT_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
REAL_EDGE_BENCHMARK: NOT_AVAILABLE
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
BRANCH_CREATED: NO
PULL_REQUEST_CREATED: NO
FORCE_PUSH: NO
HISTORY_REWRITE: NO
QUALITY_GATE_REDUCTION: NO
TEST_DELETION: NO
FABRICATED_PERFORMANCE_CLAIM: NO
```
