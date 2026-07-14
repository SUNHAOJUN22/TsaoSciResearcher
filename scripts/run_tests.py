#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_ENV = os.environ.copy()
BASE_ENV["PYTHONDONTWRITEBYTECODE"] = "1"
BASE_ENV["PYTHONNOUSERSITE"] = "1"


def run(cmd, env=None):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=ROOT, check=True, env=env or BASE_ENV)


def main():
    run([sys.executable, "scripts/audit_repository.py"])
    with tempfile.TemporaryDirectory(prefix="tsr-pycache-") as td:
        env = BASE_ENV.copy()
        env["PYTHONPYCACHEPREFIX"] = td
        run([sys.executable, "-m", "compileall", "-q", "scripts", "tests"], env=env)
    run([sys.executable, "scripts/validate_structure.py"])
    run([sys.executable, "scripts/build_capability_index.py", "--check"])
    run([sys.executable, "scripts/generate_checksums.py", "--check"])
    run([sys.executable, "scripts/route_task.py", "--self-test"])
    run([sys.executable, "scripts/validate_figure.py", "examples/figure-contract.json"])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    print("ALL TESTS PASS")


if __name__ == "__main__":
    main()
