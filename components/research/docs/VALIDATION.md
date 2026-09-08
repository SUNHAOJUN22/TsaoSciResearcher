# Validation model

Passing software checks does not grant scientific acceptance. The validation stack is:

1. version, manifests, links and schema contracts;
2. compilation, Ruff and strict Mypy;
3. archive/filesystem security, Bandit and dependency audit;
4. unit, integration, property, adversarial and tamper tests;
5. line and branch coverage thresholds;
6. reverse/random order and critical mutation tests;
7. bounded performance and deterministic reports;
8. deterministic source ZIP, wheel/sdist and isolated install;
9. SBOM, checksums and external commit attestation;
10. qualified review of actual scientific evidence.

## Complete local validation

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
mkdir -p artifacts
python scripts/sync_version.py --check
python scripts/validate_schemas.py
python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/build_readme_facts.py --check
python scripts/build_sbom.py --check
python scripts/build_validation_evidence.py --check
python scripts/build_test_dashboard.py --check
python scripts/build_research_quality_dashboard.py --check
python scripts/build_engineering_report.py --check
python scripts/generate_checksums.py --check
python -m pytest -q -p hypothesis.extra.pytestplugin --junitxml=artifacts/junit.xml
python -m pytest -q -p hypothesis.extra.pytestplugin -p pytest_cov --ignore=tests/test_import_isolation.py --cov=tsao_researcher --cov-branch --cov-report=json:artifacts/coverage.json
python -m pytest -q -p hypothesis.extra.pytestplugin -p tests.reverse_order_plugin
TSR_TEST_ORDER_SEED=20260724 python -m pytest -q -p hypothesis.extra.pytestplugin -p tests.random_order_plugin
python -m ruff format --check scripts tsao_researcher tests
python -m ruff check scripts tsao_researcher tests
python -m mypy scripts tsao_researcher
python -m bandit -q -lll -r scripts tsao_researcher
python -m pip_audit --strict
python scripts/run_mutation_smoke.py --json-out artifacts/mutation-results.json
python scripts/performance_smoke.py --json-out artifacts/performance.json
python scripts/check_quality_baseline.py
mkdocs build --strict
python scripts/package_release.py --out dist-a
python scripts/package_release.py --out dist-b
cmp "dist-a/TsaoSciResearcher-v$(cat VERSION).zip" "dist-b/TsaoSciResearcher-v$(cat VERSION).zip"
python -m build --sdist --wheel --outdir dist-python
python scripts/validate_distribution.py dist-python
```

`ci.yml` runs on main and pull requests; `audit.yml` provides a manual full audit; `nightly.yml` checks environment drift weekly; `release.yml` publishes only a validated version tag.

## Quality history

`docs/QUALITY_HISTORY.json` records release-scoped coverage, mutation, test and performance evidence. CI produces an idempotent current-tree history artifact; entries with `local-preflight` or missing metrics remain explicitly partial.

The process-isolation test module is part of complete regression but intentionally excluded from coverage collection so its fresh subprocesses do not inherit pytest-cov state.

## Performance gate scope

`scripts/performance_smoke.py` is a bounded software-regression gate, not evidence that an external DFT, MD, FEM, CFD, process-simulation, or laboratory engine ran faster. It measures implemented repository paths with deterministic inputs:

- 10,000 legacy routes and 10,000 v2 routes with unique request suffixes;
- 3,000 strategy-advisor requests spanning dielectric transport, continuum flow, and reaction kinetics while checking the advisory-only execution boundary;
- 100 defensive loads of each capability catalog and 1,000 mixed capability searches across molecular simulation, electronic structure, CFD, experimental design, and evidence integrity;
- JSONL reading, claim–evidence validation, all schemas, bounded ZIP validation, install/uninstall, and two byte-identical source-release builds.

Thresholds are intentionally platform-tolerant and detect large regressions. Any speedup claim must additionally report the execution environment, before/after measurements, numerical or semantic equivalence evidence, and whether the workload is warm-cache, cold-cache, repeated, or mixed.

## Scientific Passport contract gates

The computation-strategy schema requires a Scientific Passport and integrity gates. Regression verifies evidence maturity `E0`–`E4`, declared-only evidence semantics, deterministic passport binding, unsupported causal-language review, blocked unbridged scale jumps, competing-mechanism requirements, and rejection of fabricated maturity values.


## Decision-readiness contract

Computation-strategy schema 1.3 requires item-level evidence inventory, a claim contract and a decision-readiness record. Validation must reject automatic approval, invalid evidence identifiers, out-of-range maturity values and unknown readiness states. A `ready-for-human-review` result is planning readiness only; it is not execution, validation or scientific acceptance.


## Quantitative-integrity and transferability gates

Computation-strategy Schema 1.3 and Scientific Passport 1.2 add four conservative planning controls:

- quantity/unit parsing, normalized dimensions, missing-unit review and incompatible-dimension blocking;
- declared applicability domains, explicit extrapolation detection and independent transfer-evidence review;
- stable supporting/challenging/neutral evidence identifiers with conflict retention;
- structural/practical identifiability, competing-mechanism comparison and equifinality blocking.

These gates are deterministic software controls. They do not validate the caller's measurements, certify unit conversions for every specialist ontology, prove a mechanism or grant scientific acceptance. Regression includes normal, missing-unit, contradictory-evidence, extrapolation and deliberately incompatible-dimension cases.
