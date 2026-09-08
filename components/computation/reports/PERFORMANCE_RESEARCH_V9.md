# Performance engineering V9 — technical research ledger

## Scope and claim boundary

This ledger supports the current-main V9 rerun that froze execution-start `main` at `04ce646e51a603faf8cfad72ec15e218e09a0ebd`. Research was intentionally broad but is not represented as an exhaustive crawl of the internet. Primary documentation, release notes, project design guidance, and repository-local measurements were preferred over secondary commentary.

All accepted claims are limited to TsaoSciComputation startup, registry, routing, adapter probing, output parsing, repository traversal, validation, packaging, and CI orchestration. External DFT, MD, CFD, FEM, process simulators, licensed engines, production clusters, and scientific accuracy are outside the performance claim boundary.

## Measurement principles adopted

1. Compare baseline and candidate worktrees on one runner with the same Python executable, dependency environment, environment variables, filesystem class, and benchmark harness.
2. Separate microbenchmarks from end-to-end verification. A microsecond-level route or parser result is never presented as solver or HPC acceleration.
3. Warm each workload, run independent repetitions and batch loops, and report median, minimum, p90, standard deviation, and coefficient of variation. Retain wall time, CPU time, peak RSS, filesystem I/O, and subprocess-count evidence when the platform exposes them.
4. Treat runner-level frequency variation and cross-runner comparisons as telemetry only. Do not use the fastest sample as the accepted result.
5. Profile before optimizing. Roll back changes that do not produce stable benefit or that add complexity without measurable value.

## Python and CPython findings

- `functools.cache` and `lru_cache` are appropriate only for bounded or trusted input domains. Repeated user questions therefore use a bounded cache with explicit registry invalidation rather than an unbounded cache.
- `os.scandir()` exposes directory-entry metadata and underpins modern `os.walk()` performance. Repository traversal should avoid repeated path conversion, sorting, and `stat()` where semantics allow, while preserving global deterministic order.
- `hashlib` can release the GIL for sufficiently large update buffers. Controlled threads can therefore help large-file hashing or copying, but only when storage behavior and pool startup are measured; output ordering and exception propagation remain serial and deterministic.
- `ThreadPoolExecutor` is appropriate for isolated I/O-bound work. CPU-bound Python parsing is not moved to threads merely because threads exist; process pools add startup, serialization, and cross-platform start-method costs.
- `cProfile`, `pstats`, and `tracemalloc` are diagnostic tools whose own overhead is separated from acceptance timing. Profiling workloads are executed from temporary scripts so the command line remains portable across supported Python versions.
- CPython 3.10 through 3.14 contain meaningful import, I/O, interpreter, and standard-library changes. Those differences justify a cross-version telemetry matrix, not a mixed-version speedup claim. The hard A/B comparison therefore uses one Python version.

## Benchmarking findings

The pyperf methodology reinforces calibration, warmup, repeated worker processes, metadata capture, and system-noise awareness. V9 keeps an optional standard-library harness so the project retains zero mandatory runtime dependencies; pyperf remains a documented developer option rather than a release dependency. Microbenchmark and end-to-end reports are stored separately and joined only by a comparison report with explicit acceptance thresholds.

## GitHub Actions findings

- Dependency caches are recoverable accelerators, not evidence. Cache keys must include the operating system, Python version, dependency inputs, and relevant tool versions; a miss must regenerate safely.
- Workflow artifacts are the correct mechanism for immutable reports, logs, wheels, SBOMs, and job-to-job evidence. They are not interchangeable with dependency caches.
- Workflow concurrency is used to cancel obsolete runs that target the same mutable branch, reducing queue noise without suppressing the latest validation.
- Actions are pinned by commit SHA, permissions are minimal, checkout depth is selected by need, and credentials are disabled for read-only CI jobs.
- Evidence reuse is accepted only when its key binds commit SHA, OS, Python, dependency inputs, and tool versions. A prior commit's test or benchmark report cannot accept a new commit.

## Scientific-workflow project findings

Mature workflow systems such as Dask, Parsl, Snakemake, FireWorks, AiiDA, Prefect, and Airflow demonstrate that scheduling is not free. Dask documents per-task overhead and recommends larger units of work, fusion, and smaller graphs. V9 applies that lesson narrowly: it parallelizes only independent, coarse tasks with isolated outputs and keeps pool sizes bounded. It does not add a distributed scheduler or workflow runtime dependency to accelerate a repository whose hot paths are local and short-lived.

