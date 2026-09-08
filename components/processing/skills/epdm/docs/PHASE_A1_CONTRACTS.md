# EPDM Scientific Kernel V2 — Phase A1 contracts and schemas

## Scope

Phase A1 implements the frozen software contracts only. It does not implement a V2 reaction RHS,
thermodynamic solver, parameter estimation, GPC deconvolution, moment equations, dynamic simulation,
or an industrial prediction.

## Delivered

- immutable domain contracts and frozen enumerations in `contracts.py`;
- append-only, type-bound unique-ID registries in `registry.py`, with per-registry atomic writes, snapshot isolation, deterministic content hashes and fail-closed cross-registry references;
- transactional JSON-to-contract publication in `canonical_loader.py`: explicit schema-version decision, strict JSON parsing, frozen dataclass construction, temporary registry closure, deterministic manifest/hash, and immutable publication only after every Gate succeeds;
- structural JSON Schema plus semantic cross-reference validation in `validation_v2.py`, which now requires canonical publication for every non-failing V2 project;
- gate invariant and layered qualification aggregation in `qualification_v2.py`;
- metadata-only V1 adapter skeleton in `migration.py`;
- strict schemas, Gate/reason/state/reaction catalogs, requirement traceability and a synthetic fixture;
- negative tests for invalid units, missing or invalid evidence, unsupported diene identity, illegal local
  bindings, data leakage, mixed state bases and manual qualification PASS.

## Truth boundary

`SOFTWARE_VERIFIED_PHASE_A1` means that the contract, schema and validation software passed its
declared tests. It does not mean that any kinetic or thermodynamic parameter is calibrated, that V2
calculations are available, or that engineering use is approved. V1 public calculations remain
unchanged and continue to be identified as `V1_LUMPED_REFERENCE` / `CALCULATED_REFERENCE_ONLY`.

## Next Gate

Phase A2 may add frozen state-layout and reaction-definition implementations. Phase B
thermodynamics/calibration work remains blocked until the earlier contracts are satisfied. No later
phase may weaken the evidence, unit, applicability, status or migration contracts introduced here.
