# Hardware-aware optimization contract

This contract is a deterministic planning layer. It does not execute VASP, Quantum ESPRESSO, CP2K, Gaussian, CUDA, ROCm, oneAPI or an edge runtime, and it never reports speedup.

## Inputs

Use `templates/hardware-optimization-profile.yaml` for an engine/HPC plan and `templates/edge-inference-profile.yaml` for an edge-surrogate plan. Unknown physical cores, memory, bandwidth, architecture, device memory and build identity must remain `NOT_AVAILABLE`; do not replace missing observations with zero.

A simulated fixture must contain all three labels:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```

Engine-native accelerator plans require both an explicit build capability and an immutable build fingerprint. Detecting a toolkit or library is insufficient.

## Command

```bash
python skills/tsao-dft-hpc-provenance/scripts/hardware_aware_optimizer.py \
  skills/tsao-dft-hpc-provenance/templates/hardware-optimization-profile.yaml \
  --out build/optimization-plan.json
```

The output is validated against `templates/hardware-optimization-plan.schema.json` and records:

- backend and provider;
- expected bottleneck;
- conservative resource baseline;
- requested/recommended library decisions;
- assumptions and unresolved `NOT_AVAILABLE` fields;
- numerical, topology, transfer and evidence requirements;
- explicit prohibition of speedup claims and public capability promotion.

## Provider boundaries

- `engine-native`: only an accepted accelerated engine build; library injection is forbidden.
- `array-api`: backend-neutral Python array route for measured ML or postprocessing workloads.
- `custom-native`: source-level integration after profiling and with deterministic CPU fallback.
- `edge-runtime`: calibrated surrogate inference with uncertainty/OOD gate and remote DFT fallback.
- `remote-dft`: edge orchestration of workstation/HPC DFT, not local production DFT.
- `cpu`: MPI/OpenMP/BLAS baseline and scientific reference.

## Acceptance boundary

`ELIGIBLE_PLAN` means only that the profile is internally consistent. Real execution still requires legal engine/site access, exact build and hardware identity, repeated runs, numerical equivalence before speedup, transfer/memory/topology telemetry, retained failures and independent review.
