#!/usr/bin/env python3
"""Validate dependency, Python-version and release contracts without network access."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_TOML_BACKEND = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)(.*)$")
MINIMUM_PYTHON_RE = re.compile(r">=\s*(\d+)\.(\d+)")


def normalize_requirement(value: str) -> str:
    """Return a stable comparison key while preserving specifiers and markers."""

    cleaned = value.strip()
    match = REQUIREMENT_RE.fullmatch(cleaned)
    if match is None:
        raise ValueError(f"unsupported requirement: {value!r}")
    name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
    suffix = re.sub(r"\s+", "", match.group(2)).lower().replace('"', "'")
    return name + suffix


def read_requirements(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Read one requirements file and return includes, requirements and errors."""

    includes: list[str] = []
    requirements: list[str] = []
    errors: list[str] = []
    if not path.is_file():
        return includes, requirements, [f"missing requirements file: {path.name}"]

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ")):
            parts = line.split(maxsplit=1)
            if len(parts) != 2 or not parts[1].strip():
                errors.append(f"{path.name}:{line_number}: invalid include directive")
            else:
                includes.append(parts[1].strip())
            continue
        if line.startswith("-"):
            errors.append(f"{path.name}:{line_number}: unsupported pip option {line!r}")
            continue
        try:
            requirements.append(normalize_requirement(line))
        except ValueError as exc:
            errors.append(f"{path.name}:{line_number}: {exc}")
    return includes, requirements, errors


def normalized_release_version(value: str) -> str:
    """Translate the repository release notation to its PEP 440 form."""

    replacements = ((r"-alpha\.(\d+)$", r"a\1"), (r"-beta\.(\d+)$", r"b\1"), (r"-rc\.(\d+)$", r"rc\1"))
    result = value.strip()
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    return result


def load_pyproject(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing pyproject.toml"
    try:
        data = _TOML_BACKEND.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"pyproject.toml parse failed: {exc}"
    if not isinstance(data, dict):
        return None, "pyproject.toml root must be a table"
    return data, None


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    runtime_includes, runtime_requirements, runtime_errors = read_requirements(root / "requirements.txt")
    dev_includes, dev_requirements, dev_errors = read_requirements(root / "requirements-dev.txt")
    failures.extend(runtime_errors)
    failures.extend(dev_errors)

    if runtime_includes:
        failures.append(f"requirements.txt must not include other files: {runtime_includes}")
    if dev_includes != ["requirements.txt"]:
        failures.append("requirements-dev.txt must include requirements.txt exactly once")

    pyproject, error = load_pyproject(root / "pyproject.toml")
    if error is not None or pyproject is None:
        failures.append(error or "pyproject.toml could not be loaded")
        return failures

    project = pyproject.get("project")
    if not isinstance(project, dict):
        failures.append("pyproject.toml [project] table is missing")
        return failures

    project_dependencies = project.get("dependencies", [])
    if not isinstance(project_dependencies, list) or not all(isinstance(item, str) for item in project_dependencies):
        failures.append("project.dependencies must be a list of strings")
    else:
        normalized_project = sorted(normalize_requirement(item) for item in project_dependencies)
        if sorted(runtime_requirements) != normalized_project:
            failures.append("requirements.txt and project.dependencies differ")

    optional = project.get("optional-dependencies", {})
    project_dev = optional.get("dev", []) if isinstance(optional, dict) else []
    if not isinstance(project_dev, list) or not all(isinstance(item, str) for item in project_dev):
        failures.append("project.optional-dependencies.dev must be a list of strings")
    else:
        normalized_dev = sorted(normalize_requirement(item) for item in project_dev)
        if sorted(dev_requirements) != normalized_dev:
            failures.append("requirements-dev.txt and project.optional-dependencies.dev differ")

    version_path = root / "VERSION"
    if not version_path.is_file():
        failures.append("missing VERSION")
    else:
        release = normalized_release_version(version_path.read_text(encoding="utf-8"))
        if project.get("version") != release:
            failures.append(f"pyproject version {project.get('version')} != normalized VERSION {release}")

    requires_python = project.get("requires-python")
    minimum_match = MINIMUM_PYTHON_RE.search(requires_python) if isinstance(requires_python, str) else None
    ruff = pyproject.get("tool", {}).get("ruff", {}) if isinstance(pyproject.get("tool"), dict) else {}
    target = ruff.get("target-version") if isinstance(ruff, dict) else None
    if minimum_match is None:
        failures.append("project.requires-python must declare an explicit >= major.minor floor")
    elif not isinstance(target, str) or not target.startswith("py") or not target[2:].isdigit():
        failures.append("tool.ruff.target-version must use pyXY notation")
    else:
        digits = target[2:]
        target_version = (int(digits[0]), int(digits[1:]))
        minimum_version = (int(minimum_match.group(1)), int(minimum_match.group(2)))
        if target_version != minimum_version:
            failures.append(
                f"Ruff target {target_version[0]}.{target_version[1]} != Python floor "
                f"{minimum_version[0]}.{minimum_version[1]}"
            )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures = validate()
    payload = {"ok": not failures, "failures": failures}
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Dependency contract validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
