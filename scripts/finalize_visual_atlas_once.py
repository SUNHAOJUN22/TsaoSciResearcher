#!/usr/bin/env python3
"""One-shot, self-cleaning README visual-atlas finalizer for main."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs/assets/ai"
ARCHIVE = ASSET_DIR / "visual-atlas.zip"
EN_SECTION = ASSET_DIR / "visual-section-en.md"
ZH_SECTION = ASSET_DIR / "visual-section-zh.md"
EXPECTED = {
    ARCHIVE: "3442234d59c78fd38cefe0413bb36c07d116f1e76643f2a2ad1c4de1d60c8070",
    EN_SECTION: "a396c5e138c7d7b719b9901286ce50d4a8ee677a92f85ce6b436ee562805ee05",
    ZH_SECTION: "a00bc33255c7bef94cc537c8cb0b9c40609fe8c75bab5cdc731a372782fa3acf",
}
EXPECTED_NAMES = {
    "capability_landscape.svg",
    "computation_handoff_boundary.svg",
    "evidence_claim_graph.svg",
    "multi_agent_orchestration.svg",
    "multiscale_science_pipeline.svg",
    "project_state_machine.svg",
    "reproducibility_quality_gates.svg",
    "research_os_architecture.svg",
}


def run(*args: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def output(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def verify_and_extract() -> None:
    for path, expected_sha in EXPECTED.items():
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise SystemExit(f"staged payload checksum mismatch for {path}: {actual_sha}")
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = {info.filename for info in archive.infolist() if not info.is_dir()}
        if names != EXPECTED_NAMES:
            raise SystemExit(f"visual inventory mismatch: {sorted(names)}")
        for name in sorted(names):
            pure = PurePosixPath(name)
            if pure.is_absolute() or len(pure.parts) != 1 or pure.suffix != ".svg":
                raise SystemExit(f"unsafe visual path: {name}")
            data = archive.read(name)
            text = data.decode("utf-8", errors="strict")
            if "<svg" not in text or "<title" not in text or "<desc" not in text:
                raise SystemExit(f"invalid accessible SVG: {name}")
            (ASSET_DIR / name).write_bytes(data)


def upsert(readme: Path, section: str, anchor: str) -> None:
    start = "<!-- TSR-AI-VISUALS:START -->"
    end = "<!-- TSR-AI-VISUALS:END -->"
    text = readme.read_text(encoding="utf-8", errors="strict")
    block = f"{start}\n{section.rstrip()}\n{end}"
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise SystemExit(f"broken visual markers in {readme}")
        before, tail = text.split(start, 1)
        _, after = tail.split(end, 1)
        text = before.rstrip() + "\n\n" + block + after
    else:
        if anchor not in text:
            raise SystemExit(f"README anchor missing in {readme}: {anchor}")
        text = text.replace(anchor, block + "\n\n" + anchor, 1)
    lines = [
        "python -m pip_audit --strict -r requirements-ci.lock"
        if line.strip() == "python -m pip_audit --strict"
        else line
        for line in text.splitlines()
    ]
    readme.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def patch_stable_workflows() -> None:
    workflows = ROOT / ".github/workflows"
    freeze_old = "python -m pip freeze --all | LC_ALL=C sort > artifacts/resolved-environment.lock"
    freeze_new = (
        "python -m pip list --format=freeze --exclude-editable | LC_ALL=C sort "
        "> artifacts/resolved-environment.lock"
    )
    audit_line = (
        "python -m pip_audit --strict -r artifacts/resolved-environment.lock "
        "--format cyclonedx-json --output artifacts/resolved-environment-sbom.json"
    )
    for name in ("ci.yml", "audit.yml", "nightly.yml", "release.yml"):
        path = workflows / name
        text = path.read_text(encoding="utf-8", errors="strict")
        text = text.replace(freeze_old, freeze_new)
        text = re.sub(
            r"(?m)^(\s*)python -m pip_audit --strict[^\n]*resolved-environment-sbom\.json\s*$",
            lambda match: match.group(1) + audit_line,
            text,
        )
        path.write_text(text, encoding="utf-8", newline="\n")


def clean_one_shot_controls() -> None:
    workflows = ROOT / ".github/workflows"
    for path in (ARCHIVE, EN_SECTION, ZH_SECTION, ROOT / ".github/visual-atlas.trigger"):
        path.unlink(missing_ok=True)
    for pattern in ("*visual*.yml", "*diagnose*.yml"):
        for path in workflows.glob(pattern):
            path.unlink(missing_ok=True)
    for pattern in ("*.trigger", "*status*.json", "*transport*.json"):
        for path in (ROOT / ".github").glob(pattern):
            path.unlink(missing_ok=True)
    Path(__file__).unlink(missing_ok=True)


def normalize_and_generate() -> None:
    run(sys.executable, "-m", "ruff", "format", "scripts", "tsao_researcher", "tests")
    run(sys.executable, "-m", "ruff", "check", "--fix", "scripts", "tsao_researcher", "tests")
    for script, option in (
        ("scripts/sync_version.py", "--write"),
        ("scripts/build_readme_facts.py", "--write"),
        ("scripts/build_sbom.py", "--write"),
    ):
        run(sys.executable, script, option)
    run(
        sys.executable,
        "scripts/build_validation_evidence.py",
        "--write",
        "--preflight",
        "--evidence-date",
        output("date", "-u", "+%F"),
    )
    for script in (
        "scripts/build_test_dashboard.py",
        "scripts/build_research_quality_dashboard.py",
        "scripts/build_engineering_report.py",
        "scripts/generate_checksums.py",
    ):
        run(sys.executable, script, "--write")


def validate_repository() -> None:
    run(sys.executable, "-m", "compileall", "-q", "scripts", "tsao_researcher", "tests")
    checks = [
        ("scripts/sync_version.py", "--check"),
        ("scripts/validate_schemas.py",),
        ("scripts/audit_repository.py",),
        ("scripts/validate_structure.py",),
        ("scripts/build_readme_facts.py", "--check"),
        ("scripts/build_sbom.py", "--check"),
        ("scripts/build_validation_evidence.py", "--check"),
        ("scripts/build_test_dashboard.py", "--check"),
        ("scripts/build_research_quality_dashboard.py", "--check"),
        ("scripts/build_engineering_report.py", "--check"),
        ("scripts/generate_checksums.py", "--check"),
        ("scripts/build_capability_index.py", "--check"),
        ("scripts/route_task.py", "--self-test"),
        ("scripts/validate_figure.py", "examples/figure-contract.json"),
    ]
    for command in checks:
        run(sys.executable, *command)
    run("mkdocs", "build", "--strict")


def run_quality_gates() -> None:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    plugin = "hypothesis.extra.pytestplugin"
    run(sys.executable, "-m", "pytest", "-q", "-p", plugin, "--junitxml=artifacts/junit.xml")
    run(
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        plugin,
        "-p",
        "pytest_cov",
        "--ignore=tests/test_import_isolation.py",
        "--cov=tsao_researcher",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-report=json:artifacts/coverage.json",
        "--cov-report=xml:artifacts/coverage.xml",
    )
    run(sys.executable, "-m", "pytest", "-q", "-p", plugin, "-p", "tests.reverse_order_plugin")
    env = dict(os.environ)
    env["TSR_TEST_ORDER_SEED"] = "20260727"
    run(sys.executable, "-m", "pytest", "-q", "-p", plugin, "-p", "tests.random_order_plugin", env=env)
    run(sys.executable, "-m", "ruff", "format", "--check", "scripts", "tsao_researcher", "tests")
    run(sys.executable, "-m", "ruff", "check", "scripts", "tsao_researcher", "tests")
    run(sys.executable, "-m", "mypy", "scripts", "tsao_researcher")
    run(sys.executable, "-m", "bandit", "-q", "-lll", "-r", "scripts", "tsao_researcher")
    resolved = subprocess.check_output(
        [sys.executable, "-m", "pip", "list", "--format=freeze", "--exclude-editable"],
        cwd=ROOT,
        text=True,
    )
    lock = artifacts / "resolved-environment.lock"
    lock.write_text("\n".join(sorted(line for line in resolved.splitlines() if line)) + "\n", encoding="utf-8")
    run(
        sys.executable,
        "-m",
        "pip_audit",
        "--strict",
        "-r",
        str(lock.relative_to(ROOT)),
        "--format",
        "cyclonedx-json",
        "--output",
        "artifacts/resolved-environment-sbom.json",
    )
    run(sys.executable, "scripts/run_mutation_smoke.py", "--json-out", "artifacts/mutation-results.json")
    run(sys.executable, "scripts/performance_smoke.py", "--json-out", "artifacts/performance.json")
    run(sys.executable, "scripts/check_quality_baseline.py")
    run(
        sys.executable,
        "scripts/record_quality_history.py",
        "--source-commit",
        os.environ["GITHUB_SHA"],
        "--workflow-run-id",
        os.environ["GITHUB_RUN_ID"],
        "--workflow-attempt",
        os.environ["GITHUB_RUN_ATTEMPT"],
        "--evidence-date",
        output("date", "-u", "+%F"),
    )


def release_gates() -> None:
    run(sys.executable, "scripts/package_release.py", "--out", "dist-a")
    run(sys.executable, "scripts/package_release.py", "--out", "dist-b")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    run("cmp", f"dist-a/TsaoSciResearcher-v{version}.zip", f"dist-b/TsaoSciResearcher-v{version}.zip")
    run(sys.executable, "scripts/validate_release.py")
    run(sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist-python")
    run(sys.executable, "scripts/validate_distribution.py", "dist-python")


def create_candidate() -> str:
    for path in ("site", "build", "htmlcov", ".coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache"):
        candidate = ROOT / path
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink(missing_ok=True)
    for path in ROOT.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "-A")
    run("git", "diff", "--cached", "--check")
    run("git", "commit", "-m", "docs: publish ultimate AI scientific visual atlas")
    sha = output("git", "rev-parse", "HEAD")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as stream:
            stream.write(f"sha={sha}\n")
    return sha


def main() -> None:
    verify_and_extract()
    en = EN_SECTION.read_text(encoding="utf-8", errors="strict")
    zh = ZH_SECTION.read_text(encoding="utf-8", errors="strict")
    upsert(ROOT / "README.md", en, "## Native, delegated and human-approved boundaries")
    upsert(ROOT / "README_EN.md", en, "## Native, delegated and human-approved boundaries")
    upsert(ROOT / "README.zh-CN.md", zh, "## 能力边界")
    (ROOT / "README_CN.md").write_text(
        "# 中文 README\n\n本文件是兼容入口。完整中文说明请阅读 "
        "[README.zh-CN.md](README.zh-CN.md)。\n",
        encoding="utf-8",
        newline="\n",
    )
    patch_stable_workflows()
    clean_one_shot_controls()
    normalize_and_generate()
    validate_repository()
    run_quality_gates()
    release_gates()
    sha = create_candidate()
    run(
        sys.executable,
        "scripts/build_validation_evidence.py",
        "--write",
        "--attested",
        "--out",
        "artifacts/VALIDATION_EVIDENCE.json",
        "--source-commit",
        sha,
        "--publication-parent",
        sha,
        "--run-id",
        os.environ["GITHUB_RUN_ID"],
        "--run-attempt",
        os.environ["GITHUB_RUN_ATTEMPT"],
        "--evidence-date",
        output("date", "-u", "+%F"),
    )
    run(
        sys.executable,
        "scripts/build_publication_attestation.py",
        "--commit",
        sha,
        "--run-id",
        os.environ["GITHUB_RUN_ID"],
        "--run-attempt",
        os.environ["GITHUB_RUN_ATTEMPT"],
    )
    print(json.dumps({"candidate": sha, "status": "PASS"}, sort_keys=True))


if __name__ == "__main__":
    main()
