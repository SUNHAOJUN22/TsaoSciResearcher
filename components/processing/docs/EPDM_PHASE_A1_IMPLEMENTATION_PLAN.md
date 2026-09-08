# EPDM Phase A1 implementation plan

## Objective

Implement the frozen V2 scientific-contract and Schema layer without changing EPDM V1 numerical behavior or claiming that V2 equations, calibration, validation, or engineering use exist.

## Deliverables

1. Frozen enumerations and immutable contracts for catalyst, diene, evidence, units, parameters, thermodynamics, datasets, applicability domains, state definitions, Gates, and layered qualification.
2. Strict Draft 2020-12 JSON Schemas with `additionalProperties=false` on stable objects and a single explicit `extensions` escape hatch.
3. Structural and semantic validation, including identifier uniqueness, cross-reference closure, evidence status/applicability, SI units, parameter binding, dataset-role separation, state-basis consistency, and derived qualification.
4. A metadata-only V1-to-V2 migration adapter that preserves original input and never fabricates evidence or invokes an unfinished V2 calculation.
5. Machine-readable Gate, reason-code, state-variable, reaction-class, module-contract, and 80-requirement traceability catalogs.
6. Synthetic software fixtures and positive, negative, mutation-style, migration, Schema, and V1 zero-regression tests.
7. A software-only qualification record bound to the final source commit and permanent cross-platform CI.

## Non-goals

Phase A1 does not implement reaction-network RHS equations, active-site ODEs, thermodynamic backends, parameter estimation, GPC deconvolution, chain moments, reactor networks, design specification, dynamics, hybrid models, or industrial approval.

## Exit criteria

- V1 public APIs and golden numerics remain unchanged.
- Unsupported units, missing or invalid evidence, unresolved references, unsupported diene declarations, illegal local parameter binding, mixed state bases, calibration/validation leakage, and manual qualification overrides fail closed or hold according to the frozen contract.
- The reference V2 project passes both JSON Schema and semantic validation as a synthetic software fixture only.
- All permanent CI matrix jobs, Ruff, coverage, wheel, isolated runtime, Skillpack, and source-identity checks pass.
- Scientific, engineering, HSE, customer, and industrial statuses remain `NOT_EVALUATED`.
