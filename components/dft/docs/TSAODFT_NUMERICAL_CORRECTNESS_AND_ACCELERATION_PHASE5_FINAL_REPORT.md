# TsaoDFT Numerical Correctness and Acceleration Phase 5 Final Report

**Program:** `TSAODFT_ACCELERATION_ARCHITECTURE_AUDIT_AND_IMPLEMENTATION_V1`  
**Phase:** 5 — mathematical-program audit, numerical correctness and algorithmic efficiency  
**Starting HEAD:** `1f1a594a56a8444756c23132a4e6ad7cad72483f`  
**Validated implementation HEAD:** `c059fb7746ecd248b4b551311c870e677108c39f`  
**Validated GitHub Actions run:** `30712101094`  
**Evidence boundary:** `NOT_REAL_DFT_BENCHMARK / NOT_REAL_GPU_BENCHMARK / NOT_PERFORMANCE_EVIDENCE`

## 1. Executable-code audit scope

The final Python 3.12 coverage artifact contains:

- **158 Python files**;
- **93 production files**;
- **65 test files**;
- **10,196 production executable statements**;
- **4,480 production branches**.

The numerical audit prioritized code that implements equations, statistics, solvers, convergence decisions, uncertainty propagation, geometry reductions and scientific acceptance checks. Workflow routing, schemas, evidence state machines and scheduler generation were reviewed as control-plane code but were not rewritten merely because they are written in Python.

The expensive Kohn–Sham, FFT, diagonalization, integral and sparse-matrix kernels remain in native VASP, Quantum ESPRESSO, CP2K and Gaussian binaries. This phase therefore improves repository mathematics and data-path efficiency; it does not claim to accelerate the external electronic-structure engines.

## 2. Critical Eyring/TST unit correction

### 2.1 Defect

`eyring_rates.py` and `propagate_barrier_uncertainty.py` labelled activation free energies as `kcal/mol` while dividing directly by a gas constant expressed in `cal/(mol K)`. The missing factor of 1000 made the exponential term dimensionally inconsistent.

For a 15 kcal/mol barrier at 298.15 K, the former expression produced approximately `6.057131337546743e12 s^-1`, while the dimensionally correct SI expression gives approximately `62.83270649519368 s^-1`, a difference of about `9.64e10`.

### 2.2 Correction

Added shared `tst_math.py` using:

```text
k = κ g (k_B T / h) exp[-ΔG‡/(R T)]
ΔG‡: kcal/mol → J/mol through 4184 J/kcal
R = 8.31446261815324 J/(mol K)
```

The implementation now:

- evaluates the equation through a log-rate representation;
- rejects booleans, nonnumeric inputs and NaN/Inf values;
- rejects nonpositive temperature, transmission coefficient and degeneracy;
- handles floating-point overflow and underflow explicitly;
- computes symmetric barrier-uncertainty intervals in log-rate space;
- validates molecularity and rate-unit branches.

An independent SI regression test fixes the 15 kcal/mol, 298.15 K reference value at `62.83270649519368 s^-1`.

## 3. Eyring CSV scalability and output safety

`eyring_rates.py` was changed from complete-table materialization to row streaming. It now:

- reads and validates rows incrementally;
- writes to a temporary file;
- deletes incomplete output after any failure;
- atomically publishes only a complete CSV;
- returns structured JSON errors instead of an uncaught traceback;
- preserves deterministic row order.

This reduces retained memory from `O(rows)` to bounded row state plus CSV buffers. It is an algorithmic scalability improvement, not a measured DFT-engine speedup.

## 4. Ridge-regression mathematical correction and efficiency

`train_ridge_baseline.py` previously used an intercept based on the target mean while solving coefficients against uncentered features. That is not the correct unpenalized-intercept ridge solution when feature means are nonzero.

The corrected implementation:

1. centers training features and targets;
2. chooses the smaller primal or dual system;
3. adds regularization directly to the Gram-matrix diagonal rather than allocating a separate identity matrix;
4. computes the intercept as:

```text
intercept = target_mean - feature_mean @ coefficients
```

5. rejects empty dimensions, NaN/Inf matrices and nonfinite or negative `alpha`;
6. uses direct dot-product definitions for squared error and total variation.

Tests verify:

- primal/dual prediction equivalence;
- automatic smaller-system selection;
- feature-translation invariance of the unpenalized intercept;
- stable least-squares behavior at `alpha = 0`;
- no identity-matrix allocation in the regularized path;
- direct MAE/RMSE/R² agreement.

NumPy continues to call compiled BLAS/LAPACK. Rewriting this solver in repository C++ would duplicate optimized native numerical libraries without demonstrated end-to-end benefit.

## 5. Stable uncertainty aggregation

`validate_uncertainty_budget.py` now uses:

- `math.hypot` for root-sum-square aggregation, avoiding intermediate squaring overflow;
- `math.fsum` for summed uncertainty bounds, reducing cancellation and accumulation error.

Tests include values near `1e308` and verify that the RSS result remains finite when the mathematically correct result is representable.

## 6. Convergence-analysis correctness

`analyze_convergence.py` was hardened to:

- reject missing headers and columns;
- reject extra CSV fields;
- reject malformed and nonfinite values;
- sort convergence points by control value;
- reject NaN/negative thresholds and invalid tail counts;
- require the complete requested tail rather than accepting an undersized suffix;
- use `itertools.pairwise` for a direct adjacent-difference pass;
- return structured result codes for invalid, unconverged and converged cases.

This prevents a short or malformed table from being incorrectly labelled converged.

