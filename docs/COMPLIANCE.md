# Design compliance matrix

This document maps the uploaded **TsaoSciResearcher Design** requirements to the v0.3.0 implementation.

| Requirement | Implementation | Verification | Status |
|---|---|---|---|
| Single entry router with progressive loading | `SKILL.md`, `router_rules.json`, 15 `workflows/*/WORKFLOW.md` files | `tests/test_router.py`, repository audit | PASS |
| Research-question and hypothesis formation | `workflows/research-question/`, research-paradigm references and templates | workflow/path audit | PASS |
| Deep research and systematic review | `deep-research`, `systematic-review`, literature references and matrix template | workflow/path audit | PASS |
| Research and experiment design | `research-design`, `experiment-design`, protocol schema and templates | schema and path audit | PASS |
| Data quality, statistics and uncertainty | `data-analysis`, statistics references, 52 routed capabilities | capability audit | PASS |
| Scientific figures with a pre-plot contract | `scientific-figure`, figure schema/template, validation and export checks | `test_figure_contract.py` | PASS |
| Scientific writing and technical reporting | writing, peer-review and technical-report workflows/templates | workflow/path audit | PASS |
| Research integrity and human gates | integrity workflow, claim/evidence policy and validators | `test_claims.py` | PASS |
| TsaoSciComputation handoff | workflow, schema, template and generator | schema/path audit | PASS |
| Durable `.tsao-research/` project state | project initializer, project schema and state references | `test_init_project.py` | PASS |
| At least 150 machine-readable capabilities | 158 capabilities in 24 progressive JSON shards, Markdown and CSV catalogs | `test_capabilities.py` | PASS |
| Deterministic scripts return non-zero on failure | router, validators, installer, package and repository audit scripts | CI and unit tests | PASS |
| Codex/Claude/Open Agent installation | cross-platform installer and wrappers | `test_install.py` | PASS |
| Windows/Linux/macOS support | Python installer, PowerShell and shell wrappers | installer tests and static audit | PASS |
| License separation | Apache-2.0 core, no vendored upstream code, source/third-party records | repository audit | PASS |
| Independent ZIP release | `scripts/package_release.py` | release test/audit | PASS |

## Interpretation

`PASS` means the repository contains an implementation and an automated or structural verification. It does **not** mean external literature databases, Office software, laboratory instruments, models or scientific solvers are installed. Those are orchestrated or delegated capabilities and remain environment-dependent.
