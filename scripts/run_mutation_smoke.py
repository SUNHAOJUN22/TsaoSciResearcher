#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
        "router-word-boundary",
        "scripts/route_task.py",
        "return re.search(pattern, haystack) is not None",
        "return keyword in haystack",
        ("tests/test_router.py",),
    ),
    Mutation(
        "project-time-monotonicity",
        "scripts/validate_project.py",
        "if updated < created:",
        "if False and updated < created:",
        ("tests/test_project_state.py",),
    ),
)


def main() -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    killed = 0
    with tempfile.TemporaryDirectory(prefix="tsr-mutation-") as temporary:
        base = Path(temporary)
        for index, mutation in enumerate(MUTATIONS):
            work = base / f"mutation-{index:02d}"
            shutil.copytree(ROOT / "scripts", work / "scripts")
            shutil.copytree(ROOT / "tests", work / "tests")
            shutil.copytree(ROOT / "schemas", work / "schemas")
            shutil.copy2(ROOT / "router_rules.json", work / "router_rules.json")
            target = work / mutation.path
            source = target.read_text(encoding="utf-8", errors="strict")
            if source.count(mutation.before) != 1:
                raise SystemExit(f"mutation anchor is not unique: {mutation.name}")
            target.write_text(source.replace(mutation.before, mutation.after, 1), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *mutation.tests],
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                shell=False,
            )
            if result.returncode == 0:
                print(result.stdout)
                raise SystemExit(f"surviving mutation: {mutation.name}")
            killed += 1
            print(f"KILLED {mutation.name}")
    print(f"mutation smoke PASS killed={killed}/{len(MUTATIONS)}")


if __name__ == "__main__":
    main()
