# TsaoSciResearcher 0.4.0

**TsaoSciResearcher** is an evidence-first Agent Skill for scientific and engineering research. It converts broad objectives into testable questions, traceable evidence, experiment and analysis contracts, Figure Contracts, manuscripts, reports and governed research artifacts.

[Chinese README](README.md) · [Architecture](docs/ARCHITECTURE.md) · [158 capabilities](capability-index/capabilities.md) · [Validation](docs/VALIDATION.md) · [v0.4.0 audit](docs/AUDIT_REPORT_V040.md)

## Verified source composition

| Component | Count/status |
|---|---:|
| Progressive workflows | 15 |
| Searchable capability records | 158 |
| Draft 2020-12 JSON Schemas | 8 |
| Python compatibility matrix | 3.10–3.13 on Linux, Windows and macOS |
| Real DFT/MD/FEM/CFD/process simulation | Delegated to an actual solver |

## Truth boundaries

- `completed` is not equivalent to `checked`, `validated` or `accepted`.
- A passing local suite does not prove that PR CI, post-merge main CI or Release verification passed.
- A capability record is routing metadata; it does not prove that an external database, instrument or solver is installed.
- A computation handoff is a specification, not an executed computation.

## v0.4.0 correctness and security work

- Managed atomic installation and uninstall with target ownership, staging, backup and rollback.
- Zip Slip, absolute-path, symbolic-link, duplicate-path, expansion-size and compression-ratio defenses.
- Byte-identical deterministic ZIP builds with external SHA-256 sidecars and fresh-directory extraction checks.
- Finite standard JSON, atomic state writes, collision-resistant project IDs and explicit state invariants.
- Bidirectional Claim–Evidence links and support/refute consistency.
- Unicode-normalized routing with word boundaries, stable ties, bounded input and cached rules.
- Adversarial, property, mutation, performance and cross-platform validation.
- Immutable GitHub Action SHAs and read-only workflow permissions.

## Install and validate

```bash
git clone https://github.com/SUNHAOJUN22/TsaoSciResearcher.git
cd TsaoSciResearcher
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
```

Install for Codex:

```bash
python scripts/install.py --agent codex --scope user --validate
```

Initialize a traceable project:

```bash
python scripts/init_project.py \
  --name "example" \
  --question "What mechanism is being tested?" \
  --research-type mechanistic \
  --output .
python scripts/validate_project.py .tsao-research/project.yaml
```

Route a task:

```bash
python scripts/route_task.py "design a reproducible molecular dynamics study"
```

## Evidence, figures and computation

```bash
python scripts/validate_evidence.py .tsao-research/evidence.jsonl
python scripts/validate_claims.py .tsao-research/claims.jsonl --evidence .tsao-research/evidence.jsonl
python scripts/validate_figure.py examples/figure-contract.json
python scripts/handoff_to_computation.py --project .tsao-research --out .tsao-research/computation-handoff.json
```

A real computation is complete only after an actual solver produces versioned inputs, logs, convergence evidence, outputs and checksums.

## Validation gates

```bash
python scripts/audit_repository.py
python -m compileall -q scripts tests
python -m pytest -q
python -m ruff check scripts tests
python scripts/run_mutation_smoke.py
python scripts/performance_smoke.py
python scripts/validate_release.py
```

See [docs/VALIDATION.md](docs/VALIDATION.md) for the evidence hierarchy and [`docs/audit/defects-v0.4.0.json`](docs/audit/defects-v0.4.0.json) for the machine-readable defect ledger.

## License

Apache-2.0. Third-party inspiration and license boundaries are recorded in `THIRD_PARTY.md` and `references/source-map.md`.
