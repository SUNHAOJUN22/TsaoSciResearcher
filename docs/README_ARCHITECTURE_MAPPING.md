# README architecture mapping

This document maps the uploaded design requirements to the v0.5.1 implementation and its executable evidence.

| Design requirement | Current implementation | Primary code/artifact | Test or gate | Status |
|---|---|---|---|---|
| Single entry router with progressive disclosure | Root Skill routes before loading; cached bilingual router uses positive/negative semantics | `SKILL.md`, `tsao_researcher/router.py`, `routing/router-rules-v2.json` | `test_router.py`, `test_runtime_v2.py`, route self-test | Implemented |
| Scientific question and falsifiable hypothesis formation | Dedicated gated workflow and contracts | `workflows/research-question/` | workflow/schema audit | Implemented |
| Deep research and evidence synthesis | Deep-research and systematic-review workflows; evidence/claim schemas and validators | `workflows/deep-research/`, `workflows/systematic-review/`, `scripts/validate_evidence.py`, `scripts/validate_claims.py` | claim/evidence tests and repository audit | Implemented as orchestration/validation; retrieval depends on host tools |
| Research and experiment design | Separate research-design and experiment-design workflows with DOE/power references | `workflows/research-design/`, `workflows/experiment-design/`, `references/experimental-design/` | workflow/schema audit | Implemented |
| Data quality, statistics, UQ and scientific ML | Data-analysis workflow and 52 routed capability records | `workflows/data-analysis/`, legacy capability shards | capability/workflow tests | Implemented as method orchestration; analysis libraries depend on environment |
| Scientific figure contract before plotting | Figure schema, template and validator | `schemas/figure-contract.schema.json`, `templates/figure-contract/`, `scripts/validate_figure.py` | `test_figure_contract.py` | Implemented |
| Scientific writing, reports and peer review | Three dedicated workflows plus templates/references | `workflows/scientific-writing/`, `peer-review/`, `technical-report/` | workflow/schema audit | Implemented as guarded orchestration |
| Research integrity and read-only audit | Integrity workflow, claim/evidence policies and human-review gates | `workflows/research-integrity/`, `references/integrity/` | audit, claim/evidence and mutation tests | Implemented |
| Standardized TsaoSciComputation handoff | Project-bound, checksummed, path-contained handoff | `tsao_researcher/handoff.py`, `schemas/v2/handoff.schema.json` | `test_runtime_v2.py`, mutation/security gates | Implemented |
| Distinct lifecycle states | Hash-linked state machine with approval required for acceptance | `tsao_researcher/state.py`, `.tsao-research/` layout | project-state and tamper tests | Implemented |
| Recoverable and auditable project artifacts | Atomic writes, bounded locks, JSON/JSONL limits and SHA-256 event chain | `tsao_researcher/io.py`, `scripts/common.py` | common/state/import-isolation tests | Implemented |
| Machine-readable capability index >=150 | 340 v2 records plus 158 named compatibility records | `capabilities/v2/`, `capability-index/` | capability count/uniqueness/schema tests | Implemented, with domain naming limitation |
| Detailed domain support | Seven domain packs with method selection, validation, interpretation and figure guides | `domain-packs/` | repository audit | Implemented as guidance/contracts |
| Deterministic validators and non-zero failures | Structure, project, evidence, claims, figure, export, release and audit scripts | `scripts/` | full regression and mutation smoke | Implemented |
| Codex/Claude/Open Agent installation | Cross-platform managed installer with dry-run, force, uninstall and validate | `scripts/install.py`, `install.py`, `install.sh`, `install.ps1` | install and compatibility tests | Implemented |
| Windows/Linux/macOS support | Layered GitHub Actions compatibility matrix | `.github/workflows/ci.yml` | release CI run 29887374398 | Implemented |
| Deterministic release ZIP | Fixed metadata, sorted members, sidecar verification and safe extraction | `scripts/package_release.py`, `scripts/archive_safety.py` | release tests and two-build comparison | Implemented |
| One durable `main` branch | Post-merge workflow closes old PRs and deletes every non-main branch | `.github/workflows/cleanup-branches.yml` | workflow self-verification | Implemented |
| Full 322-skill workbook preserved one-to-one | 158 slugs exact; 164 categories represented by count-aligned generic domain slots | `capability-index/`, `capabilities/v2/`, `domain-packs/` | this coverage audit | Partial |
| Real solver/laboratory execution | Explicitly delegated; no false completion claim | computation handoff and integrity gates | handoff tests and README boundary checks | Delegated by design |
| Native DOCX/PPT rendering | Not part of core package; may be orchestrated by host tools | workflow policy only | no native renderer tests | Not native / host-dependent |

## Traceability chain

```text
Design requirement
        ↓
Workflow policy + machine contract
        ↓
Capability / Schema / runtime module
        ↓
Validator or state gate
        ↓
Test / mutation / performance / release evidence
        ↓
README claim
```

The public README must not advance a claim to a higher level than this chain supports.
