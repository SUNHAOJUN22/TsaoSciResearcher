<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="112" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>Evidence-first scientific research control layer</strong></p>
  <p>Question → evidence → design → guarded execution → validation → reproducible artifact</p>

[简体中文](README.zh-CN.md) · [Documentation](docs/index.md) · [Requirements Audit](docs/ORIGINAL_REQUIREMENTS_AUDIT.md) · [Architecture](docs/ARCHITECTURE.md) · [Validation](docs/VALIDATION.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **Release 0.7.1** · Apache-2.0 · Python 3.10–3.13 · Windows, Linux and macOS

## What the code actually implements

TsaoSciResearcher is a **single-entry research router, project-state system, validation layer, capability catalog, and reproducibility boundary**. It is not a bundle of every scientific database, solver, instrument driver, plotting engine, or Office renderer.

The original design has been checked against the actual source code and the uploaded 322-entry AI-for-Science catalog:

| Audit fact | Verified result |
|---|---:|
| Workbook Skill slugs preserved | **322 / 322** |
| Missing workbook slugs | **0** |
| Legacy/general named contracts | **158** |
| Domain computation/engineering named contracts | **164** |
| Generic domain placeholders | **0** |
| Runtime/core additions | **19** |
| Total capability contracts | **341** |
| Native-research contracts | **148** |
| Computation-delegated contracts | **170** |
| Human-review contracts | **23** |
| Gated workflows | **15** |
| JSON Schemas | **19** |
| Deterministic scripts | **39** |

Read the full [original-requirements implementation audit](docs/ORIGINAL_REQUIREMENTS_AUDIT.md). A capability contract is discoverable, routable, and testable metadata; it is **not** evidence that an external database, model, solver, instrument, or computation has executed.

## Implementation boundary

| Layer | What is implemented |
|---|---|
| **Native core** | deterministic bilingual routing, capability search, project initialization, state transitions, hash-linked events, schema validation, evidence/claim checks, figure contracts, execution receipts, reproducibility capsules, safe archives and deterministic packaging |
| **Research control layer** | research-question, literature, review, design, experiment, data, figure, writing, peer-review, report, project, patent, integrity, laboratory and computation-handoff workflows with entry/blocking/completion gates |
| **Host-tool execution** | live retrieval, PDF parsing, numerical statistics/DOE/ML, plotting, DOCX/PPT/LaTeX production and external application connectors |
| **External scientific execution** | DFT, quantum chemistry, MD, FEM, CFD, process simulation, HPC, cloud jobs, instruments and laboratory automation |
| **Qualified human approval** | medical, safety, patent/FTO, high-impact causal, integrity and final scientific acceptance decisions |

## Architecture

- **Route before loading** — one primary workflow is selected before references or templates are opened.
- **322 exact catalog contracts** — every workbook slug is retained; 19 runtime contracts add routing, safety, provenance, first-principles strategy and acceptance controls.
- **Canonical `.tsao-research/` state** — questions, hypotheses, evidence, claims, decisions, approvals, risks, artifacts, receipts and hash-linked events remain separate.
- **First-principles strategy advisor** — derives a minimum-sufficient method ladder from observables, degrees of freedom, conservation laws, quantum/statistical physics, thermodynamic ensembles, scales, falsification and UQ; it does not run solvers.
- **Guarded computation handoff** — input hashes, scale, method, conditions, convergence/UQ requirements, expected outputs and approval points are recorded before external execution.
- **Execution Receipt v2** — a real external run is bound to its handoff, engine, arguments, time, exit status and output hashes.
- **Reproducibility Capsule** — deterministic metadata/full ZIPs reject path escape, symbolic links, undeclared members, duplicate inventory records and checksum tampering.
- **Installed-runtime parity** — the wheel carries checksum-synchronized routing and capability data, and distribution acceptance executes real `route` and `search` commands from an isolated installation.
- **Ownership-bound mutations** — lock release cannot delete a replacement owner; JSONL and multi-file project mutations roll back on handled write failure.
- **Truth-preserving validation** — handoffs remain `planned`/`prepared`, receipts bind the registered handoff hash, and `completed`, `checked`, `validated`, and `accepted` remain distinct states.

## First-principles computation and simulation strategy

The distinctive capability is not a software-name recommender. It reconstructs method choice from the underlying science:

```text
question → decision observable → degrees of freedom/state variables
         → conservation/symmetry → quantum, statistical, thermodynamic or continuum frame
         → length/time/energy scales and model reduction
         → minimum-sufficient model → justified escalation → validation/falsification/UQ
         → external handoff → result review
```

“First principles” does not mean DFT for every problem. The advisor selects the cheapest falsifiable physical representation, then escalates only when validation identifies a missing degree of freedom, coupling or scale. See the [first-principles strategy guide](docs/FIRST_PRINCIPLES_STRATEGY.md).

### Scientific question → minimum-sufficient strategy

| Scientific question | Start from | Minimum-sufficient method | Evidence-driven escalation |
|---|---|---|---|
| Ground-state bonding, defect levels and trap states | charge/spin, symmetry, electrostatics and thermodynamic cycles | periodic/cluster DFT with convergence and finite-size control | hybrid DFT, embedding or higher-level wavefunction treatment |
| Excited states, optical spectra and carrier excitations | state character, selection rules and electron–hole degrees of freedom | TDDFT or a targeted excited-state calculation | GW/BSE, multireference or nonadiabatic dynamics |
| Reaction barriers, catalysis and selectivity | stoichiometry, detailed balance and candidate networks | DFT/wavefunction path search, NEB and transition-state optimisation | enhanced sampling, microkinetics, kinetic Monte Carlo and transport coupling |
| Conformations, solvation, free energies and rare events | ensemble, reservoirs, collective variables and correlation times | MD/Monte Carlo with umbrella, metadynamics or alchemical free energy | QM/MM, ab initio MD or a validated coarse-grained model |
| Polymer morphology, crystallisation and phase separation | entropy–energy competition, chain connectivity and order parameters | scaling/SCFT followed by CGMD, DPD or phase-field kinetics | chemistry-informed mapping, homogenisation and process–structure coupling |
| Flow, heat/mass transfer and pressure drop | conservation laws, constitutive closure and dimensionless groups | control-volume, 1D or reduced-order model | mesh-converged CFD and coupled multiphysics |
| Stress, viscoelasticity, fracture and fatigue | momentum/energy balance, material symmetry and constitutive identifiability | reduced mechanics or FEM with objective constitutive laws | phase-field/cohesive fracture and microstructure-informed mechanics |
| Charge transport, space charge and breakdown | electronic/trap states, electrochemical potential and Poisson/charge balance | hopping/kMC or drift–diffusion–Poisson | electrothermal, morphology-evolution and stochastic failure models |
| Reactors, molecular-weight distributions and process dynamics | mass/energy balances, residence time and identifiability | CSTR/PFR/network plus population-balance model | reactor-CFD, flowsheet dynamics, Bayesian calibration or digital-twin surrogate |
| Mixed or under-specified multiscale problem | observable, units, reservoirs, scales and competing mechanisms | analytical or reduced-order falsifiable model | sequential uncertainty-aware coupling through measurable bridge variables |

The strategy output remains `advisory-only` and records `solver_executed: false`. A recommended DFT, MD, FEM, CFD or process model becomes a real execution only after an approved checksum-bound handoff, external logs and output hashes, convergence review and separate scientific acceptance.

## Research lifecycle and workflows

```text
Frame → map evidence → design → execute/analyze → check → validate
      → accept/reject → communicate → archive
```

```text
proposed → planned → running → completed → checked → validated → accepted
                                      ↘ rejected / superseded
```

The 15 primary workflows are:

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

### Capability contracts by workflow

| Workflow | Contracts |
|---|---:|
| `computation-handoff` | 169 |
| `data-analysis` | 52 |
| `project-management` | 35 |
| `deep-research` | 16 |
| `scientific-writing` | 14 |
| `research-design` | 10 |
| `laboratory` | 8 |
| `research-integrity` | 8 |
| `patent-and-transfer` | 7 |
| `research-question` | 6 |
| `systematic-review` | 5 |
| `experiment-design` | 3 |
| `peer-review` | 3 |
| `technical-report` | 3 |
| `scientific-figure` | 2 |

### Workbook capability categories

| Category | Named contracts |
|---|---:|
| 催化、高分子与复合材料 | 30 |
| 计算化学与材料计算 | 30 |
| 分子动力学与多尺度 | 24 |
| 科研管理、专利与诚信 | 24 |
| 化工流程、动力学与数字孪生 | 22 |
| AI与机器学习科研 | 20 |
| HPC、云计算与可重复性 | 20 |
| 实验室自动化与仪器 | 20 |
| 数据统计与可视化 | 20 |
| 有限元与多物理场 | 20 |
| 科研写作与出版 | 20 |
| CFD、颗粒与加工过程 | 18 |
| 文献与知识工程 | 18 |
| 生物信息与医学科研 | 18 |
| 科研Agent与编排 | 18 |

## Scientific capability visual atlas

The following **25 AI-generated, repository-specific conceptual diagrams** describe the actual contracts, control flow, provenance, scientific reasoning and execution boundaries. They are documentation assets—not experimental observations, simulation outputs, or proof that an external engine ran.

<table>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/research_os_architecture.svg" alt="Research OS architecture"/><br/><strong>1 · Research OS architecture</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multi_agent_orchestration.svg" alt="Multi-agent orchestration"/><br/><strong>2 · Multi-agent orchestration</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_claim_graph.svg" alt="Evidence–claim graph"/><br/><strong>3 · Evidence–claim graph</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/multiscale_science_pipeline.svg" alt="Multiscale science pipeline"/><br/><strong>4 · Multiscale science pipeline</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/reproducibility_quality_gates.svg" alt="Reproducibility quality gates"/><br/><strong>5 · Reproducibility quality gates</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/computation_handoff_boundary.svg" alt="Computation handoff boundary"/><br/><strong>6 · Computation handoff boundary</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/project_state_machine.svg" alt="Project state machine"/><br/><strong>7 · Project state machine</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_landscape.svg" alt="Capability landscape"/><br/><strong>8 · Capability landscape</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/original_requirements_coverage.svg" alt="Original requirements coverage"/><br/><strong>9 · Original requirements coverage</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/capability_implementation_levels.svg" alt="Implementation levels"/><br/><strong>10 · Implementation levels</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/progressive_routing_loading.svg" alt="Progressive routing and loading"/><br/><strong>11 · Progressive routing and loading</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/project_ledgers_provenance.svg" alt="Project ledgers and provenance"/><br/><strong>12 · Project ledgers and provenance</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/evidence_citation_integrity_loop.svg" alt="Evidence and citation integrity"/><br/><strong>13 · Evidence and citation integrity</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/research_production_pipeline.svg" alt="Research production pipeline"/><br/><strong>14 · Research production pipeline</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/installation_compatibility_matrix.svg" alt="Installation compatibility"/><br/><strong>15 · Installation compatibility</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/supply_chain_release_attestation.svg" alt="Supply-chain attestation"/><br/><strong>16 · Supply-chain attestation</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/first_principles_strategy_ladder.svg" alt="First-principles strategy ladder"/><br/><strong>17 · First-principles strategy ladder</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_problem_method_decision_tree.svg" alt="Scientific problem method decision tree"/><br/><strong>18 · Problem → method decision tree</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/uncertainty_quantification_validation.svg" alt="Uncertainty quantification and validation"/><br/><strong>19 · UQ and model validation</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_integrity_causality_guard.svg" alt="Scientific integrity and causality guard"/><br/><strong>20 · Integrity and causality guard</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/laboratory_data_quality.svg" alt="Laboratory and data quality"/><br/><strong>21 · Laboratory and data quality</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/scientific_writing_evidence_chain.svg" alt="Scientific writing evidence chain"/><br/><strong>22 · Scientific writing evidence chain</strong></td></tr>
<tr><td width="50%" valign="top"><img src="docs/assets/ai/scientific_figure_edit_guard.svg" alt="Scientific figure edit guard"/><br/><strong>23 · Scientific figure edit guard</strong></td><td width="50%" valign="top"><img src="docs/assets/ai/human_approval_acceptance_boundary.svg" alt="Human approval and acceptance boundary"/><br/><strong>24 · Human approval boundary</strong></td></tr>
<tr><td colspan="2" valign="top"><img src="docs/assets/ai/polymer_multiscale_case_study.svg" alt="Polymer insulation multiscale case study"/><br/><strong>25 · Polymer-insulation multiscale strategy case</strong></td></tr>
</table>

The complete bilingual atlas is available in [docs/VISUAL_ATLAS.md](docs/VISUAL_ATLAS.md). Every SVG is self-contained, accessible through `<title>` and `<desc>`, checked into the repository, and validated against the README asset manifest.

## Quick start

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
python -m tsao_researcher --version
python -m tsao_researcher route "Design a traceable multiscale polymer study"
python -m tsao_researcher search "polymer molecular dynamics" --limit 10
```

Initialize and verify canonical project state:

```bash
python -m tsao_researcher init   --name "Polyolefin multiscale study"   --question "Which mechanisms connect processing history to product properties?"   --research-type mechanistic   --output .
python -m tsao_researcher verify .
```

Generate a first-principles computation/simulation strategy (advice only; no solver execution):

```bash
python -m tsao_researcher strategy \
  "How do trap states and morphology control space charge and breakdown?" \
  --observable "space charge" \
  --observable "breakdown strength" \
  --condition "applied electric field" \
  --evidence "PEA charge profile" \
  --output strategy.json
python scripts/validate_computation_strategy.py strategy.json
```

Create a guarded computation handoff:

```bash
python scripts/handoff_to_computation.py   --project .tsao-research   --out computation/handoff.json   --question "Which property must be computed?"   --property "target property"   --profile MD   --scale atomistic   --method "candidate method"   --boundary-condition "periodic box"   --metric "convergence metric"   --expected-output "validated result artifact"   --input-file data/input.dat
```

Record and verify a real external execution:

```bash
python -m tsao_researcher receipt record .   --handoff computation/handoff.json   --engine gromacs --engine-version 2026.1   --command gmx --command mdrun --exit-code 0   --output computation/result.dat   --started-at 2026-07-24T01:00:00Z   --finished-at 2026-07-24T01:10:00Z
python -m tsao_researcher receipt verify .
```

Export and verify a reproducibility capsule:

```bash
python -m tsao_researcher capsule export . --mode metadata --output project-metadata.zip
python -m tsao_researcher capsule export . --mode full --output project-full.zip
python -m tsao_researcher capsule verify project-full.zip
```

## Installation

```bash
python install.py --agent codex --scope user --dry-run
python install.py --agent claude --scope project --validate
python install.py --agent open-agent --scope project --target ./skills --force
```

PowerShell and shell wrappers are also provided: `install.ps1` and `install.sh`.

## Validation

The release 0.7.0 quality baseline was verified by GitHub Actions run `30525731965` on Ubuntu / Python 3.12 using the exact locked toolchain:

| Gate | Result |
|---|---:|
| Tests | **240 passed; 0 failed; 0 errors; 0 skipped** |
| Project line coverage | **95.726%** |
| Branch coverage | **92.708%** |
| Quality floor | **95% line / 90% branch** |
| Critical mutation tests | **24 / 24 killed; 0 survivors** |
| Performance baseline | **PASS** |
| Two source ZIP builds | **byte-identical** |
| Wheel and sdist isolated install | **PASS** |
| Ruff / Mypy / Bandit | **PASS** |
| Exact-lock dependency audit | **PASS; no known vulnerabilities** |

The current `main` commit is independently verified by the [Exact main attestation workflow](.github/workflows/main-attestation.yml). Successful runs publish an artifact named `exact-main-attestation-<commit SHA>`, so the commit does not need to embed a self-referential run ID.

Checked-in `docs/VALIDATION_EVIDENCE.json` remains deliberately `preflight/PARTIAL`; commit-bound PASS evidence is produced externally by CI to avoid self-referential commit claims.

## Machine-readable evidence and mapping

- [README audit report](docs/README_AUDIT_REPORT.md)
- [Capability coverage matrix](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [README architecture mapping](docs/README_ARCHITECTURE_MAPPING.md)
- [Validation evidence](docs/VALIDATION_EVIDENCE.json)
- [Interactive test dashboard](docs/test-dashboard.html)
- [Test dashboard SVG](docs/test-dashboard.svg)
- [Original requirements audit JSON](docs/ORIGINAL_REQUIREMENTS_AUDIT.json)
- [Scientific capability visual atlas](docs/VISUAL_ATLAS.md)

## Known limitations

- Live literature databases, PDF parsers and citation-network services are not bundled.
- Statistical, causal, DOE and ML methods are contracts and quality gates; numerical execution uses host tools.
- Plotting has a validated contract and runnable example, but no universal plotting daemon is bundled.
- DOCX, PPTX and LaTeX rendering rely on host capabilities.
- The strategy advisor derives quantum, statistical, continuum and multiscale method ladders, but DFT, MD, FEM, CFD, process simulators, HPC schedulers, instruments and laboratory robots remain external.
- Patent/FTO, medical, safety and integrity acceptance require qualified human review.
- A handoff is not a completed computation; a receipt is execution evidence, not scientific validity.

## License and provenance

TsaoSciResearcher is an original **Apache-2.0** implementation. No upstream source code or prompt corpus is bundled. Public projects informed architecture and taxonomy only; see [THIRD_PARTY.md](THIRD_PARTY.md) and [references/source-map.md](references/source-map.md).
