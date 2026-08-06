#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
MODE="${1:?mode required}"
APPLY_SCRIPT="${RUNNER_TEMP:-/tmp}/apply_v075.py"

assemble_apply() {
  cat .tsr-v075/apply.part000 .tsr-v075/apply.part001 \
      .tsr-v075/apply.part002 .tsr-v075/apply.part003 \
      .tsr-v075/apply.part004 .tsr-v075/apply.part005 \
      > "$APPLY_SCRIPT"
}

apply_candidate() {
  assemble_apply
  rm -f .github/workflows/v075-finalize-temp.yml
  rm -rf .tsr-v075
  python "$APPLY_SCRIPT"
  python -m pip install --disable-pip-version-check -e . --no-deps --force-reinstall
  python -m pip check
}

compatibility() {
  test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
  apply_candidate
  python -m compileall -q scripts tsao_researcher tests
  python -m pytest -q -p hypothesis.extra.pytestplugin
  python scripts/sync_version.py --check
  python scripts/sync_runtime_data.py --check
  python scripts/validate_schemas.py
  python scripts/validate_mathematical_contracts.py --check
  python scripts/build_readme_facts.py --check
  python -m ruff format --check scripts tsao_researcher tests
  python -m ruff check scripts tsao_researcher tests
  python -m tsao_researcher --version
  python -m tsao_researcher math --schema
  python -m tsao_researcher math \
    --contract decision-readiness \
    --language both \
    --output "${RUNNER_TEMP:-/tmp}/math-contract.json"
}

