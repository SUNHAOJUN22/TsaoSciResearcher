# Validation model

TsaoSciResearcher separates validation layers. Passing a lower layer never implies that a higher layer has passed.

1. **Structural** — source inventory, encoding, links, manifests, workflows, schemas, capability shards and README facts.
2. **Language and type** — Python compilation, Ruff format/lint and strict Mypy.
3. **Security** — Bandit plus explicit filesystem, archive, command, workflow and secret checks.
4. **Behavioral** — unit, integration, regression, adversarial and property tests.
5. **Scientific contract** — project state, Claim–Evidence, statistical-method, Figure Contract and computation-handoff validation.
6. **Robustness** — reverse order, fixed-seed random order, mutation smoke, bounded performance smoke and cross-platform matrices.
7. **Release** — two byte-identical builds, SHA-256 sidecars and safe extraction into a fresh directory.
8. **Remote lifecycle** — pull-request CI, merge to `main`, post-merge CI and branch-governance verification remain distinct gates.
9. **Scientific acceptance** — qualified review of the actual evidence, model, experiment or calculation. Software checks do not grant this status.

## Canonical local validation

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps

python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/build_readme_facts.py --check
python scripts/generate_checksums.py --check
python scripts/build_capability_index.py --check
python scripts/route_task.py --self-test
python scripts/validate_figure.py examples/figure-contract.json

python -m pytest -q -p hypothesis.extra.pytestplugin
python -m ruff format --check scripts tsao_researcher tests
python -m ruff check scripts tsao_researcher tests
python -m mypy scripts tsao_researcher
python -m bandit -q -lll -r scripts tsao_researcher
python scripts/run_mutation_smoke.py
python scripts/performance_smoke.py --json-out artifacts/performance.json
```

## Deterministic release verification

```bash
python scripts/package_release.py --out dist-a
python scripts/package_release.py --out dist-b
cmp dist-a/TsaoSciResearcher-v0.5.1.zip dist-b/TsaoSciResearcher-v0.5.1.zip
python scripts/validate_release.py
```

## Release 0.5.1 evidence

The dated machine-readable evidence is stored in [`VALIDATION_EVIDENCE.json`](VALIDATION_EVIDENCE.json). The release CI run recorded:

- 96 pytest tests with zero failures, errors or skips;
- 15/15 critical mutants killed;
- Ubuntu/Python 3.10 and 3.13, Windows/Python 3.12 and macOS/Python 3.12 compatibility;
- complete regression, reverse/random order, static/type/security, performance and reproducible-release gates.

## Truth boundaries

- A workflow file existing does not prove that its external task was executed.
- A locally passing suite does not prove that a pull request, `main` or a release asset passed.
- A computation handoff is a specification, not a completed scientific calculation.
- Capability metadata records routing and validation intent; it does not prove that an external database, instrument or solver is installed.
- A source ZIP is not verified unless its independently downloaded sidecar matches the ZIP bytes.
- `completed`, `checked`, `validated` and `accepted` are separate states.
