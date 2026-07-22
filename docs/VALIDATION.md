# Validation model

Passing software checks does not grant scientific acceptance. TsaoSciResearcher keeps these layers separate:

1. source structure, links, manifests, schemas and README facts;
2. Python compilation, Ruff and strict Mypy;
3. filesystem/archive/security checks and Bandit;
4. unit, integration, property and adversarial tests;
5. state, evidence, claim, figure and computation-handoff contracts;
6. reverse/random test order, mutation and performance guards;
7. byte-identical release builds and safe extraction;
8. qualified review of the actual scientific evidence or execution.

## Canonical local validation

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps

python scripts/validate_schemas.py
python scripts/build_readme_facts.py --check
python scripts/audit_repository.py
python scripts/validate_structure.py
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

## Deterministic release

```bash
VERSION="$(cat VERSION)"
ARCHIVE="TsaoSciResearcher-v${VERSION}.zip"
python scripts/package_release.py --out dist-a
python scripts/package_release.py --out dist-b
cmp "dist-a/${ARCHIVE}" "dist-b/${ARCHIVE}"
python scripts/validate_release.py
```

The latest dated results are recorded in [`VALIDATION_EVIDENCE.json`](VALIDATION_EVIDENCE.json). CI runs compatibility jobs on Ubuntu/Python 3.10 and 3.13, Windows/Python 3.12 and macOS/Python 3.12, followed by full regression, static/type/security, mutation, order-independence, performance and reproducible-release gates.

## Truth boundaries

- A contract is not an execution record.
- A computation handoff is not a completed calculation.
- A named engine is not an installed integration.
- `completed`, `checked`, `validated` and `accepted` are distinct states.
