# TsaoDFT Performance Audit

- Audit date: 2026-07-27
- Frozen baseline: `27745b74c4bc1521a47e6d74c4795cce477460bb`
- Baseline status: 78 tests across 9 suites; Python 3.10/3.12/3.13 green
- Audit scope: 356 versioned files, 109 Python files and approximately 10,287 Python source lines in the working snapshot
- Benchmark host: Python 3.13.5, Linux x86_64
- Benchmark command: `python scripts/benchmark_performance.py --baseline-commit 27745b74c4bc1521a47e6d74c4795cce477460bb`

This audit measures Python, serialization, file-I/O and scheduler-artifact overhead. It does **not** measure or claim faster Gaussian, VASP, Quantum ESPRESSO or CP2K electronic-structure kernels.

## Implemented findings

| Hotspot | Previous implementation | Current implementation | Median time | Peak Python memory / artifact scale | Equality and scope | Risk |
|---|---|---|---:|---:|---|---|
| 64 MiB provenance/structure file hash | `read_bytes()` followed by SHA-256 | 1 MiB streaming SHA-256 chunks | 0.08044 s → 0.05030 s | 64.00 MiB → 2.00 MiB | Exact digest match; applies to provenance and structure files | More read calls; chunk size remains an implementation parameter |
| 50,000-row DFT dataset canonical hash | One complete `json.dumps(rows, sort_keys=True)` payload | Exact canonical JSON emitted in bounded 256-row batches | 0.16870 s → 0.15230 s | 49.62 MiB → 0.51 MiB | Exact SHA-256 match; small datasets retain the one-shot fast path | Batch optimum depends on row width and Python version |
| 1,000 homogeneous Slurm tasks | Generate 1,000 standalone scripts | One Slurm array script plus one streamed JSONL task table | 0.03693 s → 0.21417 s | 1,000 files / 657,000 B → 2 files / 232,700 B | Same engine command contract; improves artifact and scheduler scale, not local generation latency | Slurm-only; homogeneous resource contract; actual queue throughput requires site measurement |
| HPC CPU layout | Positive resource checks only | Thread-variable bounds plus optional per-node CPU-capacity check | Validation-scale, not benchmarked | No material allocation | Rejects obvious OpenMP/BLAS and task-layout oversubscription | Site CPU topology can be more complex than a single `cpus_per_node` value |
| Approval enforcement | Approval was recorded as a comment | Pending/rejected scripts contain an executable `exit 64` guard | Negligible | Negligible | Prevents the reviewed script from launching its engine command | Scheduler allocation can still begin if a blocked script is manually submitted |
| Ridge robustness | Existing adaptive primal/dual solver | Added finite-value checks, data shape and constant-feature provenance | Negligible for normal inputs | No material allocation | Scientific predictions unchanged; malformed data fail earlier | A full condition-number calculation was deliberately not added because it duplicates expensive decomposition work |

Numbers are medians of three measured runs after one warm-up. `tracemalloc` reports Python allocations, not total resident memory, filesystem cache or native BLAS allocation. Raw benchmark JSON is generated on demand rather than committed because timing is machine-specific.

## Repository-wide audit conclusions

### Suitable and implemented

1. **Streaming content hashes.** The repository supports Python 3.10, so the implementation uses an explicit chunk loop rather than `hashlib.file_digest`, which was added in Python 3.11.
2. **Bounded canonical serialization.** The exact historical dataset digest is retained; no provenance identity changes.
3. **Slurm arrays for homogeneous independent work.** A campaign remains one reviewed base manifest plus task-specific input/workdir/output overlays. No submission occurs automatically.
4. **Explicit thread guards.** Common OpenMP, OpenBLAS, MKL, BLIS, Accelerate and NumExpr variables cannot request more threads than `cpus_per_task`.
5. **Runtime approval guard.** Generated individual and array scripts refuse to execute pending/rejected manifests.

### Recommended only for a legal target environment

