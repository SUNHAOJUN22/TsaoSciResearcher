<div align="center">
  <img src="assets/logo.svg" alt="TsaoSciResearcher" width="112" />
  <h1>TsaoSciResearcher</h1>
  <p><strong>Evidence-first scientific research control layer</strong></p>
  <p>Question → evidence → design → analysis/execution → validation → artifact</p>

[简体中文](README.zh-CN.md) · [Architecture](docs/ARCHITECTURE.md) · [Validation](docs/VALIDATION.md) · [Security](SECURITY.md)

[![CI](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SUNHAOJUN22/TsaoSciResearcher/actions/workflows/ci.yml)
</div>

> **Release 0.5.2** · Apache-2.0 · Python 3.10–3.13 · Windows, Linux and macOS

## In one sentence

TsaoSciResearcher turns a scientific request into a bounded, traceable workflow with explicit evidence, state, validation and human-approval gates.

It does **not** pretend that a search, experiment, solver or instrument ran when no execution record exists.

## Verified scope

The following values are generated from the repository and checked in CI:

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

The 322 contracts preserve the catalog slugs and names. A contract describes routing, inputs, outputs, validation and delegation; it is not proof that an external scientific engine is installed.

## What is implemented

- **Single entry and progressive loading** — `SKILL.md` selects one primary workflow before loading detailed references.
- **Deterministic bilingual routing** — cached rules, bounded input, stable tie-breaking and negative intent such as “analyze existing results only”.
- **Full research lifecycle** — question, evidence, experiment/research design, statistics, figures, writing, review, laboratory governance, patent/integrity and project management.
- **Traceable project state** — atomic writes, locks, lifecycle transitions and a SHA-256 event chain.
- **Evidence and claim controls** — schema validation, bidirectional links, citation checks and non-zero failure exits.
- **Scientific figure controls** — figure contract, units/statistics checks and PNG/SVG/PDF/TIFF export validation.
- **Guarded computation handoff** — checksummed inputs, convergence/UQ requirements, path containment and approval points.
- **Cross-platform installation** — Codex, Claude Code and Open Agent Skills; user/project scope; dry-run, validate and uninstall.
- **Reproducible engineering** — repository audit, static checks, mutation tests, order-independent tests, performance guards and byte-identical release builds.

## Boundaries

| Capability | Status |
|---|---|
| Research orchestration, validation and artifacts | Native |
| Retrieval, plotting and Office production | Uses tools available in the host agent |
| DFT, MD, FEM, CFD, process simulation, HPC and laboratory execution | Delegated through `computation-handoff` |
| Medical, safety, legal/FTO, integrity and final scientific acceptance | Qualified human approval required |

The 32 engines listed in the uploaded AI-for-Science workbook are ecosystem targets, not bundled executors.

## Quick start

### Install the package

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -e .
```

### Route a task

```bash
python -m tsao_researcher route "Design a traceable multiscale polymer study"
```

### Search named capabilities

```bash
python -m tsao_researcher search "gromacs trajectory analysis" --limit 10
python -m tsao_researcher search "non-newtonian flow" --domain cfd-particles-processing
```

### Initialize one canonical project state

```bash
python -m tsao_researcher init \
  --name "Polyolefin multiscale study" \
  --question "Which mechanisms connect active-site kinetics to product properties?" \
  --research-type mechanistic \
  --output .
```

The CLI and `scripts/init_project.py` now create the same layout:

```text
.tsao-research/
├── project.yaml
├── questions.json
├── hypotheses.json
├── evidence.jsonl
├── claims.jsonl
├── decisions.jsonl
├── artifacts.jsonl
├── risks.json
├── approvals.jsonl
├── state/events.jsonl
├── registry/
├── literature/
├── data/
├── computation/
├── artifacts/
├── figures/
├── reports/
└── protocols/
```

Advance and verify state:

```bash
python -m tsao_researcher transition . planned --reason "question and plan approved"
python -m tsao_researcher transition . running --reason "registered work started"
python -m tsao_researcher verify .
```

Lifecycle states remain distinct:

```text
proposed → planned → running → completed → checked → validated → accepted
```

`rejected` and `superseded` are also supported. `accepted` requires a recorded approval.

### Register a computation handoff

```bash
printf "input" > .tsao-research/data/input.dat
python scripts/handoff_to_computation.py \
  --project .tsao-research \
  --out computation/job.json \
  --question "What property should be computed?" \
  --property "free energy" \
  --profile MD \
  --scale atomistic \
  --method "enhanced sampling" \
  --boundary-condition "periodic box" \
  --metric "free-energy convergence" \
  --expected-output "PMF profile" \
  --input-file data/input.dat
python -m tsao_researcher verify .
```

The v2 handoff is checksummed, path-contained and registered in both `project.yaml` and `artifacts.jsonl`. It records a planned external computation; it is not an execution receipt.

## The 15 workflows

```text
research-question      deep-research          systematic-review
research-design        experiment-design      data-analysis
scientific-figure      scientific-writing     peer-review
technical-report       project-management     patent-and-transfer
research-integrity     laboratory             computation-handoff
```

Each workflow contains a human-readable policy, a machine contract and entry/blocking/completion gates.

## Validation

Run the same core checks locally:

```bash
python scripts/validate_schemas.py
python scripts/build_readme_facts.py --check
python scripts/build_test_dashboard.py --check
python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/generate_checksums.py --check
python -m pytest -q -p hypothesis.extra.pytestplugin
python scripts/performance_smoke.py
```

Reproducible release check:

```bash
VERSION="$(cat VERSION)"
python scripts/package_release.py --out dist-a
python scripts/package_release.py --out dist-b
cmp "dist-a/TsaoSciResearcher-v${VERSION}.zip" \
    "dist-b/TsaoSciResearcher-v${VERSION}.zip"
```

CI additionally runs Ruff, strict Mypy, Bandit, critical mutation tests, reverse/seeded-random test order and compatibility jobs on Windows, Linux and macOS.

## Test dashboard

![Automated test dashboard](docs/test-dashboard.svg)

- [Open the interactive HTML dashboard](docs/test-dashboard.html)
- [Read the machine-readable validation evidence](docs/VALIDATION_EVIDENCE.json)

The dashboard is generated from recorded validation evidence and checked in CI. It visualizes software gates; it does not replace scientific review or human approval.

## Design verification

Detailed evidence is kept outside the README so this page stays short:

- [README audit report](docs/README_AUDIT_REPORT.md)
- [322-skill coverage matrix](docs/CAPABILITY_COVERAGE_MATRIX.md)
- [Design → code → test mapping](docs/README_ARCHITECTURE_MAPPING.md)
- [Machine-readable README facts](docs/README_FACTS.json)
- [Latest CI evidence](docs/VALIDATION_EVIDENCE.json)

## License and upstream boundary

TsaoSciResearcher is an original Apache-2.0 implementation. It is inspired by public scientific-agent and research-tool projects, but is not their official fork or replacement. No upstream prompt corpus or source code is bundled. See [THIRD_PARTY.md](THIRD_PARTY.md) and [references/source-map.md](references/source-map.md).
