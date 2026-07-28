#!/usr/bin/env python3
"""Verify and publish a first-principles strategy-advisor Git object candidate."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path.cwd().resolve()
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GH_TOKEN"]
ISSUE_NUMBER = int(os.environ["ISSUE_NUMBER"])
PYTHON = sys.executable


def run(args: list[str], *, env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, env=merged, check=True)


def github_api(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}{path}",
        data=json.dumps(payload).encode("utf-8"),
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise RuntimeError(f"unexpected GitHub response for {path}")
    return value


def remove_transport() -> None:
    paths = [
        ".github/first-principles-advisor-plan.md",
        ".github/first-principles-development-session.txt",
        ".github/transport/finalize_first_principles_advisor.py",
        ".github/workflows/export-first-principles-source.yml",
        ".github/workflows/finalize-first-principles-advisor.yml",
        ".github/workflows/finalize-first-principles-advisor-v2.yml",
        ".github/workflows/patch-first-principles-finalizer.yml",
        "dist-b/TsaoSciResearcher-v0.5.3.zip.sha256",
    ]
    for relative in paths:
        (ROOT / relative).unlink(missing_ok=True)
    for part in (ROOT / ".github").glob("first-principles-payload.part-*"):
        part.unlink(missing_ok=True)


def add_capability() -> None:
    path = ROOT / "capabilities/v2/capabilities.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    record = {
        "category": "vNext核心能力",
        "computation_handoff": {"mode": "optional", "profile": "first-principles-strategy"},
        "data_egress": "none",
        "description": "从可观测量、自由度、守恒律、量子与统计物理、尺度分离和证伪要求出发，提出最低充分的计算或仿真策略，不执行求解器。",
        "domains": [
            "general",
            "computational-chemistry-materials",
            "molecular-dynamics-multiscale",
            "catalysis-polymers-composites",
            "fem-multiphysics",
            "cfd-particles-processing",
            "process-kinetics-digital-twin",
        ],
        "failure_modes": [
            "observable undefined",
            "scale ambiguity",
            "method chosen without governing-physics rationale",
            "validation absent",
        ],
        "human_approval": {
            "points": ["qualified method review before external execution"],
            "required": False,
        },
        "id": "TSR-A019",
        "implementation_level": "native-research",
        "input_schema": "schemas/v2/capability-invocation.schema.json",
        "maturity": "beta",
        "name_en": "First-Principles Computation Strategy Advisor",
        "name_zh": "第一性原理计算与仿真策略顾问",
        "negative_triggers": ["声称已完成计算", "伪造仿真结果"],
        "output_schema": "schemas/v2/artifact.schema.json",
        "positive_triggers": [
            "第一性原理计算策略",
            "仿真策略",
            "计算方案",
            "method selection",
            "first-principles strategy",
            "statistical mechanics",
            "quantum mechanics",
        ],
        "recovery": [
            "return unresolved first-principles questions",
            "start from analytical bounds",
            "request validation observables",
            "remain in planned state",
        ],
        "references": [
            "references/computation/first-principles-strategy.md",
            "references/computation/handoff-protocol.md",
            "references/project-governance/scientific-validation.md",
        ],
        "schema_version": "2.0",
        "slug": "first-principles-strategy-advisor",
        "source_lineage": [{"feature": "first-principles-strategy-advisor", "source": "vNext-original"}],
        "validators": ["strategy", "schema", "state", "provenance", "truth-boundary"],
        "workflow": "computation-handoff",
    }
    rows = [row for row in rows if row.get("id") != "TSR-A019" and row.get("slug") != record["slug"]]
    rows.append(record)
    rows.sort(key=lambda row: row["id"])
    path.write_text(
        json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(
        ROOT / "templates/computation-handoff/first-principles-strategy.json",
        ROOT / "examples/first-principles-strategy.json",
    )


def regenerate() -> None:
    run([PYTHON, "scripts/sync_version.py", "--write"])
    shutil.copyfile(ROOT / "README.zh-CN.md", ROOT / "README_CN.md")
    shutil.copyfile(ROOT / "README.md", ROOT / "README_EN.md")
    for command in [
        [PYTHON, "scripts/build_readme_facts.py", "--write"],
        [PYTHON, "scripts/build_sbom.py", "--write"],
        [
            PYTHON,
            "scripts/build_validation_evidence.py",
            "--write",
            "--preflight",
            "--evidence-date",
            "2026-07-28",
        ],
        [PYTHON, "scripts/build_test_dashboard.py", "--write"],
        [PYTHON, "scripts/build_research_quality_dashboard.py", "--write"],
        [PYTHON, "scripts/build_engineering_report.py", "--write"],
        [PYTHON, "scripts/generate_checksums.py", "--write"],
    ]:
        run(command)


def validate_feature() -> None:
    run([PYTHON, "scripts/validate_computation_strategy.py", "examples/first-principles-strategy.json"])
    from tsao_researcher.strategy import advise_computation_strategy

    index = json.loads((ROOT / "capabilities/v2/index.json").read_text(encoding="utf-8"))
    assert index["total"] == 341
    assert index["core_added"] == 19
    assert index["by_workflow"]["computation-handoff"] == 169
    assert len(list((ROOT / "schemas").rglob("*.schema.json"))) == 19
    assert len(list((ROOT / "scripts").glob("*.py"))) == 39
    svgs = list((ROOT / "docs/assets/ai").glob("*.svg"))
    assert len(svgs) == 17
    for svg in svgs:
        ET.parse(svg)
        text = svg.read_text(encoding="utf-8")
        assert 'role="img"' in text and "<title" in text and "<desc" in text
    continuum = advise_computation_strategy(
        "Which simulation strategy should predict pressure drop and mixing in a non-Newtonian channel?",
        observables=["pressure drop", "mixing time"],
    )
    assert continuum["method_candidates"][0]["slug"] == "continuum-conservation-model"
    assert all(row["slug"] != "periodic-dft" for row in continuum["method_candidates"])
    assert continuum["external_execution_boundary"]["execution_performed"] is False


def validate_all() -> None:
    commands = [
        [PYTHON, "-m", "compileall", "-q", "scripts", "tsao_researcher", "tests"],
        [PYTHON, "scripts/sync_version.py", "--check"],
        [PYTHON, "scripts/validate_schemas.py"],
        [PYTHON, "scripts/audit_repository.py"],
        [PYTHON, "scripts/validate_structure.py"],
        [PYTHON, "scripts/build_readme_facts.py", "--check"],
        [PYTHON, "scripts/build_sbom.py", "--check"],
        [PYTHON, "scripts/build_validation_evidence.py", "--check"],
        [PYTHON, "scripts/build_test_dashboard.py", "--check"],
        [PYTHON, "scripts/build_research_quality_dashboard.py", "--check"],
        [PYTHON, "scripts/build_engineering_report.py", "--check"],
        [PYTHON, "scripts/generate_checksums.py", "--check"],
        [PYTHON, "scripts/build_capability_index.py", "--check"],
        [PYTHON, "scripts/route_task.py", "--self-test"],
        [PYTHON, "scripts/validate_figure.py", "examples/figure-contract.json"],
        ["mkdocs", "build", "--strict"],
    ]
    for command in commands:
        run(command)


def test_all() -> None:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    common = [PYTHON, "-m", "pytest", "-q", "-p", "hypothesis.extra.pytestplugin"]
    run(common + ["--junitxml=artifacts/junit.xml"])
    run(
        common
        + [
            "-p",
            "pytest_cov",
            "--ignore=tests/test_import_isolation.py",
            "--cov=tsao_researcher",
            "--cov-branch",
            "--cov-report=term-missing",
            "--cov-report=json:artifacts/coverage.json",
            "--cov-report=xml:artifacts/coverage.xml",
        ]
    )
    run(common + ["-p", "tests.reverse_order_plugin"])
    run(common + ["-p", "tests.random_order_plugin"], env={"TSR_TEST_ORDER_SEED": "20260728"})


def static_security_quality() -> None:
    for command in [
        [PYTHON, "-m", "ruff", "format", "--check", "scripts", "tsao_researcher", "tests"],
        [PYTHON, "-m", "ruff", "check", "scripts", "tsao_researcher", "tests"],
        [PYTHON, "-m", "mypy", "scripts", "tsao_researcher"],
        [PYTHON, "-m", "bandit", "-q", "-lll", "-r", "scripts", "tsao_researcher"],
    ]:
        run(command)
    resolved = subprocess.check_output(
        [PYTHON, "-m", "pip", "list", "--format=freeze", "--exclude-editable"],
        cwd=ROOT,
        text=True,
    )
    (ROOT / "artifacts/resolved-environment.lock").write_text(
        "\n".join(sorted(line for line in resolved.splitlines() if line)) + "\n",
        encoding="utf-8",
    )
    run(
        [
            PYTHON,
            "-m",
            "pip_audit",
            "--strict",
            "-r",
            "artifacts/resolved-environment.lock",
            "--format",
            "cyclonedx-json",
            "--output",
            "artifacts/resolved-environment-sbom.json",
        ]
    )
    for command in [
        [PYTHON, "scripts/build_sbom.py", "--check"],
        [PYTHON, "scripts/run_mutation_smoke.py", "--json-out", "artifacts/mutation-results.json"],
        [PYTHON, "scripts/performance_smoke.py", "--json-out", "artifacts/performance.json"],
        [PYTHON, "scripts/check_quality_baseline.py"],
    ]:
        run(command)


def release_gates() -> None:
    for directory in ("dist-a", "dist-b", "dist-python"):
        shutil.rmtree(ROOT / directory, ignore_errors=True)
    run([PYTHON, "scripts/package_release.py", "--out", "dist-a"])
    run([PYTHON, "scripts/package_release.py", "--out", "dist-b"])
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    first = ROOT / f"dist-a/TsaoSciResearcher-v{version}.zip"
    second = ROOT / f"dist-b/TsaoSciResearcher-v{version}.zip"
    if first.read_bytes() != second.read_bytes():
        raise RuntimeError("deterministic source releases differ")
    run([PYTHON, "scripts/validate_release.py"])
    run([PYTHON, "-m", "build", "--sdist", "--wheel", "--outdir", "dist-python"])
    run([PYTHON, "scripts/validate_distribution.py", "dist-python"])


def clean_runtime() -> dict[str, Any]:
    quality = json.loads((ROOT / "artifacts/quality-current.json").read_text(encoding="utf-8"))
    for relative in [
        "site",
        "build",
        "htmlcov",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".hypothesis",
        "artifacts",
        "dist",
        "dist-a",
        "dist-b",
        "dist-python",
    ]:
        path = ROOT / relative
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    (ROOT / ".coverage").unlink(missing_ok=True)
    for cache in ROOT.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache)
    return quality


def create_candidate(quality: dict[str, Any]) -> str:
    run(["git", "add", "-A"])
    run(["git", "diff", "--cached", "--check"])
    parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    parent_tree = subprocess.check_output(
        ["git", "show", "-s", "--format=%T", "HEAD"], cwd=ROOT, text=True
    ).strip()
    changed = sorted(
        filter(
            None,
            subprocess.check_output(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"],
                cwd=ROOT,
                text=True,
            ).splitlines(),
        )
    )
    deleted = sorted(
        filter(
            None,
            subprocess.check_output(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=D"],
                cwd=ROOT,
                text=True,
            ).splitlines(),
        )
    )
    required = {
        "tsao_researcher/strategy.py",
        "schemas/v2/computation-strategy.schema.json",
        "scripts/advise_computation_strategy.py",
        "scripts/validate_computation_strategy.py",
        "tests/test_first_principles_strategy.py",
        "docs/FIRST_PRINCIPLES_STRATEGY.md",
        "docs/assets/ai/first_principles_strategy_ladder.svg",
    }
    missing = required - set(changed)
    if missing:
        raise RuntimeError(f"required feature files missing: {sorted(missing)}")
    forbidden = [
        path
        for path in changed
        if "first-principles-payload" in path
        or path.startswith(".github/transport/")
        or "first-principles-advisor" in path and path.startswith(".github/workflows/")
    ]
    if forbidden:
        raise RuntimeError(f"temporary controls remain: {forbidden}")
    tree: list[dict[str, Any]] = []
    for relative in changed:
        path = ROOT / relative
        raw = path.read_bytes()
        blob = github_api(
            "POST",
            "/git/blobs",
            {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"},
        )
        mode_row = subprocess.run(
            ["git", "ls-files", "-s", "--", relative],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        mode = mode_row.split()[0] if mode_row else (
            "100755" if relative.startswith("scripts/") and raw.startswith(b"#!") else "100644"
        )
        tree.append({"path": relative, "mode": mode, "type": "blob", "sha": blob["sha"]})
    for relative in deleted:
        tree.append({"path": relative, "mode": "100644", "type": "blob", "sha": None})
    created_tree = github_api("POST", "/git/trees", {"base_tree": parent_tree, "tree": tree})
    commit = github_api(
        "POST",
        "/git/commits",
        {
            "message": "feat: add first-principles strategy advisor",
            "tree": created_tree["sha"],
            "parents": [parent],
        },
    )
    body = (
        f"status=first-principles-candidate-ready; candidate={commit['sha']}; parent={parent}; "
        "version=0.7.0; capability-contracts=341; runtime-core=19; schemas=19; scripts=39; "
        f"visual-atlas=17; tests={quality['tests']['tests']}; "
        f"line-coverage={quality['coverage']['line_percent']}; "
        f"branch-coverage={quality['coverage']['branch_percent']}; "
        f"mutation={quality['mutation']['killed']}/{quality['mutation']['total']}; "
        "strategy-schema=PASS; route=PASS; docs=PASS; ruff=PASS; mypy=PASS; bandit=PASS; "
        "dependency-audit=PASS; performance=PASS; deterministic-release=PASS; "
        "wheel-and-sdist=PASS; execution-boundary=PRESERVED; temporary-controls=REMOVED"
    )
    github_api("PATCH", f"/issues/{ISSUE_NUMBER}", {"body": body})
    return str(commit["sha"])


def main() -> None:
    remove_transport()
    add_capability()
    regenerate()
    validate_feature()
    validate_all()
    test_all()
    static_security_quality()
    release_gates()
    quality = clean_runtime()
    candidate = create_candidate(quality)
    print(f"verified candidate: {candidate}")


if __name__ == "__main__":
    main()