finalize() {
  test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
  test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = "$GITHUB_SHA"
  apply_candidate

  python scripts/sync_runtime_data.py --write
  python scripts/validate_mathematical_contracts.py --write-example
  python scripts/build_readme_facts.py --write
  python scripts/build_sbom.py --write
  python scripts/build_validation_evidence.py --write --preflight --evidence-date 2026-08-07
  python scripts/build_test_dashboard.py --write
  python scripts/build_research_quality_dashboard.py --write
  python scripts/build_engineering_report.py --write
  python scripts/generate_checksums.py --write
  python -m pip install --disable-pip-version-check -e . --no-deps --force-reinstall
  python -m pip check

  mkdir -p artifacts
  python -m compileall -q scripts tsao_researcher tests
  python scripts/sync_version.py --check
  python scripts/sync_runtime_data.py --check
  python scripts/validate_schemas.py
  python scripts/validate_mathematical_contracts.py --check
  python scripts/audit_repository.py
  python scripts/validate_structure.py
  python scripts/build_readme_facts.py --check
  python scripts/build_sbom.py --check
  python scripts/build_validation_evidence.py --check
  python scripts/build_test_dashboard.py --check
  python scripts/build_research_quality_dashboard.py --check
  python scripts/build_engineering_report.py --check
  python scripts/generate_checksums.py --check
  python scripts/build_capability_index.py --check
  python scripts/route_task.py --self-test
  python scripts/validate_figure.py examples/figure-contract.json
  python scripts/validate_computation_strategy.py examples/first-principles-strategy.json
  python -m tsao_researcher math --schema
  python -m tsao_researcher math \
    --contract uncertainty-budget \
    --language both \
    --output artifacts/math-contract.json
  mkdocs build --strict

  python -m pytest -q -p hypothesis.extra.pytestplugin --junitxml=artifacts/junit.xml
  python -m pytest -q -p hypothesis.extra.pytestplugin -p pytest_cov \
    --ignore=tests/test_import_isolation.py \
    --cov=tsao_researcher --cov-branch \
    --cov-report=term-missing \
    --cov-report=json:artifacts/coverage.json \
    --cov-report=xml:artifacts/coverage.xml
  python -m pytest -q -p hypothesis.extra.pytestplugin -p tests.reverse_order_plugin
  TSR_TEST_ORDER_SEED=20260807 \
    python -m pytest -q -p hypothesis.extra.pytestplugin -p tests.random_order_plugin
  python -m ruff format --check scripts tsao_researcher tests
  python -m ruff check scripts tsao_researcher tests
  python -m mypy scripts tsao_researcher
  python -m bandit -q -lll -r scripts tsao_researcher
  python -m pip list --format=freeze --exclude-editable | LC_ALL=C sort \
    > artifacts/resolved-environment.lock
  python -m pip_audit --strict \
    -r artifacts/resolved-environment.lock \
    --format cyclonedx-json \
    --output artifacts/resolved-environment-sbom.json
  python scripts/run_mutation_smoke.py --json-out artifacts/mutation-results.json
  python scripts/performance_smoke.py --json-out artifacts/performance.json
  python scripts/check_quality_baseline.py

  python scripts/package_release.py --out dist-a
  python scripts/package_release.py --out dist-b
  cmp "dist-a/TsaoSciResearcher-v$(cat VERSION).zip" \
      "dist-b/TsaoSciResearcher-v$(cat VERSION).zip"
  python scripts/validate_release.py
  python -m build --sdist --wheel --outdir dist-python
  python scripts/validate_distribution.py dist-python

  rm -rf \
    .coverage .coverage.* .hypothesis .mypy_cache .pytest_cache .ruff_cache \
    artifacts build dist dist-a dist-b dist-python site \
    ./*.egg-info tsao_researcher/*.egg-info artifacts-math-contract.json

  python - <<'PY'
from pathlib import Path
import subprocess

allowed = {
    ".github/workflows/ci.yml",
    ".github/workflows/v075-finalize-temp.yml",
    ".tsr-v075/apply.part000",
    ".tsr-v075/apply.part001",
    ".tsr-v075/apply.part002",
    ".tsr-v075/apply.part003",
    ".tsr-v075/apply.part004",
    ".tsr-v075/apply.part005",
    ".tsr-v075/run_candidate.sh",
    "VERSION",
    "pyproject.toml",
    "manifest.json",
    "SKILL.md",
    "agents/openai.yaml",
    "CITATION.cff",
    "CHANGELOG.md",
    "README.md",
    "README_EN.md",
    "README.zh-CN.md",
    "schemas/v2/mathematical-contract-registry.schema.json",
    "tsao_researcher/data/schemas/mathematical-contract-registry.schema.json",
    "scripts/sync_runtime_data.py",
    "scripts/validate_mathematical_contracts.py",
    "scripts/performance_smoke.py",
    "scripts/build_readme_facts.py",
    "tsao_researcher/__main__.py",
    "tsao_researcher/mathematical_contracts.py",
    "tests/test_mathematical_contracts.py",
    "examples/mathematical-contract.json",
    "docs/assets/ai/mathematical_contract_schema_pipeline.svg",
    "docs/MATHEMATICAL_CONTRACTS.md",
    "docs/CLI.md",
    "docs/VISUAL_ATLAS.md",
    "docs/VISUAL_ATLAS.zh-CN.md",
    "docs/index.md",
    "SHA256SUMS",
    "docs/README_FACTS.json",
    "docs/SBOM.cdx.json",
    "docs/SCIENTIFIC_QUALITY_EXAMPLES.json",
    "docs/VALIDATION_EVIDENCE.json",
    "docs/engineering-audit-report.pdf",
    "docs/research-quality-dashboard.html",
    "docs/research-quality-dashboard.svg",
    "docs/test-dashboard.html",
    "docs/test-dashboard.svg",
}
output = subprocess.check_output(["git", "status", "--porcelain=v1"], text=True)
actual = {
    line[3:].split(" -> ", 1)[-1].strip('"')
    for line in output.splitlines()
    if line
}
unexpected = sorted(actual - allowed)
if unexpected:
    raise SystemExit("unexpected changed paths: " + ", ".join(unexpected))
required = {
    ".github/workflows/v075-finalize-temp.yml",
    ".tsr-v075/apply.part000",
    ".tsr-v075/apply.part005",
    ".tsr-v075/run_candidate.sh",
    "VERSION",
    "schemas/v2/mathematical-contract-registry.schema.json",
    "tsao_researcher/data/schemas/mathematical-contract-registry.schema.json",
    "scripts/validate_mathematical_contracts.py",
    "examples/mathematical-contract.json",
    "docs/assets/ai/mathematical_contract_schema_pipeline.svg",
    "SHA256SUMS",
}
missing = sorted(required - actual)
if missing:
    raise SystemExit("required final changes missing: " + ", ".join(missing))
for path in (Path(".github/workflows/v075-finalize-temp.yml"), Path(".tsr-v075")):
    if path.exists():
        raise SystemExit(f"temporary orchestration path remains: {path}")
print(f"exact v0.7.5 final scope PASS ({len(actual)} paths)")
PY

  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git add --all
  git commit -m "feat: finalize v0.7.5 schema-backed mathematical delivery"
  git fetch origin main
  test "$(git rev-parse origin/main)" = "$GITHUB_SHA"
  git push origin HEAD:main
  echo "FINAL_COMMIT=$(git rev-parse HEAD)"
}

case "$MODE" in
  compatibility) compatibility ;;
  finalize) finalize ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
