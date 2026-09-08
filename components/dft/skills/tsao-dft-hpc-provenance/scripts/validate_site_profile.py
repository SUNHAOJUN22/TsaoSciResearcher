#!/usr/bin/env python3
"""Validate a private/public HPC site profile without exposing secrets."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml

SCHEDULERS = {"local", "slurm", "pbs"}
WALLTIME_RE = re.compile(r"^(?:(\d+)-)?(\d+):(\d{2}):(\d{2})$")
CREDENTIAL_RE = re.compile(r"(token|password|secret)\s*[=:]\s*[\"']?[^\"',}\s]+", re.I)


def positive_number(value: Any, label: str, errors: list[str], *, integer: bool = False) -> None:
    valid_type = isinstance(value, int) if integer else isinstance(value, (int, float))
    if isinstance(value, bool) or not valid_type:
        errors.append(f"{label} must be {'a positive integer' if integer else 'positive finite numeric'}")
        return
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        errors.append(f"{label} must be {'a positive integer' if integer else 'positive finite numeric'}")


def valid_walltime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    match = WALLTIME_RE.fullmatch(value)
    if match is None:
        return False
    hour = int(match.group(2))
    minute = int(match.group(3))
    second = int(match.group(4))
    if minute >= 60 or second >= 60:
        return False
    return match.group(1) is None or hour < 24


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["site profile root must be a mapping"], warnings

    for key in [
        "schema_version",
        "site_id",
        "scheduler",
        "execution_host_scope",
        "software",
        "scratch",
        "resource_limits",
        "security",
        "status",
    ]:
        if key not in data:
            errors.append(f"missing {key}")
    if data.get("scheduler") not in SCHEDULERS:
        errors.append("unsupported scheduler")

    software = data.get("software")
    if not isinstance(software, dict):
        errors.append("software must be a mapping")
        software = {}
    for engine, record in software.items():
        if not isinstance(engine, str) or not engine:
            errors.append("software engine names must be non-empty strings")
            continue
        if not isinstance(record, dict):
            errors.append(f"software.{engine} must be mapping")
            continue
        for key in ("executable", "version_policy", "module_or_environment"):
            if record.get(key) in (None, "", "unknown"):
                warnings.append(f"software.{engine} unresolved {key}")

    scratch = data.get("scratch")
    if not isinstance(scratch, dict):
        errors.append("scratch must be a mapping")

    security = data.get("security")
    if not isinstance(security, dict):
        errors.append("security must be a mapping")
        security = {}
    contains_credentials = security.get("contains_credentials")
    if contains_credentials is True:
        errors.append("site profile must not contain credentials")
    elif contains_credentials is not False:
        errors.append("security.contains_credentials must be boolean false")

    serialized = yaml.safe_dump(data, sort_keys=True)
    if CREDENTIAL_RE.search(serialized):
        errors.append("possible credential literal detected")

    limits = data.get("resource_limits")
    if not isinstance(limits, dict):
        errors.append("resource_limits must be a mapping")
        limits = {}
    for key in ("max_nodes", "max_walltime", "max_memory_gb_per_node"):
        if key not in limits:
            warnings.append(f"resource_limits missing {key}")
    if "max_nodes" in limits:
        positive_number(limits.get("max_nodes"), "resource_limits.max_nodes", errors, integer=True)
    if "max_memory_gb_per_node" in limits:
        positive_number(
            limits.get("max_memory_gb_per_node"),
            "resource_limits.max_memory_gb_per_node",
            errors,
        )
    if "max_walltime" in limits and not valid_walltime(limits.get("max_walltime")):
        errors.append("resource_limits.max_walltime must be valid HH:MM:SS or D-HH:MM:SS")

    if data.get("status") == "accepted" and (errors or warnings):
        errors.append("accepted site profile has unresolved errors/warnings")
    return sorted(set(errors)), sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        data = yaml.safe_load(args.profile.read_text(encoding="utf-8"))
        errors, warnings = validate(data)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors = [f"site profile parse failed: {exc}"]
        warnings = []
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
