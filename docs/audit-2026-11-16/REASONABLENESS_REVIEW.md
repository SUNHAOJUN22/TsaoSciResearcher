# Scientific logic review — 2026-11-16

## Scope and baseline

Baseline: `94275c30b691a40baac319c3ed663b8b807ec138` on `main`.
This review follows the earlier path/receipt audit and concentrates on whether
the research decision logic reasonably interprets its declared inputs.

Assessed paths include `strategy.py` (evidence maturity, extrapolation,
identifiability and readiness aggregation), `scientific_quality.py`,
`evidence_resolution.py`, the claim/evidence validators, `state.py`,
`capabilities.py` and `discovery.py`. The review traced the distinction between
declared evidence, verified artifact identity, and scientific acceptance.
Catalog caches use bounded byte snapshots; discovery explicitly does not claim
full catalog or scientific verification. Positive traceability requires
reciprocal links, current bytes and receipt-output bindings, and known refuting
links cannot be selectively omitted. No new repair was justified for those
assessed paths.

## Reproduced defects and repair

| Severity | Reproduced behavior | Consequence and repair |
| --- | --- | --- |
| P1 | `no transfer validation`, `Transfer validation has not been performed.`, and future validation plans were counted as available transfer evidence. | An explicit extrapolation blocker became only a review item. Filter available-evidence markers by local affirmation, absence and planning scope. |
| P1 | Absent or planned experiments raised declared evidence maturity to E3. | The evidence-baseline and claim-evidence blockers could disappear even though the supplied statement denied the work. Apply the same bounded declaration filter to maturity classification. |
| P2 | The short spectroscopy marker `pea` matched inside `repeated` and `appears`. | A simulation or literature statement could be upgraded to experimental evidence. Require Latin word boundaries while preserving Chinese phrase matching. |

The implementation is confined to the two existing free-text evidence entry
points. It preserves the original evidence statements and their
`declared-unverified` status. It does not authenticate a measurement, establish
a claim, execute a solver, or automatically approve a decision.

Clause boundaries preserve an affirmative statement after a separate denial.
`not yet` is treated as one negative status expression rather than the generic
contrast word `yet`; present-perfect negatives and explicit future execution are
also excluded. Completed declarations remain eligible for human review.

The final 48 new public-API regression cases were replayed against the exact
baseline `strategy.py` in an isolated Python module, without replacing checkout
files: **34 failed and 14 passed**. The repaired code passes all 48, and the
broader strategy slice passes **87 tests**. Cases include English and Chinese,
prefix/suffix negation, planned and future work, mixed affirmative/negative
clauses, short-token collisions, and preservation of the declared-only boundary.
Independent review added eight failing negative controls before the final fix.
Five additional positive controls preserve common plural evidence nouns after
introducing word boundaries; two negative plural controls remain blocked.

## Validation

Environment: Linux, Python 3.12.14, the repository's unchanged
`requirements-ci.lock`, and imports from this checkout.

| Gate | Observed result |
| --- | --- |
| Complete regression | 1,017 passed, plus 3 subtests |
| Reverse and seeded-random order (`20260806`) | 1,017 passed, plus 3 subtests, in each order |
| Coverage suite with the CI import-isolation exclusion | 1,009 passed, plus 3 subtests; statements 95.95%, branches 93.43%, combined 95.24% |
| Quality baseline | Passed, including the separate 95% combined coverage floor |
| Critical mutation smoke | 24/24 killed |
| Bounded performance smoke | Passed |
| Locked dependency installation and `pip check` | Passed |
| Resolved-environment vulnerability audit | 66 packages; no known vulnerabilities reported |
| Ruff format / lint, strict mypy, Bandit | Passed; 148 Python files formatted and 68 source files type-checked |
| Unicode, repository/structure, schema, mathematical/figure/strategy contracts | Passed |
| Runtime/version/catalog, deterministic SBOM, README facts and final preflight | Passed |
| Strict MkDocs build and acceptance-controller tests | Passed |
| Byte-identical source release archives and release validator | Passed |
| Wheel/sdist build and isolated distribution installation | Passed |

Tracked facts, preflight evidence, dashboards, the engineering report and tree
checksums are regenerated from the staged inventory. A second generation must
leave the tracked tree unchanged. The checked-in evidence remains explicitly
PARTIAL; it is not relabelled as a completed GitHub Actions attestation.

The existing deliberate multithreaded fork test emits one Python deprecation
warning. It remains visible and is not counted as a failure.

## Reproduction

```bash
python -m pip install -r requirements-ci.lock
python -m pip check
python -m pytest -p hypothesis.extra.pytestplugin tests/test_evidence_declaration_scope.py
python -m pytest -p hypothesis.extra.pytestplugin --junitxml=artifacts/junit.xml
python -m pytest -p hypothesis.extra.pytestplugin -p pytest_cov \
  --ignore=tests/test_import_isolation.py --cov=tsao_researcher --cov-branch \
  --cov-report=json:artifacts/coverage.json
python -m pytest -p hypothesis.extra.pytestplugin -p tests.reverse_order_plugin
TSR_TEST_ORDER_SEED=20260806 python -m pytest \
  -p hypothesis.extra.pytestplugin -p tests.random_order_plugin
python scripts/run_mutation_smoke.py --json-out artifacts/mutation-results.json
python scripts/performance_smoke.py --json-out artifacts/performance.json
python scripts/check_quality_baseline.py
```

The CI workflow records the remaining ordered schema, static, build,
distribution, dependency and attestation commands. New tests and this report
are staged before regenerating tracked facts and source-tree evidence.

## Limits

This remains a deterministic lexical screen for explicit declarations, not a
general natural-language truth classifier. Unusual or ambiguous wording can
require qualified review; all evidence declarations remain unverified. The
change does not infer the relevance, independence, quality, or authenticity of
a source from its wording. The local matrix is Linux/Python 3.12; the exact
published commit's GitHub workflows supply the additional platform and Python
checks. No external scientific calculation or experiment was run.
