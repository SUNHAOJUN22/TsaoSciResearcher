# TSAO performance technology review

Date: 2026-07-27  
Frozen performance baseline: `0.1.0-alpha.10` / `3069e2bce162a361f9dadda7635206804581a6aa`

Execution audit baseline: remote `main` / `92150eac35ded7eb001a261c8a05e21de4e01070`

Promotion orchestration commit: `44028e32ffae51a5747b155df69acbb13f92a5a4`
Scope: software performance and numerical reproducibility only

This review records the primary technical sources consulted for the second performance pass. It does not claim exhaustive indexing of the public internet. Priority was given to official project documentation and peer-reviewed numerical-modeling literature.

## Decision matrix

| Technology | Primary source | Relevant TSAO workload | Decision for this pass | Expected value | Cost / compatibility | Fail-safe fallback |
|---|---|---|---|---|---|---|
| NumPy broadcasting and ufuncs | [NumPy user guide](https://numpy.org/doc/stable/user/), including broadcasting and copies/views | EPDM temperature, residence-time, active-site and propagation-parameter scenario grids | **Adopt in the base package** | Removes Python dispatch across hundreds or thousands of independent screening scenarios | NumPy is already a required dependency; array shape and finite-value contracts must be explicit | Retain scalar reference functions and compare every batch result against them |
| Accurate exponential transforms | [NumPy mathematical functions](https://numpy.org/doc/stable/reference/routines.math.html) | `1 - exp(-x)` conversion calculations at small `x` | **Adopt where batch arrays are introduced** | `expm1` avoids cancellation while remaining vectorized | No new dependency; output may differ by floating-point rounding from the scalar expression | Tolerance-based parity plus monotonic/bounds tests; scalar API remains unchanged |
| SciPy adaptive ODE solvers and sparse Jacobians | [SciPy `solve_ivp`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html) | Future stiff EPDM/POE dynamic systems, PBM and recycle models | **Evaluate as an optional extra; do not force into base install yet** | Radau/BDF and `jac_sparsity` can materially reduce work for stiff sparse systems | Adds SciPy and solver-selection complexity; current reference kernels are small explicit systems | Preserve deterministic RK4 reference; add SciPy only after representative stiffness benchmarks and tolerance qualification |
| Numba no-Python compilation | [Numba performance tips](https://numba.readthedocs.io/en/stable/user/performance-tips.html) | Long POE RK4 loops, semibatch trajectories, large independent scans | **Benchmark as a future optional backend; not adopted in base package** | Native loops and optional `prange` may accelerate long homogeneous workloads | JIT warm-up, additional wheel/platform matrix, type restrictions; `fastmath` can change IEEE behavior | Keep pure Python/NumPy backend authoritative; never enable `fastmath` without separate numerical qualification |
| Numba parallel loops | [Numba automatic parallelization](https://numba.readthedocs.io/en/stable/user/parallel.html) | Embarrassingly parallel Monte Carlo or parameter scans | **Deferred** | CPU parallelism without the GIL for large, uniform batches | Scheduling overhead can dominate small jobs; mutable containers are unsafe in `prange` | Use serial NumPy for small batches and require crossover benchmarks before parallel activation |
| JAX `vmap` + `jit` | [JAX automatic vectorization](https://docs.jax.dev/en/latest/automatic-vectorization.html) and [JAX quickstart](https://docs.jax.dev/en/latest/quickstart.html) | Differentiable parameter estimation, very large batched twins, accelerator execution | **Research adapter only; not a runtime dependency** | Automatic batching, autodiff and XLA compilation can support large gradient-based workflows | Large dependency surface, compilation latency, dtype/device semantics and three-platform support burden | Keep NumPy arrays as the interchange boundary; a JAX adapter must reproduce scalar and batch digests within declared tolerance |
| Process-based parallelism | [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html) | Independent experiments, Monte Carlo cases and package comparisons | **Deferred until batch size justifies serialization cost** | Uses multiple CPU cores and avoids the GIL | Spawn behavior differs across platforms; inputs and results must be serializable | Default serial/vectorized path; explicit worker count and deterministic ordering if later added |
| Shared memory | [Python shared memory](https://docs.python.org/3/library/multiprocessing.shared_memory.html) | Large read-only parameter arrays shared across worker processes | **Deferred** | Avoids repeated serialization and copying for large arrays | Lifecycle cleanup and Windows/POSIX differences increase operational risk | Use ordinary NumPy arrays until profiling proves inter-process copies are dominant |
| GitHub dependency caching | [GitHub dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching) | Cross-platform qualification and optional backend matrices | **Retain and tighten** | Reduces repeated package downloads on clean hosted runners | Cache keys must follow dependency files; caches are not test evidence | A cache miss must only increase runtime, never change correctness or qualification results |
| Population-balance moment/sectional methods | Ramkrishna & Singh, [Population Balance Modeling](https://doi.org/10.1146/annurev-chembioeng-060713-040241); Shiea et al., [PBE–CFD numerical methods](https://doi.org/10.1146/annurev-chembioeng-092319-075814) | Future MWD/CCD/LCB and multiphase PBM extensions | **Roadmap, not fabricated implementation** | Moment and quadrature methods can control state dimension compared with full distributions | Closure assumptions and validation evidence are model-specific | Keep current chain-moment references explicitly labeled as references until a PBM is implemented and benchmarked |
| Polymerization PBE computation | Kiparissides et al., [particulate polymerization population-balance perspective](https://doi.org/10.1016/j.jprocont.2005.06.004) | Future polymer molecular/morphological distributions and online estimation | **Use as architecture guidance only** | Confirms that discretization and dynamic-PBE solution method dominate computational cost | Does not provide EPDM-specific calibrated parameters | No claim of implemented PBM or industrial predictive capability |
| Digital-twin uncertainty and online model maintenance | [Integrated chemical-engineering digital-twin framework](https://doi.org/10.1016/j.compchemeng.2025.109178); [online parameter estimation and model maintenance](https://doi.org/10.1016/j.compchemeng.2025.109403) | Active learning, online parameter updating and uncertainty-aware twins | **Use to define interfaces and evidence gates, not to claim online validation** | Supports future reduced-order, adaptive and uncertainty-aware execution | Requires live data, online validation and accountable model governance | Keep all current digital-twin claims at reference/interface level until project data are supplied |

## Current pass priorities

1. Expand the benchmark surface before changing the numerical code.
2. Add a true NumPy batch-screening API for EPDM scenario grids while retaining scalar references.
3. Replace remaining POE RK4 dataclass/object churn with a fixed-state internal representation.
4. Add a validated EPDM semibatch trajectory API so 10,000-step studies validate invariants once rather than at every public call boundary.
5. Record peak traced memory and warm-up counts in addition to timing and `cProfile` data.
6. Preserve deterministic ordering, result identity, balance residuals and all `HOLD` / `FAIL` / `NOT_EVALUATED` semantics.

## Explicit non-adoptions

- `fastmath` is not accepted because reassociation and relaxed IEEE rules can change scientific results.
- GPU execution is not claimed because no accelerator qualification is part of this source release.
- SciPy, Numba, JAX, Diffrax, Cython and Rust are not added to base dependencies without representative crossover benchmarks and clean installation evidence on Linux, Windows and macOS.
- Parallel execution is not enabled merely because a workload is independent; process start-up, data transfer and deterministic result ordering must be measured first.

## Qualification boundary

The sources above justify candidate algorithms and implementation choices. They do not provide EPDM parameters, validate a reactor model, approve equipment, close HAZOP/LOPA/SIL work, qualify customer performance or establish an industrial guarantee. Those states remain `NOT_EVALUATED`.


## Additional official-source checks

- CPython free-threading, Cython, PyPy, Numba, JAX and process parallelism remain deferred pending separate crossover and three-platform qualification.
- BLAS thread controls remain deployment tuning, not a package default.
- Pinned Actions, artifact v4, dependency caches and read-only permanent permissions are retained; caches are not evidence.
