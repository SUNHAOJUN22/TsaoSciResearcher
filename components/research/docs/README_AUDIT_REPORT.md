# TsaoSciResearcher design and README audit

**Audit date:** 2026-07-24  
**Target release:** v0.7.0

## Conclusion

The public README is constrained to facts generated or checked from the repository. It describes TsaoSciResearcher as a research control layer rather than a bundle of databases, solvers or instruments.

The v0.7.0 audit closed the following gaps:

1. corrected the runtime package version drift and made root `VERSION` the single manually maintained version source;
2. expanded the repository from 15 to 19 JSON Schemas for execution receipts, reproducibility capsules and validation evidence 1.6;
3. added checksum-verified execution receipts linked to the exact computation handoff;
4. added deterministic metadata/full reproducibility capsules and archive-tamper tests;
5. added line/branch coverage, 18 critical mutation checks, bounded performance and quality-baseline evidence;
6. added deterministic CycloneDX SBOM, resolved-environment vulnerability audit and external commit attestation;
7. added source ZIP, wheel, sdist, typed-package and isolated-install validation;
8. replaced one-shot validation controls with permanent read-only CI, manual audit and nightly health workflows plus a tag-bounded release workflow;
9. expanded SECURITY, CONTRIBUTING, architecture, CLI, supply-chain and release documentation.

## Requirement-to-evidence result

| Requirement | Evidence | Result |
|---|---|---|
| Full research lifecycle | 15 workflow directories and gate contracts | Implemented |
| Named AI-for-Science coverage | 322 workbook-named contracts + 19 runtime/core contracts | 341 total |
| Project provenance | hash-linked state, decisions, approvals and registries | Implemented |
| Computation boundary | contained v2 handoff with input hashes and approval gates | Implemented |
| Real execution evidence | receipt v2 with handoff identity, timestamps, exit state and output hashes | Implemented |
| Transfer/reproduction | deterministic capsule manifest, tree digest and sidecar | Implemented |
| Scientific claim discipline | four executable scientific-quality guards | Implemented |
| Schema and metadata governance | 18 Schemas, version synchronization and repository audit | Implemented |
| Software test strength | line/branch coverage and 24/24 critical mutations | Gated |
| Supply-chain transparency | exact direct toolchain, SBOM, pip-audit, pinned Actions and attestation | Gated |
| Distribution | byte-identical source ZIP, wheel, sdist and isolated import | Gated |
| External DFT/MD/FEM/CFD/process/lab execution | real external environment | Delegated; receipt required |
| Final scientific acceptance | qualified reviewer and project evidence | Human decision |

## README policy

A README claim must not be stronger than its code, Schema, test and CI evidence. A named engine is an integration target. A handoff is a plan. A receipt is execution provenance. A capsule is integrity evidence. None alone proves scientific correctness.
