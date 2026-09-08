# TsaoSciResearcher

TsaoSciResearcher is an evidence-first scientific research control layer. It separates methodology, mathematical explanation contracts, external execution, execution evidence, software validation, and final scientific acceptance.

## Verified scope

- 322/322 workbook Skill slugs preserved as named contracts;
- 19 runtime/core additions;
- 341 total capability contracts;
- 15 gated workflows;
- 20 JSON Schemas, including the schema-backed mathematical-contract registry;
- 38 AI-generated conceptual documentation diagrams;
- canonical `.tsao-research/` state, execution receipts and reproducibility capsules;
- explicit native, host-tool, external-computation and human-approval boundaries.

## Mathematical contract interface

Release 0.7.4 exposes a versioned bilingual registry for eight explanation contracts and now publishes the governing Draft 2020-12 Schema:

```bash
python -m tsao_researcher math
python -m tsao_researcher math --schema
python -m tsao_researcher math --contract decision-readiness --output contract.json
python scripts/validate_mathematical_contracts.py --check
```

The registry covers capability ranking, quantity/dimension consistency, applicability and extrapolation, evidence conflict, identifiability, uncertainty propagation, multiscale bridge error, and conservative decision readiness. It always reports `solver_executed=false` and `automatic_approval=false`.

## Acceptance evidence

The repository supports `preflight`, `current-tree`, and `composite` validation scopes. The checked-in acceptance hardening record uses a pinned exact-tree full-repository baseline plus a SHA-256-bound focused current-change regression; `current_end_to_end_ci` remains explicitly `NOT_RUN` until a fresh current-tree external attestation is produced.

Start with the [original requirements audit](ORIGINAL_REQUIREMENTS_AUDIT.md), [mathematical contracts](MATHEMATICAL_CONTRACTS.md), [validation evidence](VALIDATION_EVIDENCE.json), and [scientific capability visual atlas](VISUAL_ATLAS.md).

A software PASS validates declared software controls. It does not certify an external experiment, database query, solver run, or scientific conclusion.