Scientific packages such as ASE, pymatgen, MDAnalysis, OpenMM, NumPy, and SciPy also reinforce lazy optional integration, vectorized native kernels, explicit thread-safety boundaries, and benchmark suites tied to real workloads. TsaoSciComputation does not imitate their solver kernels; it adopts only matching orchestration practices that can be verified locally.

## Optimizations selected for candidate measurement

1. **Fail-closed output parsing:** retain the existing authoritative failure regular expression and failure-first precedence. Use a complete folded-literal cue prefilter to avoid the expensive multi-alternative failure scan for ordinary success or no-status logs. The full file is still scanned for accepted status semantics; no tail-only shortcut is introduced.
2. **Coverage analysis de-duplication:** execute the test suite under Coverage once, load the generated data once, emit the JSON evidence once, and enforce the unchanged 95% threshold from that same analysis.
3. **Deterministic wheel verification I/O:** create two isolated source snapshots with a bounded two-worker thread pool, build the two wheels independently, compare byte hashes, install with pip in an isolated target, and import from that target. Suppress only bytecode compilation that is irrelevant to the install contract.
4. **Measurement infrastructure:** cover startup/imports, cold and cached registries, multilingual route batches, adapter worker counts, 1 KiB through 50 MiB parser matrices, repository traversal, Manifest, security scan, repository audit, all verification profiles, pytest, CPU, RSS, filesystem I/O, and cProfile attribution.

## Explicitly rejected or deferred

- Tail-only parsing, shortened safety scans, reduced rules, warning-only failures, reduced coverage, reduced mutation gates, or reduced scientific benchmarks.
- Unbounded user-input caches or persistent executable-probe caches without PATH and environment invalidation.
- Mandatory third-party JSON, regex, scheduler, or profiling runtime dependencies for small synthetic gains.
- Broad thread/process fan-out, nondeterministic result ordering, swallowed worker exceptions, or parallel tasks that write the same directory.
- Cross-runner, cross-version, or best-sample comparisons represented as speedups.
- Cached evidence reused across commits, or README claims generated before the machine-readable comparison passes.
- Changes that optimize only the benchmark generator rather than the production call path.

## Primary source ledger

- Python documentation — `functools`: https://docs.python.org/3/library/functools.html
- Python documentation — `os.scandir` / `os.walk`: https://docs.python.org/3/library/os.html
- Python documentation — `hashlib`: https://docs.python.org/3/library/hashlib.html
- Python documentation — `concurrent.futures`: https://docs.python.org/3/library/concurrent.futures.html
- Python documentation — `cProfile` / `pstats`: https://docs.python.org/3/library/profile.html
- Python documentation — `tracemalloc`: https://docs.python.org/3/library/tracemalloc.html
- Python release notes, 3.10–3.14: https://docs.python.org/3/whatsnew/
- pyperf documentation: https://pyperf.readthedocs.io/
- Coverage.py command-line and JSON reporting: https://coverage.readthedocs.io/
- GitHub Actions dependency caching: https://docs.github.com/actions/using-workflows/caching-dependencies-to-speed-up-workflows
- GitHub Actions workflow artifacts: https://docs.github.com/actions/concepts/workflows-and-actions/workflow-artifacts
- GitHub Actions concurrency: https://docs.github.com/actions/using-jobs/using-concurrency
- GitHub Actions workflow syntax and permissions: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions
- Dask best practices: https://docs.dask.org/en/stable/best-practices.html
- Snakemake documentation: https://snakemake.readthedocs.io/
- Parsl documentation: https://parsl.readthedocs.io/
- AiiDA documentation: https://aiida.readthedocs.io/
- MDAnalysis documentation: https://docs.mdanalysis.org/
- NumPy CPU/SIMD and thread-safety documentation: https://numpy.org/doc/stable/reference/

## Evidence rule

A technique listed here is not a performance result. Only `PERFORMANCE_BASELINE_V9.json`, `PERFORMANCE_CANDIDATE_V9.json`, and a passing `PERFORMANCE_COMPARISON_V9.json` produced by the same-host audit may support numeric README claims. The final documented tree must then pass the full deterministic release gates and canonical cross-platform CI.
