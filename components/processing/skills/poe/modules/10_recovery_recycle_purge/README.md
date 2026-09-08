# 10_recovery_recycle_purge — Recovery, recycle and purge

## Purpose

Close solvent/comonomer recovery, impurity memory, purge and recycle topology.

## Evidence and lineage

Inputs must cite POE asset IDs from `../../data/source_asset_registry.json`, requirement IDs from `../../data/requirement_trace.json`, and open deviations from `../../data/conflict_ledger.json`. Historical Aspen, MATLAB and Origin files remain `CONTROLLED_HISTORICAL_EVIDENCE`; they are not redistributed or silently treated as qualified code.

## Input contract

recovery units, recycle streams, impurities, losses and purge basis. Inputs use SI units unless a field explicitly declares and converts another unit. `contract.schema.json` defines the machine-readable input and output envelope.

## Equations or algorithm

Use the minimum model that can answer the decision. State equations, conservation basis, parameters, units, numerical tolerances, applicability domain and uncertainty. Module-specific executable reference logic is implemented in `../../core.py` where available; commercial simulation and physical experiments remain external.

## Output contract

closed-loop balances, accumulation risk and purge rationale. Every output carries `status`, evidence IDs, applicability, uncertainty, blockers and approval state.

## Applicability domain

The module applies only to ethylene/alpha-olefin solution-polymerization cases whose component identities, measurement boundaries, property method, catalyst basis, scale and recycle state are explicitly declared.

## Fail-closed conditions

Missing recycle connections or impurity state block G9. Missing evidence returns `NOT_EVALUATED` or `HOLD`; structural inconsistency returns `FAIL`. No missing item is converted into an assumed PASS.

## Tests

Positive, boundary and malicious-input tests are located in `../../tests/test_poe_alpha6_p0.py` and `../../tests/test_poe_alpha6_package.py`. Required Gate: `G9`.

## External execution boundary

Physical polymerization, commercial Aspen/Origin/MATLAB execution, CFD, equipment design, HAZOP/LOPA/SIL, pilot operation, customer qualification and industrial guarantees remain `NOT_EVALUATED` until performed and approved by named qualified teams.
