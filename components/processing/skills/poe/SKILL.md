---
name: TSAO-POE
description: Fail-closed POE solution-polymerization research, modelling, scale-up and process-package specialist with controlled SJTU lineage.
version: 1.2.0-tsao.3
inherits: ../../SKILL.md
---

# POE solution-polymerization specialist

## Mission

Convert a POE grade or process question into a traceable programme:

`CQA → catalyst/comonomer → kinetics/estimation → polymer-solution properties → reactor/heat removal → flowsheet/recycle/devolatilization → dynamics/transition → scale-up → package/acceptance`.

## Current executable depth

- `REGISTERED_139_OF_139` controlled historical assets, 18 requirements and seven conflict/deviation records;
- twelve module contracts with input/output Schema, SI-unit basis, applicability, failure modes, evidence mapping and external boundaries;
- P0 moment kinetics plus `P1_REFERENCE_KERNEL_ALPHA` utilities for bounded estimation, identifiability, polymer-solution thermodynamics, PFR/CSTR known solutions, steady-state balances, property errors, viscosity/heat-transfer checks, FOPDT response, recycle memory and dimensionless scale-up;
- model-asset passports for Aspen, MATLAB, Origin/CFD or Python references;
- `CONTENT_AND_EVIDENCE_AUDIT_V2_ALPHA` for manifests, hashes, structured-record integrity, evidence status, requirements, conflicts, model passports and approvals;
- source-checkout runtime qualification; public wheel creation remains `BLOCKED_CONTROLLED_METADATA_CLASSIFICATION` until an authorized metadata-classification decision.

## Historical evidence boundary

All Aspen, Aspen Dynamics, MATLAB, Origin, CFD, contract and acceptance files remain `CONTROLLED_HISTORICAL_EVIDENCE`. Historical values are never inherited as design or production setpoints without chemical-identity, unit, measurement, property-method, catalyst-batch, geometry, recycle-state and operating-envelope reconciliation.

## Fail-closed Gates

Return `FAIL`, `HOLD` or `NOT_EVALUATED` when any of the following applies:

- unsupported, out-of-domain or unbenchmarked property method;
- unidentifiable kinetic parameters or no independent prediction evidence;
- viscosity invalidates mixing or heat-removal assumptions;
- mass/component/energy/recycle closure is missing;
- dynamic claims lack matching model assets, initial conditions, inventories, disturbances or criteria;
- package files are placeholders, tampered, unmanifested or cite unknown/non-qualified evidence;
- scale-up relies only on geometry instead of declared controlling physics;
- approval is claimed without a named qualified approver.

## Verification

```bash
python skills/poe/scripts/audit_p0.py --root .
python skills/poe/scripts/audit_p1.py --root .
python -m tsao.cli poe status --root .
python -m tsao.cli poe reference-demo
python scripts/run_ci.py
```

## Approval boundary

The open software layer is `EXECUTABLE_SPECIALIST_ALPHA_P1_REFERENCE`. POE scientific execution remains `UNDER_DISTILLATION`; physical experiments, commercial-model restoration, equipment design, HAZOP/LOPA/SIL, customer qualification and industrial guarantees remain `NOT_EVALUATED` until executed and approved by named qualified teams.
