# Project integration audit - 2026-07-23

## Scope

This record documents the bounded integration of accumulated scientific-research requirements into `TsaoSciResearcher` directly on `main`. No branch and no pull request were created.

## Integrated principles

The implementation now expresses the requested practices as configurable, domain-independent controls:

- evidence-first claim control, source locators and bidirectional traceability;
- explicit distinction between planned work, delegated execution and execution receipts;
- Measurement Boundary fields for measurand, method, sample, conditions, units, calibration/reference, uncertainty, applicability, exclusions and traceability;
- Structure-Property planning for intervention, multiscale structure, measurable mediator, response, confounders, alternatives, predictions, validation, uncertainty, scale bridges, statistics and conservation constraints;
- Causality Guard separation of association, mechanism-consistent inference and bounded causal claims, including unsupported English and Chinese causal wording;
- physical consistency, units, statistical distributions, uncertainty, applicability and reproducibility constraints;
- qualified human approval for high-consequence scientific, safety, legal, medical and integrity decisions;
- deterministic HTML/SVG dashboards, machine-readable JSON evidence and a generated engineering PDF report.

## Domain adaptation rule

Polyolefin and cable-insulation experience is retained only as a configurable research pattern:

`processing history -> multiscale structure -> traps/interfaces/transport -> macroscopic properties`

This pattern is not encoded as a universal conclusion. Material-specific numbers, phase assignments, trap interpretations and property trends require project evidence, measurement boundaries, competing hypotheses, uncertainty and an explicit applicability domain.

## Corrected defects

The integration corrected the following concrete repository problems:

1. release metadata drift: `VERSION` and `pyproject.toml` were `0.5.3` while README and validation artifacts still reported `0.5.2`;
2. the scientific-quality JSON generator returned a list while the engineering PDF generator required an object root, which blocked deterministic PDF generation;
3. causal booleans could accept truthy strings instead of strict JSON booleans;
4. causal overclaim detection did not cover Chinese wording;
5. evidence-to-source locators and execution-receipt checks were missing from the quality dispatcher;
6. the old dashboard assumed every recorded status was `PASS` and could not represent `NOT_RUN` honestly;
7. validation evidence retained an obsolete simulated-permanent-tree marker;
8. the repository checksum still represented the earlier tree and is now explicitly deferred in composite-evidence mode rather than presented as current;
9. duplicate manual v0.5.3 audit pages and the obsolete one-shot workflow/status file were removed.

## Test and validation evidence

### Recorded full-repository baseline

GitHub Actions run `30005498100`, triggered from commit `420327139eda539f311fa8cd37709c226a374e44`, completed these stages successfully:

1. exact dependency installation and package verification;
2. deterministic artifact generation;
3. schema, repository, structure, README, dashboard and report gates;
4. complete regression and JUnit evidence export;
5. reverse-order and seeded-random-order regression;
6. Ruff, strict Mypy and Bandit;
7. critical mutation, bounded performance and byte-identical release checks;
8. final generated-state verification.

The run failed only at the final Git publication transport step after `main` moved. This is recorded as a publication failure, not as a test failure.

### Focused current-change regression

The changed scientific-quality and visual-report modules passed `14/14` tests in an isolated Python 3.13 sandbox:

```bash
python -m pytest -q \
  tests/test_scientific_quality.py \
  tests/test_visual_report_contract.py
```

The tested scope covered:

- `tsao_researcher/scientific_quality.py`;
- `tests/test_scientific_quality.py`;
- `scripts/build_research_quality_dashboard.py`;
- `scripts/build_test_dashboard.py`;
- `scripts/build_engineering_report.py`;
- `tests/test_visual_report_contract.py`.

### Current-tree limitation

Connector-created Contents API commits did not emit an observable GitHub Actions run during this execution. Therefore:

- current-tree end-to-end CI is recorded as `NOT_RUN`;
- no current-main source-tree digest is asserted;
- cross-platform statuses are explicitly retained as the last complete baseline;
- composite evidence must not be interpreted as a fresh current-tree CI receipt.

## Published visual interfaces

- `docs/test-dashboard.html` — interactive scoped test dashboard;
- `docs/test-dashboard.svg` — static test evidence graphic;
- `docs/research-quality-dashboard.html` — interactive scientific-quality dashboard;
- `docs/research-quality-dashboard.svg` — static scientific-quality graphic;
- `docs/SCIENTIFIC_QUALITY_EXAMPLES.json` — machine-readable guard examples;
- `docs/engineering-audit-report.pdf` — deterministic four-page engineering report target;
- `docs/VALIDATION_EVIDENCE.json` — scoped machine-readable validation evidence.

## Reproduction commands

```bash
python scripts/validate_schemas.py
python scripts/audit_repository.py
python scripts/validate_structure.py
python scripts/build_readme_facts.py --check
python scripts/build_validation_evidence.py --check
python scripts/build_test_dashboard.py --check
python scripts/build_research_quality_dashboard.py --check
python scripts/build_engineering_report.py --check
python scripts/generate_checksums.py --check
python -m pytest -q -p hypothesis.extra.pytestplugin
python scripts/performance_smoke.py
```

## Non-claims

This integration does not claim that an external experiment, literature search, DFT, MD, FEM, CFD, Aspen calculation, instrument run, legal analysis or safety decision occurred. Software validation is not scientific acceptance of project-specific conclusions.
