# Compute Efficiency and Performance Evidence Guide

This guide separates **repository overhead**, **scheduler throughput** and **electronic-structure kernel cost**. Faster parsing, more ranks or a detected GPU never make an unconverged or scientifically incompatible calculation acceptable.

## Implemented repository optimizations

### Large-output parsing

VASP, Quantum ESPRESSO and CP2K selected-field adapters use read-only memory maps and bounded terminal evidence scans. The Gaussian adapter retains its established decoded-text implementation. Parser optimisation never changes the scientific acceptance boundary.

### Content hashing

Provenance, structures and artifacts are hashed in 1 MiB chunks with ordinary SHA-256. Large canonical datasets use bounded serialization while preserving the historical digest.

### Linear algebra

The NumPy ridge baseline selects the smaller regularised system: primal for non-wide matrices, dual for wide matrices and `numpy.linalg.lstsq` for `alpha = 0`. It rejects NaN/Inf and records solver, dimensions and constant features.

### Homogeneous campaigns

`generate_job_array.py` writes an approval-gated Slurm array plus a streamed JSONL task table. It never submits the result. Use arrays only for independent tasks with compatible resources and method policy.

### Oversubscription and topology

The HPC validator checks OpenMP/BLAS thread variables, `tasks_per_node × cpus_per_task`, GPU count, ranks per GPU, oversubscription approval, backend/vendor compatibility and scheduler-owned device visibility.

## Structured execution boundary

Formal Manifest commands are argv lists. Executable and arguments are quoted separately. Scheduler job/partition/queue fields, environment names, module/source entries, work directories and scratch paths are validated. Raw command fields, control characters, header injection and path escape fail closed.

Execution approval is not a string flag. An approved Manifest requires an Ed25519 attestation bound to:

- Manifest SHA-256;
- benchmark plan ID;
- candidate ID;
- method fingerprint digest;
- approver identity, scope and time window;
- verified public-key fingerprint and signature.

The generator never submits a job or executes a DFT engine.

## Hardware inventory and bounded automatic tuning

`plan_acceleration.py --inspect-environment` performs a non-invoking environment and hardware inventory. It records only bounded availability and identity facts for CPU architecture, MPI/OpenMP, accelerator runtimes and visible devices. It never launches Gaussian, VASP, Quantum ESPRESSO or CP2K, never returns secret environment values and represents unavailable optional tools as `NOT_AVAILABLE` rather than fabricated zero values.

`generate_autotuning_candidates.py` consumes an explicit profile containing scientific identity, workload estimates, declared hardware capacity, policy limits and tuning ranges. It deterministically generates a bounded candidate set while enforcing:

- immutable input SHA-256, method fingerprint and convergence-policy identity;
- a required FP64 CPU scientific reference;
- engine and GPU-vendor compatibility;
- CPU, GPU, memory, topology and oversubscription limits;
- a configured maximum candidate count;
- `approval: pending` for every generated candidate.

The candidate generator writes planning artifacts only. It does not submit a scheduler job, invoke an external engine, measure performance or promote a capability.

Example:

```bash
python skills/tsao-dft-hpc-provenance/scripts/plan_acceleration.py \
  --inspect-environment \
  --out build/hardware-inventory.json

python skills/tsao-dft-hpc-provenance/scripts/generate_autotuning_candidates.py \
  autotuning-profile.yaml \
  --out build/autotuning-candidates.json
```

Inventory and candidate output remain L1 planning evidence until legal target-environment execution, Parser acceptance, numerical equivalence, artifact verification and independent review are attached.

## GPU, native-code and edge planning

`plan_acceleration.py` creates a deterministic compatibility and benchmark plan for Gaussian, VASP, Quantum ESPRESSO, CP2K and explicit native integrations across workstation, HPC and edge targets.

It distinguishes:

1. engine-native GPU builds;
2. CPU MPI/OpenMP execution;
3. validated atomistic-ML surrogates;
4. edge orchestration/inference with remote production DFT.

CUDA-X, ROCm, oneAPI, Metal and portability libraries are evaluated by workload and integration boundary, never as universal drop-in switches. Python remains on the Manifest, validation, scheduling, provenance and experiment-control plane. Only profiled numerical hotspots should move to a native or accelerator backend, with a deterministic CPU fallback.

