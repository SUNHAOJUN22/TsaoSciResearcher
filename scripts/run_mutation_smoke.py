#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_COPY_NAMES = {
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tsao-research",
    "__pycache__",
    "build",
    "dist",
}


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    before: str
    after: str
    tests: tuple[str, ...]


MUTATIONS = (
    Mutation(
        "zip-slip-parent-segment",
        "scripts/archive_safety.py",
        'part in {"", ".", ".."}',
        'part in {"", "."}',
        ("tests/test_archive_safety.py",),
    ),
    Mutation(
        "zip-total-expanded-size",
        "scripts/archive_safety.py",
        "if total > max_total_bytes:",
        "if False and total > max_total_bytes:",
        ("tests/test_archive_safety.py",),
    ),
    Mutation(
        "zip-compression-ratio",
        "scripts/archive_safety.py",
        "if info.compress_size and info.file_size / info.compress_size > max_compression_ratio:",
        "if False and info.compress_size and info.file_size / info.compress_size > max_compression_ratio:",
        ("tests/test_archive_safety.py",),
    ),
    Mutation(
        "capability-shard-path-boundary",
        "scripts/capability_io.py",
        "if not path.is_relative_to(root):",
        "if False and not path.is_relative_to(root):",
        ("tests/test_capability_io.py",),
    ),
    Mutation(
        "atomic-replace-bypass",
        "scripts/common.py",
        "os.replace(temporary, target)",
        'target.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8")',
        ("tests/test_common.py",),
    ),
    Mutation(
        "json-nan-writer",
        "scripts/common.py",
        "json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)",
        "json.dumps(data, ensure_ascii=False, indent=2, allow_nan=True)",
        ("tests/test_common.py",),
    ),
    Mutation(
        "evidence-support-refute-overlap",
        "scripts/validate_evidence.py",
        "if overlap:",
        "if False and overlap:",
        ("tests/test_claims.py",),
    ),
    Mutation(
        "claim-reverse-link",
        "scripts/validate_claims.py",
        "if claim_id not in linked:",
        "if False and claim_id not in linked:",
        ("tests/test_claims.py",),
    ),
    Mutation(
        "project-time-monotonicity",
        "scripts/validate_project.py",
        "if updated < created:",
        "if False and updated < created:",
        ("tests/test_project_state.py",),
    ),
    Mutation(
        "project-accepted-approval",
        "scripts/validate_project.py",
        'if data["status"] == "accepted" and not data.get("approvals"):',
        'if False and data["status"] == "accepted" and not data.get("approvals"):',
        ("tests/test_project_state.py",),
    ),
    Mutation(
        "project-idempotent-transition",
        "scripts/validate_project.py",
        "if previous == current:\n        return True",
        "if False and previous == current:\n        return True",
        ("tests/test_project_state.py",),
    ),
    Mutation(
        "router-word-boundary",
        "scripts/route_task.py",
        "return re.search(pattern, haystack) is not None",
        "return keyword in haystack",
        ("tests/test_router.py",),
    ),
    Mutation(
        "router-keyword-deduplication",
        "scripts/route_task.py",
        "if not keyword or keyword in seen:",
        "if not keyword:",
        ("tests/test_router.py",),
    ),
    Mutation(
        "router-stable-tie-break",
        "scripts/route_task.py",
        "key=lambda item: (-item[1], item[3])",
        "key=lambda item: (-item[1], -item[3])",
        ("tests/test_router.py",),
    ),
    Mutation(
        "release-sidecar-digest",
        "scripts/package_release.py",
        "if actual != expected:",
        "if False and actual != expected:",
        ("tests/test_release.py",),
    ),
)


def _copy_repository(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(*sorted(IGNORED_COPY_NAMES)),
    )


def _run_tests(
    work: Path, tests: tuple[str, ...], environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *tests],
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
        shell=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run critical mutation smoke tests with baseline validation."
    )
    parser.add_argument("--json-out")
    args = parser.parse_args()

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    results: list[dict[str, object]] = []
    baseline_cache: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {}

    with tempfile.TemporaryDirectory(prefix="tsr-mutation-") as temporary:
        base = Path(temporary)
        baseline = base / "baseline"
        _copy_repository(baseline)

        for mutation in MUTATIONS:
            baseline_result = baseline_cache.get(mutation.tests)
            if baseline_result is None:
                baseline_result = _run_tests(baseline, mutation.tests, environment)
                baseline_cache[mutation.tests] = baseline_result
            if baseline_result.returncode != 0:
                print(baseline_result.stdout)
                print(baseline_result.stderr, file=sys.stderr)
                raise SystemExit(f"baseline tests fail before mutation: {mutation.name}")

        for index, mutation in enumerate(MUTATIONS):
            work = base / f"mutation-{index:02d}"
            _copy_repository(work)
            target = work / mutation.path
            source = target.read_text(encoding="utf-8", errors="strict")
            if source.count(mutation.before) != 1:
                raise SystemExit(f"mutation anchor is not unique: {mutation.name}")
            target.write_text(source.replace(mutation.before, mutation.after, 1), encoding="utf-8")
            result = _run_tests(work, mutation.tests, environment)
            killed = result.returncode != 0
            evidence = (result.stdout + "\n" + result.stderr).strip()[-2000:]
            results.append(
                {
                    "mutant": mutation.name,
                    "target": mutation.path,
                    "expected_killing_tests": list(mutation.tests),
                    "killed": killed,
                    "evidence": evidence,
                }
            )
            if not killed:
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
                raise SystemExit(f"surviving mutation: {mutation.name}")
            print(f"KILLED {mutation.name}")

    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"mutation smoke PASS killed={len(results)}/{len(MUTATIONS)}")


if __name__ == "__main__":
    main()
