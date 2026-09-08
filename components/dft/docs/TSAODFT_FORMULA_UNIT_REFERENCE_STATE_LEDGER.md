# TsaoDFT Formula, Unit and Reference-State Ledger

**Repository:** `SUNHAOJUN22/TsaoDFT_skill`  
**Scope:** validated scientific formulas, numerical reductions, performance mathematics and reference-state contracts implemented through Phase 6  
**Evidence boundary:** this ledger documents repository logic and tests; it is not real DFT-engine or GPU performance evidence.

## 1. Ledger conventions

Each entry records:

- the implemented mathematical relationship;
- input and output units;
- the reference or standard state;
- the main numerical hazard;
- the protection implemented in the repository;
- the validation evidence currently available.

Status values:

- `VALIDATED`: implementation and direct regression tests pass permanent CI;
- `VALIDATED_WITH_SCOPE_LIMIT`: formula is validated for the declared repository scope but does not establish external-engine physical validity beyond the supplied inputs;
- `PROFILE_GATED`: correctness is retained, but further acceleration depends on representative profiling;
- `REAL_EVIDENCE_REQUIRED`: the formula is implemented, but a real performance or hardware claim requires additional evidence.

## 2. Kinetics and thermodynamics

### F-001 — Eyring transition-state-theory rate

| Field | Contract |
|---|---|
| Module | `skills/tsao-dft-kinetics-multiscale/scripts/tst_math.py` |
| Formula | `k = κ g (k_B T / h) exp[-ΔG‡/(R T)]` |
| Barrier input | `kcal/mol` |
| Internal barrier | `J/mol`, using `4184 J/kcal` |
| Temperature | K |
| Output | rate; first-order default reported as `s^-1` |
| Reference/standard state | molecularity-dependent; bimolecular and higher-order results require the declared concentration standard-state convention |
| Main hazards | kcal/cal mismatch; exponential overflow/underflow; bool/NaN/Inf inputs; non-positive temperature, κ or degeneracy |
| Protection | shared SI constants; log-rate calculation; explicit overflow/underflow boundary; finite positive input contracts |
| Independent reference | 15 kcal/mol at 298.15 K gives `62.83270649519368 s^-1` for κ = g = 1 |
| Status | `VALIDATED` |

### F-002 — TST barrier-uncertainty interval

| Field | Contract |
|---|---|
| Module | `tst_math.py`, `propagate_barrier_uncertainty.py` |
| Relationship | evaluate `ΔG‡ - u`, `ΔG‡`, and `ΔG‡ + u` in log-rate space |
| Barrier and bound | `kcal/mol` |
| Temperature | K |
| Output | lower, central and upper rates plus log rates |
| Assumption | symmetric declared activation-free-energy bound only |
| Explicit exclusion | does not automatically include model-form, transport, tunneling-model or standard-state uncertainty |
| Main hazards | asymmetric linear-rate interpretation; negative uncertainty; exponential overflow |
| Protection | non-negative finite bound; symmetric interval in log rate; explicit note in output |
| Status | `VALIDATED_WITH_SCOPE_LIMIT` |

### F-003 — Molecularity-dependent rate unit

| Molecularity | Unit contract |
|---:|---|
| 1 | `s^-1` |
| 2 | `M^-1 s^-1` with standard-state convention required |
| n > 2 | `concentration^(1-n) s^-1` |

Molecularity must be a positive exact integer. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

### F-004 — Forward/reverse thermodynamic closure

| Field | Contract |
|---|---|
| Module | `skills/tsao-dft-kinetics-multiscale/scripts/check_thermodynamic_closure.py` |
| Formula | `ΔG‡reverse = ΔG‡forward - ΔGreaction` |
| Input unit | inherited from the network `energy_unit`; all three values must use the same unit |
| Output | expected reverse barrier and closure residual |
| Reference state | the reaction and both barriers must share the same thermodynamic reference and method identity supplied by the network |
| Main hazards | sign reversal; NaN/Inf; bool values; missing barriers; negative/non-finite tolerance; cancellation |
| Protection | finite numeric contracts; exact boolean reversible flag; `math.fsum` for expected value and residual; structured failure |
| Status | `VALIDATED_WITH_SCOPE_LIMIT` |

## 3. Energy and reference-state calculations

### F-005 — Relative electronic/free-energy profile

| Field | Contract |
|---|---|
| Module | `skills/tsao-dft-researcher/scripts/build_energy_profile.py` |
| Formula | `ΔE_i(kcal/mol) = (E_i(Hartree) - E_ref(Hartree)) × 627.5094740631` |
| Input | Hartree |
| Output | kcal/mol |
| Allowed reference | first row, minimum energy, or one unique explicit label |
| Main hazards | non-finite totals; duplicate labels; ambiguous reference; catastrophic loss from close large totals; partial output publication |
| Protection | finite input gate; unique labels; explicit reference validation; `math.fsum((E_i, -E_ref))`; staged four-file publication |
| Status | `VALIDATED` |

The generated CSV, SVG, PDF and PNG form one output bundle. A figure-generation failure must not publish a new partial bundle.

