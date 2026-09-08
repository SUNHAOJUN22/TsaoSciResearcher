#!/usr/bin/env python3
"""Verify the EPDM acceptance path from an installed release Wheel."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

_REQUIRED = {
    "skills/epdm/acceptance.py",
    "skills/epdm/docs/SOFTWARE_ACCEPTANCE.md",
    "skills/epdm/tests/test_acceptance.py",
}
_RUNTIME_LOAD_SAMPLES = 3


def _choose_wheel(directory: Path) -> Path:
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"expected exactly one Wheel in {directory}, found {len(wheels)}")
    return wheels[0]


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def _acceptance_code(extra_path: Path | None = None) -> str:
    prefix = ""
    if extra_path is not None:
        prefix = f"import sys; sys.path.insert(0, {str(extra_path)!r}); "
    return prefix + (
        "from skills.epdm.acceptance import qualify_acceptance; "
        f"result=qualify_acceptance(load_samples={_RUNTIME_LOAD_SAMPLES}); "
        "assert result.pass_, result.as_dict(); "
        "print(__import__('json').dumps(result.as_dict(), allow_nan=False))"
    )


def verify(wheel: Path) -> dict[str, object]:
    errors: list[str] = []
    runtimes: dict[str, object] = {}
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    missing = sorted(member for member in _REQUIRED if member not in names)
    if missing:
        errors.append(f"missing acceptance Wheel members: {missing}")

    with tempfile.TemporaryDirectory(prefix="tsao-acceptance-wheel-") as temporary:
        root = Path(temporary)
        target = root / "target"
        install = _run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--no-deps",
                "--target",
                str(target),
                str(wheel.resolve()),
            ],
            cwd=root,
        )
        if install.returncode:
            errors.append(
                f"PIP_TARGET install failed: {install.stderr.strip() or install.stdout.strip()}"
            )
        else:
            completed = _run([sys.executable, "-I", "-c", _acceptance_code(target)], cwd=root)
            if completed.returncode:
                errors.append(
                    "PIP_TARGET acceptance failed: "
                    f"{completed.stderr.strip() or completed.stdout.strip()}"
                )
            else:
                runtimes["PIP_TARGET"] = json.loads(completed.stdout)

        venv_root = root / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_root)
        python_executable = _venv_python(venv_root)
        install = _run(
            [
                str(python_executable),
                "-m",
                "pip",
                "install",
                "--quiet",
                str(wheel.resolve()),
            ],
            cwd=root,
        )
        if install.returncode:
            errors.append(
                f"STANDARD_VENV install failed: {install.stderr.strip() or install.stdout.strip()}"
            )
        else:
            completed = _run([str(python_executable), "-I", "-c", _acceptance_code()], cwd=root)
            if completed.returncode:
                errors.append(
                    "STANDARD_VENV acceptance failed: "
                    f"{completed.stderr.strip() or completed.stdout.strip()}"
                )
            else:
                runtimes["STANDARD_VENV"] = json.loads(completed.stdout)

    return {
        "wheel": str(wheel),
        "pass": not errors,
        "errors": errors,
        "required_members": sorted(_REQUIRED),
        "runtime_load_samples": _RUNTIME_LOAD_SAMPLES,
        "runtimes": runtimes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(_choose_wheel(args.wheel_dir))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        result = {"pass": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
