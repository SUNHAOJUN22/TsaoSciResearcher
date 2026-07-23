<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="112" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>Evidence-first scientific research control layer</strong></p>
  <p>Question → evidence → design → analysis/execution → validation → artifact</p>

[简体中文](README.zh-CN.md) · [Architecture](docs/ARCHITECTURE.md) · [Validation](docs/VALIDATION.md) · [Security](SECURITY.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **Release 0.5.3** · Apache-2.0 · Python 3.10–3.13 · Windows, Linux and macOS

## Purpose

TsaoSciResearcher turns a scientific request into a bounded, traceable workflow with explicit evidence, project state, validation and qualified human-approval gates. It does **not** claim that a search, experiment, solver, instrument or external computation ran unless an execution record exists.

## Verified repository scope

The inventory below is generated from repository contracts and checked by the validation tooling.

| Item | Verified value |
|---|---:|
| Capability records | **340** |
| Named AI-for-Science catalog contracts | **322** |
| General research/compatibility contracts | **158** |
| Named computation/engineering domain contracts | **164** |
| Generic domain placeholders | **0** |
| Native runtime/core contracts | **18** |
| Gated workflows | **15** |
| JSON Schemas | **15** |
| Domain packs | **7** |
| Progressive-load references | **22** |
| Templates | **13** |

```text
340 = 322 named AI-for-Science contracts + 18 runtime/core contracts
322 = 158 general research contracts + 164 named domain contracts
```

A capability contract describes routing, inputs, outputs, validation and delegation. It is not proof that an external scientific engine is installed or that a calculation was executed.

## Implemented architecture

- **Single entry and progressive loading** — `SKILL.md` selects one primary workflow before detailed references are loaded.
- **Deterministic bilingual routing** — bounded input, cached rules, negative-intent handling and stable tie-breaking.
- **Full research lifecycle** — question framing, evidence, design, statistics, figures, writing, review, laboratory governance, integrity, patent and project workflows.
- **Traceable project state** — atomic writes, locks, lifecycle transitions and a SHA-256 event chain.
- **Evidence and claim controls** — schema validation, bidirectional links, source locators, citation checks and non-zero failure exits.
- **Scientific figure controls** — figure contracts, units/statistics checks and PNG/SVG/PDF/TIFF export validation.
- **Guarded computation handoff** — checksummed inputs, path containment, convergence/UQ requirements and approval points.
- **Reproducible engineering** — repository audit, static analysis, mutation tests, order-independent tests, performance guards and byte-identical release builds.

## Executable scientific-quality guards

The `quality` command exposes four deterministic controls:

| Guard | Purpose |
|---|---|
| **Measurement Boundary** | Declares measurand, method, sample, conditions, units, calibration/reference, uncertainty, applicability, exclusions and optional traceability metadata. |
| **Structure–Property Planner** | Records intervention, structure, measurable mediator, response, confounders, alternatives, validation, uncertainty, scale bridge, statistics and conservation constraints. |
| **Causality Guard** | Separates association, mechanism-consistent inference and bounded causal claims; detects unsupported English and Chinese causal wording. |
| **Evidence Traceability** | Links claims to evidence IDs and source locators and blocks execution claims that lack execution receipts. |

```bash
python -m tsao_researcher quality examples/scientific-quality-check.json
```

These controls generalize research-method rules without hard-coding a material-specific result. Statistical physics can provide conservation, distributional and uncertainty constraints, but project conclusions remain evidence- and applicability-bound.

## Boundaries

| Capability | Status |
|---|---|
| Research orchestration, validation and artifact governance | Native |
| Retrieval, plotting and Office production | Uses tools supplied by the host agent |
| DFT, MD, FEM, CFD, process simulation, HPC and laboratory execution | Delegated through `computation-handoff` |
| Medical, safety, legal/FTO, integrity and final scientific acceptance | Qualified human approval required |

The scientific-engine catalog contains ecosystem integration targets, not bundled executors.

## Quick start

### Install

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
```

### Route and search

```bash
python -m tsao_researcher route "Design a traceable multiscale polymer study"
python -m tsao_researcher search "gromacs trajectory analysis" --limit 10
python -m tsao_researcher search "non-newtonian flow" --domain cfd-particles-processing
```

### Initialize a project

```bash
python -m tsao_researcher init \
  --name "Polyolefin multiscale study" \
  --question "Which mechanisms connect processing history to product properties?" \
  --research-type mechanistic \
  --output .
```

The canonical project layout is created under `.tsao-research/` and contains questions, hypotheses, evidence, claims, decisions, artifacts, risks, approvals, state events, data, computation records, figures, reports and protocols.

### Advance and verify state

```bash
python -m tsao_researcher transition . planned --reason "question and plan approved"
python -m tsao_researcher transition . running --reason "registered work started"
python -m tsao_researcher verify .
```

```text
proposed → planned → running → completed → checked → validated → accepted
```

`rejected` and `superseded` are also supported. `accepted` requires a recorded approval.

## Workflows

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

Each workflow contains a human-readable policy, a machine contract and entry, blocking and completion gates.

## Validation

Run the core checks locally:

```bash
python scripts/validate_schemas.py
python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/build_readme_facts.py --check
python scripts/build_test_dashboard.py --check
python scripts/build_validation_evidence.py --check
python scripts/build_research_quality_dashboard.py --check
python scripts/build_engineering_report.py --check
python scripts/generate_checksums.py --check
python -m pytest -q -p hypothesis.extra.pytestplugin
python scripts/performance_smoke.py
```

CI additionally runs Python compatibility jobs on Windows, Linux and macOS, Ruff formatting/lint, strict Mypy, Bandit, critical mutation checks, reverse and seeded-random test order, bounded performance and byte-identical release packaging.

Reproducible release check:

```bash
VERSION="$(cat VERSION)"
python scripts/package_release.py --out dist-a
python scripts/package_release.py --out dist-b
cmp "dist-a/TsaoSciResearcher-v${VERSION}.zip" \
    "dist-b/TsaoSciResearcher-v${VERSION}.zip"
```

## Visual validation interfaces

![Automated test dashboard](docs/test-dashboard.svg)

- [Open the interactive test dashboard](docs/test-dashboard.html)
- [View the static test dashboard](docs/test-dashboard.svg)
- [Open the scientific-quality dashboard](docs/research-quality-dashboard.html)
- [View the scientific-quality SVG report](docs/research-quality-dashboard.svg)
- [Read the machine-readable scientific-quality examples](docs/SCIENTIFIC_QUALITY_EXAMPLES.json)
- [Download the engineering audit PDF](docs/engineering-audit-report.pdf)
- [Read the machine-readable validation evidence](docs/VALIDATION_EVIDENCE.json)

The dashboards are deterministic generated artifacts. They visualize software and research-method gates; they do not replace scientific review or prove external execution.

## Design and audit evidence

- [README audit report](docs/README_AUDIT_REPORT.md)
- [Capability coverage matrix](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [Design → code → test mapping](docs/README_ARCHITECTURE_MAPPING.md)
- [Machine-readable README facts](docs/README_FACTS.json)
- [Project integration audit](docs/PROJECT_INTEGRATION_2026-07-23.md)
- [Latest validation evidence](docs/VALIDATION_EVIDENCE.json)

## Known limitations

- External scientific engines, instruments and databases are not bundled.
- A planned handoff is not an execution receipt.
- Scientific-quality guards constrain wording and completeness but do not establish scientific truth by themselves.
- Material-specific trends, phase assignments and mechanism conclusions require project evidence, uncertainty and applicability boundaries.

## Development, security and license

Changes should preserve deterministic outputs, cross-platform paths, strict validation and the truth boundary between planning and execution. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [THIRD_PARTY.md](THIRD_PARTY.md) and [references/source-map.md](references/source-map.md).

TsaoSciResearcher is an original Apache-2.0 implementation. It is inspired by public scientific-agent and research-tool projects but is not their official fork or replacement.
