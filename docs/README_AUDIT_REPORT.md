# TsaoSciResearcher design and README audit

**Audit date:** 2026-07-22  
**Target release:** v0.5.2  
**Inputs:** current source tree, uploaded design specification, uploaded 322-entry AI for Science workbook, executable scripts and CI configuration.

## Conclusion

The original design is implemented as a **research control and orchestration layer**, not as a bundle of external databases, solvers or instruments. This audit found and fixed five concrete inconsistencies:

1. 164 computation/engineering records used generic numbered slugs; they now preserve the exact workbook names and slugs.
2. The CLI initializer and compatibility initializer produced two different `.tsao-research/` layouts; both now use one v2 implementation.
3. The design-required question, hypothesis, evidence, claim, decision, artifact, risk and approval registries were not all created by the v2 CLI; they now are.
4. The public computation-handoff script still emitted the legacy v1 contract and did not register the artifact in project state; it now delegates to the canonical v2 runtime and records the handoff in `project.yaml` and `artifacts.jsonl`.
5. README and CI contained release-specific repetition; README is shorter and CI derives the archive name from `VERSION`.

## Requirement-by-requirement result

| Design requirement | Evidence | Result |
|---|---|---|
| Comprehensive research-method hub | 15 workflows, 322 named research/domain contracts and 18 runtime contracts | Done |
| Single entry router | `SKILL.md`, `tsao_researcher/router.py` | Done |
| Progressive loading | Root Skill selects one workflow and its references | Done |
| Scientific question and falsifiable hypotheses | `research-question`, question/hypothesis registries | Done |
| Deep research, systematic review and evidence synthesis | `deep-research`, `systematic-review`, evidence/claim validators | Done; retrieval uses host tools |
| Research and experiment design | `research-design`, `experiment-design`, DOE/power references | Done |
| Data quality, statistics, causal/UQ/ML planning | `data-analysis` and named contracts | Done; libraries depend on environment |
| Figure contract before plotting | figure schema/template/validator/export checker | Done |
| Scientific writing, reports and review responses | writing, peer-review and technical-report workflows/templates | Done |
| Research integrity and read-only audit | integrity workflow, citation/claim/evidence checks | Done |
| TsaoSciComputation collaboration | canonical v2 contract with scale, boundaries, metrics, outputs, evidence level, checksums, project registration and artifact log | Done |
| Exact project status sequence | hash-linked state machine and human approval for `accepted` | Done |
| Design-specified `.tsao-research/` registries | unified initializer creates all nine root registries plus event chain/directories | Done |
| At least 150 machine-readable capabilities | 322 named catalog contracts + 18 runtime contracts | Done |
| All 322 workbook skills named one-to-one | exact workbook slugs/names and catalog IDs in lineage | Done |
| Deterministic validators with non-zero failures | schema, project, evidence, claim, citation, figure, export, structure, release and audit CLIs | Done |
| Generic JSON Schema validator | `scripts/validate_schemas.py` | Done |
| Codex/Claude/Open Agent installation | managed cross-platform installer | Done |
| Windows/Linux/macOS support | CI compatibility matrix | Done |
| Independent deterministic ZIP | two-build byte comparison and safe archive validation | Done |
| License separation | original Apache-2.0 code; upstream sources documented, not bundled | Done |
| Real DFT/MD/FEM/CFD/process/lab execution | intentionally delegated, never fabricated | Boundary by design |
| Native DOCX/PPT renderer | not embedded; uses host document tools | Host-dependent boundary |

## Priority-list check

| Workbook priority item | Current status |
|---|---|
| Scientific Validation Gate | Implemented in workflow gates, state, evidence and audit checks |
| Academic research and scientific-agent suites | Ideas absorbed into original contracts; upstream packages are not silently vendored |
| Chinese research and Office production | Routed through host tools; no false native renderer claim |
| GROMACS/MD analysis | Exact named contracts, MD domain pack and computation handoff; execution remains external |
| Computational materials and catalysis | Exact named contracts and domain guidance; solvers remain external |
| Polymer kinetics | Named contracts across catalysis/polymer and process/kinetics packs |
| OpenFOAM extrusion/CFD | Named contracts and CFD validation pack; OpenFOAM is not bundled |
| DOLFINx multiphysics | Named contracts and FEM/multiphysics validation pack; DOLFINx is not bundled |
| DWSIM/IDAES digital twin | Named process/digital-twin contracts; engines remain external |
| Autonomous experiment loops | Planning, state and provenance exist; unattended external execution requires adapters and approval |
| Research supply chain/version governance | pinned CI, checksums, provenance, deterministic packaging and single-main governance |

## README policy after this audit

The README reports only verified code facts, keeps operational steps short, and sends detailed evidence to dedicated documents. External software names are described as integration targets rather than installed capabilities.
