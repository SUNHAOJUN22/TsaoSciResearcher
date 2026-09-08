#!/usr/bin/env python3
"""Deterministic final-acceptance preflight for TSAO-PROCESSING-SKILL.

This script qualifies repository delivery surfaces only. It never invokes a
commercial solver, claims a scientific result, or upgrades external evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = "tsao.final-acceptance-preflight/v1"
REPOSITORY = "TSAO-PROCESSING-SKILL"
MIN_PYTHON = (3, 11)
MAX_SVG_BYTES = 2_000_000
ALLOWED_PLATFORM_FAMILIES = ("windows", "linux")
EXTERNAL_BOUNDARY_MARKER = "NOT_EVALUATED"
REQUIRED_PATHS = (
    "README.md",
    "README.zh-CN.md",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "scripts/run_ci.py",
    "tsao/cli.py",
    "skills/epdm/numerical_integration.py",
    "README_ACCEPTANCE.md",
    "docs/assets/acceptance/final-acceptance-map.svg",
)
FORBIDDEN_PLATFORM_MARKERS = (
    "macos-latest",
    "Operating System :: MacOS",
    "Operating System :: OS Independent",
)


def platform_family(value: str | None = None) -> str:
    """Normalize Python platform identifiers to a stable delivery family."""

    raw = (sys.platform if value is None else value).casefold()
    if raw.startswith(("win32", "cygwin", "msys")):
        return "windows"
    if raw.startswith("linux"):
        return "linux"
    return "unsupported"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _issue(
    issues: list[dict[str, str]],
    code: str,
    path: str,
    detail: str,
) -> None:
    issues.append({"code": code, "path": path, "detail": detail})


def _check_svg(path: Path, issues: list[dict[str, str]]) -> None:
    """Validate a bounded, repository-owned SVG without parsing active XML."""

    try:
        size = path.stat().st_size
        if size > MAX_SVG_BYTES:
            _issue(
                issues,
                "svg_too_large",
                str(path),
                f"SVG exceeds the {MAX_SVG_BYTES}-byte acceptance limit",
            )
            return
        text = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        _issue(issues, "svg_unreadable", str(path), str(exc))
        return

    normalized = text.lstrip("\ufeff \t\r\n")
    if "<svg" not in normalized[:512].casefold():
        _issue(issues, "svg_root_invalid", str(path), "Opening <svg> tag is missing")
    if "</svg>" not in normalized[-2048:].casefold():
        _issue(issues, "svg_not_closed", str(path), "Closing </svg> tag is missing")
    for marker in ("AI-ASSISTED", "NOT SCIENTIFIC DATA", REPOSITORY):
        if marker not in text:
            _issue(issues, "svg_marker_missing", str(path), marker)


def build_report(root: Path, *, platform_name: str | None = None) -> dict[str, Any]:
    """Build a deterministic machine-readable acceptance report."""

    root = root.resolve()
    issues: list[dict[str, str]] = []
    family = platform_family(platform_name)
    if family not in ALLOWED_PLATFORM_FAMILIES:
        _issue(
            issues,
            "platform_unsupported",
            platform_name or sys.platform,
            "Only Windows and Linux belong to the delivery contract",
        )
    if sys.version_info[:2] < MIN_PYTHON:
        _issue(
            issues,
            "python_too_old",
            platform.python_version(),
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required",
        )

    identities: dict[str, str] = {}
    for relative in REQUIRED_PATHS:
        path = root / relative
        if not path.is_file():
            _issue(
                issues,
                "required_path_missing",
                relative,
                "Required acceptance surface is missing",
            )
            continue
        identities[relative] = _sha256(path)

    textual_paths = [
        root / "pyproject.toml",
        root / ".github" / "workflows" / "ci.yml",
    ]
    for path in textual_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for marker in FORBIDDEN_PLATFORM_MARKERS:
            if marker in text:
                _issue(
                    issues,
                    "unsupported_platform_claim",
                    str(path.relative_to(root)),
                    marker,
                )

    acceptance_readme = root / "README_ACCEPTANCE.md"
    if acceptance_readme.is_file():
        text = acceptance_readme.read_text(encoding="utf-8", errors="strict")
        for marker in (
            "中文",
            "English",
            EXTERNAL_BOUNDARY_MARKER,
            "Windows",
            "Linux",
            "\\[",
        ):
            if marker not in text:
                _issue(
                    issues,
                    "acceptance_readme_marker_missing",
                    "README_ACCEPTANCE.md",
                    marker,
                )

    svg = root / "docs" / "assets" / "acceptance" / "final-acceptance-map.svg"
    if svg.is_file():
        _check_svg(svg, issues)

    return {
        "schema": SCHEMA,
        "repository": REPOSITORY,
        "status": "PASS" if not issues else "BLOCK",
        "delivery_platforms": list(ALLOWED_PLATFORM_FAMILIES),
        "observed_platform": family,
        "python": platform.python_version(),
        "external_boundary_marker": EXTERNAL_BOUNDARY_MARKER,
        "solver_or_experiment_executed": False,
        "automatic_scientific_approval": False,
        "critical_file_sha256": dict(sorted(identities.items())),
        "issues": sorted(
            issues,
            key=lambda item: (item["code"], item["path"], item["detail"]),
        ),
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as stream:
        stream.write(data)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit compact JSON on stdout")
    args = parser.parse_args(argv)

    report = build_report(args.root)
    if args.output is not None:
        _atomic_write_json(args.output, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
    else:
        print(f"{REPOSITORY} final acceptance preflight: {report['status']}")
        for issue in report["issues"]:
            print(f"- {issue['code']}: {issue['path']} — {issue['detail']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
