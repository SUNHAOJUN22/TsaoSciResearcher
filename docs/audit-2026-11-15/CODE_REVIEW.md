# Code review and automated validation — 2026-11-15

## Scope

Reviewed from `c196e167a5c6d6431090845fd3736313404394a2` on `main`.
The review covered repository and distribution boundaries, handoff construction,
execution-receipt identity, input snapshots, scientific-state contracts, generated
metadata, and the declared test, type, security, mutation and packaging gates.
Manual inspection concentrated on these boundaries; automated gates scanned the
repository's declared source and test scopes.

## Reproduced defects and repairs

| Priority | Defect | Repair and regression evidence |
| --- | --- | --- |
| P1 | A string such as `"false"` was accepted as truthy handoff readiness. Invalid input containers reached path handling, and path aliases could register one input multiple times. | Require a real boolean and a list of nonblank input paths; reject duplicate resolved paths before publishing a handoff or changing project state. |
| P1 | Receipt creation stripped command arguments and environment values. It also trimmed file paths, so requesting a leading-space filename could record the hash of a different file. | Preserve exact argument strings, environment values and file paths. Permit empty or whitespace-only argument values after a nonblank executable; reject NUL-bearing command vectors. Align the JSON Schema with the runtime contract. |
| P1 | Output aliases could bypass duplicate checks during both receipt creation and later verification. | Compare resolved project-relative paths in both paths. A tampered receipt naming the same file through `./` aliases is rejected. |
| P2 | Source audits and mutation snapshots included `.venv`/`venv` dependency trees. This caused false source violations and made copied release fixtures exceed their file limit. | Exclude generated virtual environments consistently in the legacy audit, structure validator and mutation snapshot copier. Source files remain in scope. |

The candidate regression cases were executed before repair. The initial tests
reproduced 22 failures, including the source-audit contamination; subsequent
focused negative controls reproduced two receipt-verifier/argument failures,
four environment-boundary failures, and one output-path identity failure.
The new tests exercise public behaviors and failed publication, not just code shape.

## Local validation

Environment: Linux, Python 3.12.14. Imports were checked against this checkout;
the prior working directory and its environment were left unchanged.

| Gate | Observed result |
| --- | --- |
| Complete regression, normal order | 969 passed, plus 3 subtests |
| Reverse order and seeded random order (`20260806`) | 969 passed, plus 3 subtests, in each order |
| Coverage suite, with the CI import-isolation exclusion | 961 passed, plus 3 subtests |
| Coverage | Statements 95.99%; branches 93.37%; combined 95.26%; required combined minimum 85% |
| Ruff formatting / lint | Passed; 147 Python files checked for formatting |
| Strict mypy | Passed; 68 source files |
| Bandit high-severity scan | Passed |
| Critical mutation smoke | 24 of 24 mutants killed after clean baselines |
| Dependency audit | 66 resolved packages; no known vulnerabilities reported |
| Runtime data, versions, schemas, mathematical and figure contracts | Passed |
| Repository/structure audit, routing and final preflight | Passed |
| Strict MkDocs build and acceptance-controller tests | Passed |
| Source archive reproducibility and release validator | Passed |
| Wheel and sdist build and isolated wheel installation | Passed |

One existing Python deprecation warning is emitted by the deliberate multithreaded
fork regression. It is recorded as a warning rather than a test failure.

Generated README facts, preflight evidence and tree checksums are refreshed for
the final staged file inventory. Checked-in preflight evidence remains explicitly
partial; the exact commit's GitHub Actions run supplies the external CI attestation.
The local run covers Linux/Python 3.12, while the workflow also checks its declared
Windows and Python-version matrix. No external scientific solver was run.

## Reproduction

```bash
python -m pytest -p hypothesis.extra.pytestplugin --junitxml=artifacts/junit.xml
python -m pytest -p hypothesis.extra.pytestplugin -p pytest_cov \
  --ignore=tests/test_import_isolation.py --cov=tsao_researcher --cov-branch \
  --cov-report=json:artifacts/coverage.json
python -m pytest -p hypothesis.extra.pytestplugin -p tests.reverse_order_plugin
TSR_TEST_ORDER_SEED=20260806 python -m pytest \
  -p hypothesis.extra.pytestplugin -p tests.random_order_plugin
python scripts/run_mutation_smoke.py --json-out artifacts/mutation-results.json
python scripts/validate_structure.py
python scripts/build_validation_evidence.py --check
python scripts/generate_checksums.py --check
```

CI contains the complete ordered command list and produces the machine-readable
coverage, JUnit, distribution and attestation artifacts.
