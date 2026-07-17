#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_ENV = os.environ.copy()
BASE_ENV["PYTHONDONTWRITEBYTECODE"] = "1"
BASE_ENV["PYTHONNOUSERSITE"] = "1"
DEFAULT_TIMEOUT_SECONDS = 300


def run(
    command: Sequence[str], *, env: Mapping[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> None:
    printable = [str(part) for part in command]
    print("+", " ".join(printable), flush=True)
    subprocess.run(
        printable,
        cwd=ROOT,
        check=True,
        env=dict(env or BASE_ENV),
        timeout=timeout,
        shell=False,
    )


def main() -> None:
    run([sys.executable, "scripts/audit_repository.py"])
    with tempfile.TemporaryDirectory(prefix="tsr-pycache-") as directory:
        env = BASE_ENV.copy()
        env["PYTHONPYCACHEPREFIX"] = directory
        run([sys.executable, "-m", "compileall", "-q", "scripts", "tests"], env=env)
    run([sys.executable, "scripts/validate_structure.py"])
    run([sys.executable, "scripts/build_capability_index.py", "--check"])
    run([sys.executable, "scripts/route_task.py", "--self-test"])
    run([sys.executable, "scripts/validate_figure.py", "examples/figure-contract.json"])
    run([sys.executable, "-m", "pytest", "-q"], timeout=600)
    run([sys.executable, "scripts/validate_release.py"], timeout=600)
    print("ALL TESTS PASS")


if __name__ == "__main__":
    main()
