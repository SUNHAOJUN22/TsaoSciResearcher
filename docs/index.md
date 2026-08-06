# TsaoSciResearcher

TsaoSciResearcher is an evidence-first scientific research control layer. It separates methodology, mathematical explanation contracts, external execution, execution evidence, software validation, and final scientific acceptance.

## Verified scope

- 322/322 workbook Skill slugs preserved as named contracts;
- 19 runtime/core additions;
- 341 total capability contracts;
- 15 gated workflows;
- 19 JSON Schemas;
- 37 AI-generated conceptual documentation diagrams;
- canonical `.tsao-research/` state, execution receipts and reproducibility capsules;
- explicit native, host-tool, external-computation and human-approval boundaries.

## Mathematical contract interface

Release 0.7.4 adds a versioned bilingual registry for eight explanation contracts:

```bash
python -m tsao_researcher math
```

The registry covers capability ranking, quantity/dimension consistency, applicability and extrapolation, evidence conflict, identifiability, uncertainty propagation, multiscale bridge error, and conservative decision readiness. It always reports `solver_executed=false` and `automatic_approval=false`.

Start with the [original requirements audit](ORIGINAL_REQUIREMENTS_AUDIT.md), [mathematical contracts](MATHEMATICAL_CONTRACTS.md), and [scientific capability visual atlas](VISUAL_ATLAS.md).

A software PASS validates declared software controls. It does not certify an external experiment, database query, solver run, or scientific conclusion.
