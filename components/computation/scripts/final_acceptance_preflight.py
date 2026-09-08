#!/usr/bin/env python3
"""Deterministic delivery preflight for TsaoSciComputation.

The preflight validates repository contracts and evidence boundaries. It does not
launch an external solver or grant scientific approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

SCHEMA = "tsao.final-acceptance-preflight/v1"
REPOSITORY = "TsaoSciComputation"
MIN_PYTHON = (3, 10)
DELIVERY_PLATFORMS = ("windows", "linux")
EXTERNAL_BOUNDARY = "EXTERNAL_HOLD"
EXPECTED_COUNTS = {"capabilities": 164, "adapters": 27, "accelerators": 27, "workflows": 20}
REQUIRED_PATHS = (
    "README.md",
    "README.zh-CN.md",
    "README_ACCEPTANCE.md",
    "VERSION",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "tsao_computation/execution/runner.py",
    "tsao_computation/execution/resources.py",
    "tsao_computation/repository_audit.py",
    "tsao_computation/accelerators/audit.py",
    "docs/accelerated-native-backend.md",
    "docs/assets/acceptance/final-acceptance-map.svg",
)
BAD_ENCODING_MARKERS = ("\ufffd", "Ã", "Â", "â€“", "â€”", "â†’")
FORBIDDEN_PLATFORM_MARKERS = (
    "Operating System :: OS Independent",
    "Operating System :: MacOS",
    "macos-latest",
)


def platform_family(value: str | None = None) -> str:
    raw = (sys.platform if value is None else value).casefold()
    if raw.startswith(("win32", "cygwin", "msys")):
        return "windows"
    if raw.startswith("linux"):
        return "linux"
    return "unsupported"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _issue(issues: list[dict[str, str]], code: str, path: str, detail: str) -> None:
    issues.append({"code": code, "path": path, "detail": detail})


def _check_svg(path: Path, issues: list[dict[str, str]]) -> None:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError, DefusedXmlException) as exc:
        _issue(issues, "svg_invalid", path.as_posix(), str(exc))
        return
    if root is None:
        _issue(issues, "svg_root_missing", path.as_posix(), "parser returned no root element")
        return
    if not root.tag.endswith("svg"):
        _issue(issues, "svg_root_invalid", path.as_posix(), "root is not svg")
    if not root.attrib.get("viewBox"):
        _issue(issues, "svg_viewbox_missing", path.as_posix(), "scalable viewBox required")
    tags = {node.tag.rsplit("}", 1)[-1] for node in root}
    if "title" not in tags or "desc" not in tags:
        _issue(issues, "svg_accessibility_missing", path.as_posix(), "title and desc required")
    text = " ".join(node.text or "" for node in root.iter())
    for marker in ("AI-ASSISTED", "NOT SCIENTIFIC DATA", REPOSITORY):
        if marker not in text:
            _issue(issues, "svg_marker_missing", path.as_posix(), marker)
    for marker in BAD_ENCODING_MARKERS:
        if marker in text:
            _issue(issues, "svg_encoding_corrupt", path.as_posix(), repr(marker))


def _inventory_counts(root: Path, issues: list[dict[str, str]]) -> dict[str, int]:
    sys.path.insert(0, str(root))
    try:
        from tsao_computation.registries import accelerators, adapters, capabilities, workflows

        counts = {
            "capabilities": len(capabilities()),
            "adapters": len(adapters()),
            "accelerators": len(accelerators()),
            "workflows": len(workflows()),
        }
    except Exception as exc:  # fail-closed report, exercised by repository tests
        _issue(issues, "registry_load_failed", "tsao_computation/data/registry", str(exc))
        return {}
    finally:
        with suppress(ValueError):
            sys.path.remove(str(root))
    for name, expected in EXPECTED_COUNTS.items():
        observed = counts[name]
        if observed != expected:
            _issue(issues, "registry_count_mismatch", name, f"{observed} != {expected}")
    return counts


def build_report(root: Path, *, platform_name: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    issues: list[dict[str, str]] = []
    family = platform_family(platform_name)
    if family not in DELIVERY_PLATFORMS:
        _issue(issues, "platform_unsupported", platform_name or sys.platform, "Windows/Linux only")
    if sys.version_info[:2] < MIN_PYTHON:
        _issue(issues, "python_too_old", platform.python_version(), "Python >= 3.10 required")

    identities: dict[str, str] = {}
    for relative in REQUIRED_PATHS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            _issue(issues, "required_path_missing", relative, "regular file required")
            continue
        identities[relative] = _sha256(path)

    temporary_files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and any(path.name.endswith(suffix) for suffix in (".tmp", ".part", ".orig", ".rej"))
    )
    for relative in temporary_files:
        _issue(issues, "temporary_delivery_file", relative, "remove transport or editor residue")

    for relative in ("pyproject.toml", ".github/workflows/ci.yml"):
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for marker in FORBIDDEN_PLATFORM_MARKERS:
            if marker in text:
                _issue(issues, "unsupported_platform_claim", relative, marker)

    for relative in ("README.md", "README.zh-CN.md", "README_ACCEPTANCE.md"):
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for marker in BAD_ENCODING_MARKERS:
            if marker in text:
                _issue(issues, "text_encoding_corrupt", relative, repr(marker))

    acceptance = root / "README_ACCEPTANCE.md"
    if acceptance.is_file():
        text = acceptance.read_text(encoding="utf-8", errors="strict")
        for marker in (
            "中文",
            "English",
            EXTERNAL_BOUNDARY,
            "\\[",
            "H_{bundle}",
            "resource admission",
            "Windows",
            "Linux",
        ):
            if marker not in text:
                _issue(issues, "acceptance_marker_missing", "README_ACCEPTANCE.md", marker)

    svg = root / "docs/assets/acceptance/final-acceptance-map.svg"
    if svg.is_file():
        _check_svg(svg, issues)

    counts = _inventory_counts(root, issues)
    return {
        "schema": SCHEMA,
        "repository": REPOSITORY,
        "status": "PASS" if not issues else "BLOCK",
        "delivery_platforms": list(DELIVERY_PLATFORMS),
        "observed_platform": family,
        "python": platform.python_version(),
        "registry_counts": counts,
        "external_boundary": EXTERNAL_BOUNDARY,
        "solver_or_experiment_executed": False,
        "automatic_scientific_approval": False,
        "critical_file_sha256": dict(sorted(identities.items())),
        "issues": sorted(issues, key=lambda item: (item["code"], item["path"], item["detail"])),
    }


def _atomic_write(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        stream.write(rendered)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.root)
    if args.output is not None:
        _atomic_write(args.output, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
    else:
        print(f"{REPOSITORY} final acceptance preflight: {report['status']}")
        for issue in report["issues"]:
            print(f"- {issue['code']}: {issue['path']} — {issue['detail']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
