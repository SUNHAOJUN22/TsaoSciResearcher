#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?")
_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?==([^\s;\\]+)")
_HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})(?=\s|$)")


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _direct_dependency_names(pyproject_path: Path) -> set[str]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml has no [project] table")
    rows: list[str] = []
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ValueError("project.dependencies must be a list")
    rows.extend(str(item) for item in dependencies)
    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, dict):
        raise ValueError("project.optional-dependencies must be a table")
    dev = optional.get("dev", [])
    if not isinstance(dev, list):
        raise ValueError("project.optional-dependencies.dev must be a list")
    rows.extend(str(item) for item in dev)
    names: set[str] = set()
    for row in rows:
        match = _NAME.match(row)
        if match is None:
            raise ValueError(f"cannot parse dependency name: {row}")
        names.add(normalize_name(match.group(1)))
    return names


def _logical_lines(text: str) -> list[str]:
    logical: list[str] = []
    pending = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pending = f"{pending} {line}".strip()
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        logical.append(pending)
        pending = ""
    if pending:
        logical.append(pending)
    return logical


def _option_issue(line: str) -> str | None:
    option, _, value = line.partition(" ")
    if option in {"--trusted-host", "--find-links", "--extra-index-url"}:
        return f"unsafe global option is forbidden: {option}"
    if option != "--index-url":
        return f"unsupported global option: {option}"
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        return "index URL must be an absolute HTTPS URL"
    if parsed.username or parsed.password:
        return "index URL must not contain credentials"
    return None


def verify_lock(lock_path: Path, pyproject_path: Path) -> dict[str, Any]:
    lock_path = Path(lock_path)
    pyproject_path = Path(pyproject_path)
    errors: list[str] = []
    packages: dict[str, dict[str, Any]] = {}
    global_options: list[str] = []
    for row_number, line in enumerate(_logical_lines(lock_path.read_text(encoding="utf-8")), 1):
        if line.startswith("--"):
            global_options.append(line)
            issue = _option_issue(line)
            if issue:
                errors.append(f"row {row_number}: {issue}")
            continue
        lowered = line.casefold()
        if lowered.startswith(("-e ", "git+", "hg+", "svn+", "bzr+", "file:", "http:", "https:")):
            errors.append(
                f"row {row_number}: editable, VCS, file and direct URL requirements are forbidden"
            )
            continue
        match = _PIN.match(line)
        if match is None:
            errors.append(f"row {row_number}: requirement is not exactly pinned with ==")
            continue
        raw_name, version = match.groups()
        name = normalize_name(raw_name)
        hashes = sorted(set(_HASH.findall(line)))
        if not hashes:
            errors.append(f"row {row_number}: {name} has no SHA-256 hash")
        if name in packages:
            errors.append(f"row {row_number}: duplicate package pin: {name}")
        packages[name] = {"version": version, "hashes": hashes}

    try:
        direct = _direct_dependency_names(pyproject_path)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        errors.append(f"pyproject: {exc}")
        direct = set()
    missing_direct = sorted(direct - set(packages))
    if missing_direct:
        errors.append("missing direct dependencies: " + ", ".join(missing_direct))
    if not packages:
        errors.append("lock contains no package pins")

    return {
        "format": "TSAO-DEPENDENCY-LOCK-1",
        "status": "PASS" if not errors else "FAIL",
        "lock_path": lock_path.as_posix(),
        "pyproject_path": pyproject_path.as_posix(),
        "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "package_count": len(packages),
        "direct_dependency_count": len(direct),
        "missing_direct_dependencies": missing_direct,
        "global_options": global_options,
        "packages": packages,
        "errors": errors,
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify an exact, hashed Python dependency lock")
    parser.add_argument("lock", nargs="?", default="requirements.lock")
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--json-out")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args(argv)
    lock = Path(args.lock)
    if not lock.is_file():
        if args.allow_missing:
            print(json.dumps({"status": "SKIP", "reason": f"missing {lock}"}, indent=2))
            return 0
        print(json.dumps({"status": "FAIL", "errors": [f"missing lock file: {lock}"]}, indent=2))
        return 2
    try:
        report = verify_lock(lock, Path(args.pyproject))
    except (OSError, UnicodeError) as exc:
        report = {"status": "FAIL", "errors": [str(exc)]}
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.json_out:
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    return 0 if report.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
