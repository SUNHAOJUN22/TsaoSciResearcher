#!/usr/bin/env python3
"""Validate wheel/sdist metadata, typed marker and isolated installation."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    directory = Path(args.directory)
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    wheels = sorted(directory.glob("*.whl"))
    sdists = sorted(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit(f"expected one wheel and one sdist: {wheels}, {sdists}")

    with zipfile.ZipFile(wheels[0]) as handle:
        names = set(handle.namelist())
        if "tsao_researcher/py.typed" not in names:
            raise SystemExit("wheel missing tsao_researcher/py.typed")
        metadata = next((name for name in names if name.endswith(".dist-info/METADATA")), None)
        if metadata is None:
            raise SystemExit("wheel METADATA is missing")
        metadata_text = handle.read(metadata).decode("utf-8")
        if f"Version: {version}" not in metadata_text:
            raise SystemExit("wheel version metadata mismatch")
        requirements = [
            line.split(":", 1)[1].strip().casefold()
            for line in metadata_text.splitlines()
            if line.startswith("Requires-Dist:")
        ]
        for dependency in ("pyyaml", "jsonschema"):
            if not any(requirement.startswith(dependency) for requirement in requirements):
                raise SystemExit(f"wheel metadata missing dependency: {dependency}")

    with tarfile.open(sdists[0], "r:gz") as handle:
        names = set(handle.getnames())
        if not any(name.endswith("/tsao_researcher/py.typed") for name in names):
            raise SystemExit("sdist missing py.typed")

    with tempfile.TemporaryDirectory(prefix="tsr-wheel-") as temporary:
        environment = Path(temporary) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(wheels[0]),
            ],
            check=True,
        )
        result = subprocess.run(
            [str(python), "-c", "import tsao_researcher; print(tsao_researcher.__version__)"],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() != version:
            raise SystemExit("isolated wheel import version mismatch")

    print(f"distribution PASS version={version} wheel={wheels[0].name} sdist={sdists[0].name}")


if __name__ == "__main__":
    main()