`check_energy_compatibility.py` now uses `math.fsum` for coefficient totals, improving cancellation-sensitive checks of whether an expression is a total energy or an energy difference.

## 7. Thermodynamic-closure hardening

`check_thermodynamic_closure.py` retains the scientific relation:

```text
ΔG‡reverse = ΔG‡forward - ΔGreaction
```

but now:

- validates the document root and reaction collection types;
- requires a real boolean reversible flag;
- rejects booleans, missing values and NaN/Inf barriers;
- rejects negative or nonfinite tolerance;
- uses `math.fsum` for expected reverse barriers and closure residuals;
- reports malformed YAML and file failures as structured JSON;
- preserves irreversible-reaction skipping;
- records normalized expected, reported and residual values.

Direct tests cover valid closure, mismatch detection, malformed documents, invalid numerical values and malformed YAML.

## 8. Geometry-vectorization improvements

`validate_atom_mapping.py` now performs mapped coordinate displacement, RMSD and maximum-displacement reductions with NumPy arrays rather than one Python `math.dist` call per atom. A 2,000-atom test verifies that the scalar distance path is not used and that RMSD/max-displacement results remain correct.

`inspect_xyz.py` also uses a vectorized hypot reduction for NumPy pair-distance calculations. These changes accelerate repository geometry preprocessing, not the electronic-structure solver.

A future C++/OpenMP/Kokkos or GPU geometry backend remains conditional on realistic structure profiling and end-to-end benefit after Python/native conversion costs.

## 9. Changed paths

The Phase 5 implementation spans 29 sequential fast-forward commits and 16 changed paths:

- `skills/tsao-dft-kinetics-multiscale/scripts/check_thermodynamic_closure.py`
- `skills/tsao-dft-kinetics-multiscale/scripts/eyring_rates.py`
- `skills/tsao-dft-kinetics-multiscale/scripts/propagate_barrier_uncertainty.py`
- `skills/tsao-dft-kinetics-multiscale/scripts/tst_math.py`
- `skills/tsao-dft-kinetics-multiscale/tests/test_kinetics_depth.py`
- `skills/tsao-dft-kinetics-multiscale/tests/test_tst_numerics.py`
- `skills/tsao-dft-ml-active-learning/scripts/train_ridge_baseline.py`
- `skills/tsao-dft-ml-active-learning/tests/test_solver_efficiency.py`
- `skills/tsao-dft-researcher/scripts/validate_uncertainty_budget.py`
- `skills/tsao-dft-researcher/tests/test_uncertainty_numerics.py`
- `skills/tsao-periodic-dft-materials/scripts/analyze_convergence.py`
- `skills/tsao-periodic-dft-materials/scripts/check_energy_compatibility.py`
- `skills/tsao-periodic-dft-materials/tests/test_numerical_convergence.py`
- `skills/tsao-structure-prep/scripts/inspect_xyz.py`
- `skills/tsao-structure-prep/scripts/validate_atom_mapping.py`
- `skills/tsao-structure-prep/tests/test_acceleration_backends.py`

## 10. Tests and coverage

| Metric | Phase 4 baseline | Phase 5 validated implementation |
|---|---:|---:|
| Tests | 415 | **434** |
| Isolated suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 93.83% | **93.98%** |
| Branch coverage | 82.98% | **83.22%** |

Coverage initially reached 93.86% statement / 82.96% branch, which was below the Phase 4 branch baseline. The phase was not closed at that point. Business-meaningful tests were added for TST unit branches, malformed convergence inputs and thermodynamic-closure contracts until both coverage measures exceeded the baseline.

The six execution/trust cores remain unchanged:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

## 11. Permanent quality gate

The validated implementation commit passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint and formatting;
- mypy across 18 isolated targets;
- strict trust-boundary mypy across 4 targets;
- 434 tests across 9 suites;
- statement and branch coverage;
- Bandit production audit;
- strict repository audit;
- CodeQL Python analysis;
- runtime dependency audit;
- development dependency audit;
- exact locked-environment audit;
- CycloneDX SBOM generation and upload.

## 12. Remaining numerical and performance boundaries

This phase intentionally did not replace the large `performance_evidence.py` trust-boundary module. Existing Schema-facing routes already test rejection of noninteger benchmark identities, but a dedicated future audit should further tighten direct programmatic coercion and uniformly reject nonfinite scientific observables before any performance qualification.

Other remaining profile-gated candidates include:

- finite-value and large-table hardening of energy-profile generation;
- representative large Gaussian-log profiling;
- realistic trajectory and neighbour-list profiling;
- real VASP/QE/CP2K build and topology benchmarking;
- accepted equivariant-ML workloads before considering cuEquivariance or cuTENSOR;
- a narrow C++/OpenMP/Kokkos boundary only after measured end-to-end benefit.

No C++, CUDA, HIP or SYCL layer was introduced because this phase found correctness defects and Python/NumPy algorithmic improvements with higher immediate value and lower compatibility risk.

## 13. Evidence and repository-operation confirmation

```text
PHASE_5_NUMERICAL_AUDIT: COMPLETE
CRITICAL_TST_UNIT_DEFECT: CORRECTED
NUMERICAL_STABILITY_HARDENING: COMPLETE_FOR_SCOPED_MODULES
ALGORITHMIC_EFFICIENCY_IMPLEMENTATION: COMPLETE_FOR_SCOPED_MODULES
VALIDATED_IMPLEMENTATION_CI: PASS
COVERAGE_REGRESSION: CLOSED
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
```
