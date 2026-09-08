from __future__ import annotations

import runpy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast


def load_scan() -> Callable[[Path], dict[str, object]]:
    sys.path.insert(0, str(Path("scripts").resolve()))
    try:
        namespace = runpy.run_path("scripts/security_scan.py", run_name="security_scan_test")
    finally:
        sys.path.pop(0)
    return cast(Callable[[Path], dict[str, object]], namespace["scan"])


def test_security_scan_ignores_generated_directories_and_reports_findings(
    tmp_path: Path,
) -> None:
    dangerous_text = "e" + "val('x')\n"
    (tmp_path / "source.txt").write_text("safe", encoding="utf-8")
    (tmp_path / "unsafe.py").write_text(dangerous_text, encoding="utf-8")
    for directory in (
        ".hypothesis",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".tsao-computation",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "dist-a",
        "dist-b",
        "htmlcov",
        "tsao_scicomputation.egg-info",
        "venv",
    ):
        path = tmp_path / directory
        path.mkdir()
        (path / "generated.txt").write_text(dangerous_text, encoding="utf-8")
    (tmp_path / ".coverage").write_text("ignored", encoding="utf-8")
    (tmp_path / ".coverage.worker").write_text("ignored", encoding="utf-8")

    report = load_scan()(tmp_path)

    assert report["files_scanned"] == 2
    assert report["findings"] == [{"path": "unsafe.py", "rule": "dangerous_eval", "offset": 0}]
