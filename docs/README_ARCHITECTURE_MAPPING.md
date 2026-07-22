# Design → code → test mapping

This matrix maps the uploaded design baseline to the v0.5.2 implementation.

| Design intent | Code or artifact | Automated evidence | Status |
|---|---|---|---|
| Route before loading | `SKILL.md`, `router.py`, route rules | router property and semantic tests | Implemented |
| One complete research lifecycle | 15 workflow directories and contracts | repository cross-contract audit | Implemented |
| 322-skill coverage | `capabilities/v2/capabilities.json` with workbook lineage | design-compliance and audit checks | 322/322 named |
| Progressive references/templates | 22 references, 13 templates | README facts and structure audit | Implemented |
| Question/evidence/claim registries | unified `.tsao-research/` initializer | initializer and design-compliance tests | Implemented |
| Recoverable state | atomic writes, locks, managed replacement | state/common tests | Implemented |
| Auditable state | SHA-256 event chain, decisions and approvals logs | tamper and lifecycle tests | Implemented |
| Evidence/citation integrity | validators and closed schemas | claims/schema/audit tests | Implemented |
| Scientific figure contract | schema, template, plotting example, export validator | figure-contract tests | Implemented |
| Computation boundary | path-contained checksummed v2 handoff with scale, boundaries, metrics, outputs and evidence level, registered in project/artifact state | runtime, CLI, security and mutation tests | Implemented |
| Generic schema validation CLI | `scripts/validate_schemas.py` | schema CLI test and CI | Implemented |
| Cross-platform installer | installer and shell/PowerShell wrappers | install and compatibility tests | Implemented |
| Reproducible release | deterministic ZIP and sidecars | release tests and two-build CI | Implemented |
| Documentation/code consistency | generated `README_FACTS.json` | README facts test and audit | Implemented |
| Real external execution | TsaoSciComputation/solver/lab environment | execution receipts required | Delegated by design |
| Office rendering | host document tools | no native core claim | Host-dependent |

## Traceability rule

```text
Design requirement
  → workflow/capability/schema
  → validator/state gate
  → automated test or CI evidence
  → README claim
```

A README claim must never be stronger than the last verified link in this chain.