### F-006 — Energy-expression coefficient classification

| Field | Contract |
|---|---|
| Module | `skills/tsao-periodic-dft-materials/scripts/check_energy_compatibility.py` |
| Relationship | the coefficient sum distinguishes total-energy-like expressions from balanced energy differences according to the declared quantity |
| Units | coefficients are dimensionless; all terms must share compatible energy units and method fingerprints |
| Main hazards | cancellation in large positive/negative coefficient sequences; mixed method identities |
| Protection | `math.fsum`; method-fingerprint validation |
| Status | `VALIDATED_WITH_SCOPE_LIMIT` |

## 4. Regression and statistical metrics

### F-007 — Ridge regression with unpenalized intercept

| Field | Contract |
|---|---|
| Module | `skills/tsao-dft-ml-active-learning/scripts/train_ridge_baseline.py` |
| Centering | `X_c = X - mean(X)`, `y_c = y - mean(y)` |
| Primal | `(X_c^T X_c + αI) β = X_c^T y_c` |
| Dual | `(X_c X_c^T + αI) a = y_c`, `β = X_c^T a` |
| Intercept | `b = mean(y) - mean(X)^T β` |
| α | finite, non-negative |
| Solver selection | auto chooses dual when features > samples, otherwise primal |
| α = 0 | stable least-squares on the design matrix |
| Main hazards | penalized or incorrect intercept; explicit inverse; unnecessarily large linear system; identity allocation; NaN/Inf |
| Protection | centering; `solve`/`lstsq`; smaller-system selection; direct diagonal update; finite shape contracts |
| Status | `VALIDATED` |

The NumPy implementation delegates dense linear algebra to compiled BLAS/LAPACK. A repository C++ rewrite is `PROFILE_GATED`.

### F-008 — Mean absolute error

`MAE = mean(|ŷ - y|)`

Inputs must be aligned, non-empty, one-dimensional and finite. Status: `VALIDATED`.

### F-009 — Root mean square error

`RMSE = sqrt(((ŷ - y)^T(ŷ - y)) / N)`

Inputs follow F-008. Status: `VALIDATED`.

### F-010 — Coefficient of determination

`R² = 1 - SSE/SST`, where `SST = (y - mean(y))^T(y - mean(y))`.

When `SST = 0`, the repository returns no scalar R² rather than fabricating a value. Status: `VALIDATED`.

### F-011 — Median, quartiles, IQR and MAD

| Metric | Definition/contract |
|---|---|
| median | deterministic median of finite values |
| Q1/Q3 | linear interpolation at 0.25/0.75 over sorted finite values |
| IQR | `Q3 - Q1` |
| MAD | median absolute deviation from the median |
| modified z-score | `0.6745 (x - median) / MAD` when MAD > 0 |

Outliers are counted and retained; they are not silently deleted. The threshold must be finite and positive. Status: `VALIDATED`.

## 5. Uncertainty aggregation

### F-012 — Root-sum-square uncertainty

| Field | Contract |
|---|---|
| Module | `skills/tsao-dft-researcher/scripts/validate_uncertainty_budget.py` |
| Formula | `u_RSS = hypot(u_1, u_2, ..., u_n)` |
| Assumption | appropriate only for the declared independent-component aggregation rule |
| Main hazard | intermediate overflow from `sqrt(sum(u_i²))` |
| Protection | `math.hypot` |
| Status | `VALIDATED_WITH_SCOPE_LIMIT` |

### F-013 — Linear summed bound

`u_sum = math.fsum(u_i)`

This is a declared conservative summed-bound rule, not a covariance model. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

### F-014 — Separate reporting

When the aggregation rule is `report_separately`, no combined scalar is created. Status: `VALIDATED`.

## 6. Convergence mathematics

### F-015 — Absolute adjacent convergence difference

| Field | Contract |
|---|---|
| Module | `skills/tsao-periodic-dft-materials/scripts/analyze_convergence.py` |
| Difference | `d_i = |observable_i - observable_(i-1)|` after deterministic sorting by control value |
| Candidate criterion | the complete requested tail contains differences no greater than the finite non-negative absolute threshold |
| Reference | the recommended value is the final control value in the validated ordered series |
| Main hazards | undersized tail accepted; missing columns; non-finite values; invalid threshold; duplicate/unsorted controls |
| Protection | full-tail requirement; finite contracts; structured CSV validation; pairwise pass |
| Status | `VALIDATED_WITH_SCOPE_LIMIT` |

This is an absolute-threshold convergence rule. A relative or multi-observable scientific convergence criterion must be declared separately rather than inferred.

## 7. Geometry reductions

### F-016 — Atom-mapping displacement

For mapped coordinates `r_i` and `r'_i`:

`d_i = ||r'_i - r_i||₂`

The implementation uses NumPy vectorized coordinate differences and norm reduction. Coordinates must be finite. Status: `VALIDATED`.

### F-017 — RMSD

`RMSD = sqrt(mean(d_i²))`

The current mapping RMSD is computed for the declared mapping and coordinate frame; it is not an automatic rotational/translation alignment unless supplied by the surrounding workflow. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