## Benchmark materialisation

`materialize_acceleration_campaign.py` combines a matching base Manifest and acceleration profile into:

- a reviewed accelerated Manifest;
- an FP64 CPU scientific reference;
- declared GPU scaling candidates;
- a benchmark matrix and plan.

Every candidate is reset to `approval: pending`. The tool writes files only.

## Executable evidence contracts

The evidence pipeline executes these versioned contracts:

- `benchmark-result.schema.json`;
- `performance-qualification-policy.schema.json`;
- `engine-parser-result.schema.json`;
- approval/review attestation Schemas.

Schema validation precedes semantic validation. Unknown, malformed or incompatible formal records fail before qualification.

A qualification run accepts one benchmark plan and isolates candidates by scientific identity, engine build, hardware/driver and topology. CPU reference and candidates must belong to the same plan.

## Unified Parser and bridge layer

Gaussian, VASP, Quantum ESPRESSO and CP2K share a fail-closed Parser result contract. Fatal or final failure takes precedence over an earlier success marker. Missing files return structured failures. Parser acceptance never means scientific acceptance.

Four bridge CLIs combine Parser records with Manifest, method fingerprint, runtime, scheduler metrics, GPU inventory and artifact hashes. Missing fields remain explicit and block formal qualification.

## Numerical-equivalence-first performance

Effective speedup is calculated only after matching:

- plan, engine/version and build;
- input SHA-256 and method fingerprint;
- model chemistry, corrections and convergence;
- observable set and Parser acceptance;
- energy, force, stress and declared-property tolerances.

The Policy requires repeated successful runs and uses medians, quartiles, IQR, MAD, outlier detection, scaling efficiency, GPU-hours, CPU-core-hours, memory, SCF, I/O and optional energy-to-solution. Failed attempts are retained.

## Signed review and content-addressed publication

The prequalification payload is hashed and independently reviewed. The review must be an Ed25519-signed attestation binding:

- reviewer identity and attestation ID;
- Policy ID, benchmark plan and candidates;
- evidence-root SHA-256;
- decision, scope, issue and expiry times;
- key fingerprint and verified signature.

Formal publication occurs through a staging directory and atomic rename:

```text
evidence-<root_sha256>/
  records.json
  benchmark-summary.json
  policy.json
  review-attestation.json
  qualification-report.json
  evidence-root.json
```

`evidence-root.json` covers every formal file by digest and size. Directory/root mismatch, missing/extra file, digest/size mismatch, collision and partial publication fail closed. `verify_evidence_bundle.py` performs independent verification.

## Commands

```bash
python skills/tsao-dft-hpc-provenance/scripts/validate_benchmark_result.py \
  results/*.yaml \
  --schema skills/tsao-dft-hpc-provenance/templates/benchmark-result.schema.json \
  --artifact-root run-artifacts

python skills/tsao-dft-hpc-provenance/scripts/qualify_performance_evidence.py \
  results/* \
  --result-schema skills/tsao-dft-hpc-provenance/templates/benchmark-result.schema.json \
  --policy skills/tsao-dft-hpc-provenance/templates/performance-qualification-policy.yaml \
  --policy-schema skills/tsao-dft-hpc-provenance/templates/performance-qualification-policy.schema.json \
  --artifact-root run-artifacts \
  --review signed-review-attestation.json \
  --review-public-key reviewer-ed25519-public.pem \
  --out-parent build/performance-evidence

python skills/tsao-dft-hpc-provenance/scripts/verify_evidence_bundle.py \
  build/performance-evidence/evidence-<root_sha256>
```

## Qualification boundary

`QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE` means a bounded evidence package passed eligibility rules. It does not change the public capability level.

Public HPC L3 requires generic execution evidence plus the complete acceleration contract: exact build/hardware/site identity, repeated real-engine runs, numerical/Parser/performance passes, artifact/bundle/root SHA-256 values, signed review identity/scope/signature verification, independent approval and explicit capability registration.

The current public state remains `L2_VALIDATED_ADAPTER`.

## Non-claims

The repository does not claim universal speedups or legal execution coverage for Gaussian, VASP, Quantum ESPRESSO, CP2K, Multiwfn, VMD, Cantera or any HPC installation. Only measurements from a legal target environment can establish a scoped L3 result.