- VASP `KPAR`/`NCORE` tuning, Quantum ESPRESSO MPI/OpenMP decomposition and CP2K MPI/OpenMP/ELPA tuning must be benchmarked with the actual executable, model, interconnect and filesystem.
- Compatible checkpoint, charge-density and wavefunction reuse can avoid repeated work, but only when engine version, method fingerprint, geometry and restart semantics remain compatible.
- ASE socket calculators can reduce repeated process startup for supported engines; they are not a universal wrapper for licensed binaries.
- ASE database reservations or an AiiDA-style content hash can prevent duplicate work in multi-worker campaigns. This repository does not add an implicit result cache because stale scientific data would be more damaging than a repeated calculation.
- `ProcessPoolExecutor` is appropriate only for sufficiently coarse, picklable CPU-bound Python tasks. It must not be nested blindly around MPI/BLAS-heavy engines.

### Rejected or deferred

| Candidate | Decision | Reason |
|---|---|---|
| Keep one full `splitlines()` list and share it across all Gaussian helpers | Rejected | The measured candidate increased peak memory and did not improve wall time reliably |
| Lower-retention/full-stream Gaussian rewrite | Not shipped | A measured prototype changed 0.90791 s → 0.89095 s and 12.74 MiB → 8.89 MiB on a 3.64 MB synthetic rich log, but it still required a full decoded string and added high-context compatibility risk for only ~1.9% wall-time gain |
| Compute matrix condition number for every ridge fit | Rejected by default | `numpy.linalg.cond` can add another expensive factorization/SVD; finite checks, solver identity and matrix shape provide low-cost provenance instead |
| Add SciPy solely for sparse ridge support | Deferred | No audited repository fixture demonstrated a genuinely sparse production matrix; the dependency and code-path cost is not yet justified |
| Split static CI gates away from two Python versions | Rejected | The repository is small and current full-matrix wall time is acceptable; preserving identical end-to-end coverage is more valuable than a minor CI saving |
| Remove pip upgrade from CI without a controlled runner comparison | Not implemented | The available historical log was insufficient to isolate a stable saving, and installer compatibility is worth retaining |
| Implicit parsed-manifest or calculation-result cache | Rejected | Cache invalidation must include content, code, engine, method fingerprint and environment; an incomplete cache could return stale scientific evidence |

## Primary sources reviewed

Accessed 2026-07-27.

- Python `concurrent.futures`: <https://docs.python.org/3.13/library/concurrent.futures.html>
- Python `hashlib.file_digest`: <https://docs.python.org/3.12/library/hashlib.html#hashlib.file_digest>
- Python `JSONEncoder.iterencode`: <https://docs.python.org/3/library/json.html#json.JSONEncoder.iterencode>
- NumPy `vectorize`: <https://numpy.org/doc/stable/reference/generated/numpy.vectorize.html>
- ASE parallel I/O: <https://wiki.fysik.dtu.dk/ase/ase/parallel.html>
- ASE database reservations: <https://wiki.fysik.dtu.dk/ase/ase/db/db.html>
- ASE socket I/O: <https://wiki.fysik.dtu.dk/ase/ase/calculators/socketio/socketio.html>
- Slurm Job Array: <https://slurm.schedmd.com/job_array.html>
- Slurm CPU management: <https://slurm.schedmd.com/cpu_management.html>
- OpenBLAS runtime variables: <https://github.com/OpenMathLib/OpenBLAS/wiki/Faq>
- Intel oneMKL threading with MPI: <https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/current/using-openmp-threading-with-mpi.html>
- AiiDA calculation caching: <https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/caching.html>
- VASP parallelization guidance: <https://www.vasp.at/wiki/index.php/Optimizing_the_parallelization>
- VASP `KPAR`: <https://www.vasp.at/wiki/index.php/KPAR>
- VASP `NCORE`: <https://www.vasp.at/wiki/index.php/NCORE>
- Quantum ESPRESSO `pw.x` input/restart documentation: <https://www.quantum-espresso.org/Doc/INPUT_PW.html>
- CP2K restart/wavefunction keywords: <https://manual.cp2k.org/>
- GitHub dependency caching: <https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows>
- `actions/setup-python` Node 24 release line: <https://github.com/actions/setup-python/releases>
- `actions/checkout` Node 24 release line: <https://github.com/actions/checkout/releases>

## Scientific boundary

All implemented changes preserve method fingerprints, convergence thresholds and result acceptance rules. They optimize repository-side overhead only. Engine-level speed, scaling and memory claims require immutable measurements from the legal target executable, version, node layout and filesystem before promotion to L3 evidence.
