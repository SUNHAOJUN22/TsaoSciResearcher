from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 120


def minimal_subprocess_environment() -> dict[str, str]:
    """Return a deterministic environment with only platform-critical variables."""
    keep = {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
    environment = {key: value for key, value in os.environ.items() if key in keep}
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
        }
    )
    environment.pop("PYTHONPATH", None)
    return environment


def run_python(
    arguments: Sequence[str],
    *,
    cwd: Path = ROOT,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run the active Python interpreter without a shell and capture both streams."""
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        env=minimal_subprocess_environment(),
        shell=False,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=timeout,
    )
