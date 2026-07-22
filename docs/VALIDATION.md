# Validation model

TsaoSciResearcher separates evidence layers. A lower layer passing does not imply a higher layer passed.

1. **Structural** — inventory, encoding, links, manifests, schemas and capability shards.
2. **Language and type** — Python compilation, Ruff and strict mypy for the audited core.
3. **Security** — Bandit plus explicit filesystem, archive, command and workflow checks.
4. **Behavioral** — unit, integration, regression, adversarial and property tests.
5. **Scientific contract** — project state, Claim–Evidence, statistical-method and Figure Contract validation.
6. **Robustness** — mutation smoke, performance smoke and cross-platform matrices.
7. **Release** — two byte-identical builds, external SHA-256 sidecars and extraction into a fresh directory.
8. **Remote lifecycle** — PR CI, post-merge main CI and downloaded Release-asset verification are separate gates.

## Local validation

```bash
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
python -m ruff check scripts tests
python -m mypy scripts/common.py scripts/route_task.py scripts/archive_safety.py scripts/package_release.py scripts/install.py scripts/init_project.py scripts/validate_project.py scripts/validate_evidence.py scripts/validate_claims.py scripts/validate_release.py
python -m bandit -q -lll -r scripts
python scripts/run_mutation_smoke.py
python scripts/performance_smoke.py
python scripts/validate_release.py
```

## Truth boundaries

- A workflow file existing does not prove that a CI run occurred.
- A locally passing suite does not prove that PR or main checks passed.
- A computation handoff is a specification, not a completed scientific calculation.
- Capability metadata records routing intent; it does not prove that external databases, instruments or solvers are installed.
- A source ZIP is not verified unless its separately downloaded sidecar matches the downloaded ZIP bytes.