### F-018 — Maximum displacement

`d_max = max(d_i)`

Status: `VALIDATED`.

### F-019 — Pair distance

`d_ij = hypot(Δx, Δy, Δz)`

The NumPy backend uses a vectorized hypot reduction. Periodic minimum-image semantics must be supplied by modules that explicitly support periodic cells; they are not inferred for generic XYZ. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

## 8. Performance and scaling mathematics

### F-020 — CPU-to-candidate speedup

| Field | Contract |
|---|---|
| Module | `skills/tsao-dft-hpc-provenance/scripts/performance_evidence.py` |
| Formula | `S_CPU = median(t_reference) / median(t_candidate)` |
| Preconditions | finite positive medians; sufficient eligible repeats; consistent identities; verified artifacts; numerical equivalence PASS |
| Main hazards | NaN comparison bypass; zero/negative time; fastest-run cherry-picking; non-equivalent science |
| Protection | finite positive checks; median; all failures retained; qualification gates |
| Status | `VALIDATED_WITH_SCOPE_LIMIT` |

A computed repository speedup does not by itself prove external DFT-engine or GPU acceleration.

### F-021 — Single-GPU-to-candidate scaling speedup

`S_N = median(t_single_gpu) / median(t_N_gpu)`

The single-GPU baseline must be a qualified compatible candidate. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

### F-022 — Strong-scaling efficiency

`η_N = S_N / (N / N_base)`

Preconditions include compatible topology, finite positive times and nonzero GPU counts. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

### F-023 — GPU hours

`GPU_hours = median_wall_time_s × total_GPU_count / 3600`

Status: `VALIDATED_WITH_SCOPE_LIMIT`.

### F-024 — CPU core hours

`CPU_core_hours = median_wall_time_s × nodes × ranks_per_node × threads_per_rank / 3600`

Nodes, ranks and threads must be positive exact integers. Invalid topology produces no fabricated resource total. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

## 9. Profiler and scheduler-unit conversions

### F-025 — Duration conversion

Supported forms:

- integer seconds;
- `MM:SS`;
- `HH:MM:SS`;
- `D-HH:MM:SS`.

Minutes/seconds ranges, finite values and non-negative day components are validated. Status: `VALIDATED`.

### F-026 — Memory conversion

Scheduler memory values use binary factors:

- K = 1 KiB;
- M = 1024 KiB;
- G = 1024² KiB;
- T = 1024³ KiB.

Overflow and malformed values return unavailable. Status: `VALIDATED`.

## 10. Identity and equivalence reference states

### F-027 — Scientific identity

A performance comparison is bound to a canonical identity containing:

- engine name and version;
- input SHA-256;
- method fingerprint;
- model identity;
- convergence thresholds;
- sorted observable set.

Candidate and reference identities must match. Status: `VALIDATED`.

### F-028 — Numerical-equivalence maxima

The repository records maximum absolute deviations for:

- energy in eV;
- forces in eV/Å;
- stress in GPa;
- named task-specific properties.

Every tolerance must be finite and non-negative. Missing, incompatible or non-finite observables fail the gate. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

The physical appropriateness of each tolerance remains task- and method-specific and must be reviewed for real evidence campaigns.

## 11. Hashing and provenance

### F-029 — SHA-256 content identity

Files are hashed incrementally in chunks. Large files are not required to be loaded into memory. Status: `VALIDATED`.

### F-030 — Evidence-bundle identity

Canonical JSON and artifact checksums bind retained records, summaries and qualification reports. A content digest establishes identity and tamper detection; it does not establish scientific truth by itself. Status: `VALIDATED_WITH_SCOPE_LIMIT`.

## 12. Remaining formula/reference-state work

| Area | Remaining requirement | Status |
|---|---|---|
| real VASP/QE/CP2K/Gaussian benchmarks | task-specific scientific tolerances and actual hardware/build records | `REAL_EVIDENCE_REQUIRED` |
| Gaussian large-log parser | representative files and profile before changing parsing architecture | `PROFILE_GATED` |
| periodic geometry/neighbor lists | explicit cell and minimum-image contracts for future high-volume paths | `PROFILE_GATED` |
| higher-order kinetic rates | explicit concentration standard state and activity convention | `REAL_EVIDENCE_REQUIRED` |
| correlated uncertainty | covariance/correlation model rather than RSS | `REAL_EVIDENCE_REQUIRED` |
| GPU/native kernels | reference implementation, end-to-end profile and equivalence tests | `PROFILE_GATED` |

## 13. Ledger status

```text
FORMULA_LEDGER_CREATED: YES
DIMENSIONAL_CONTRACTS_RECORDED: YES
REFERENCE_STATE_CONTRACTS_RECORDED: YES
CRITICAL_TST_UNIT_DEFECT: RESOLVED
RIDGE_INTERCEPT_FORMULATION: RESOLVED
NONFINITE_PERFORMANCE_MATH: FAIL_CLOSED
REAL_DFT_PHYSICAL_VALIDATION: NOT_CLAIMED
REAL_GPU_PERFORMANCE_VALIDATION: NOT_AVAILABLE
```
