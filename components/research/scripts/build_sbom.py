#!/usr/bin/env python3
"""Generate a deterministic CycloneDX 1.6 SBOM from direct locked dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/SBOM.cdx.json"
LOCK = ROOT / "requirements-ci.lock"
REQUIREMENT = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$")
NAMESPACE = uuid.UUID("ebd12bf7-87f8-5a35-9921-7a33fc874a31")


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirements() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in LOCK.read_text(encoding="utf-8", errors="strict").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = REQUIREMENT.fullmatch(stripped)
        if not match:
            raise ValueError(f"requirements-ci.lock entry must be exact NAME==VERSION: {stripped}")
        rows.append((_normalized_name(match.group(1)), match.group(2)))
    return sorted(dict.fromkeys(rows))


def build() -> dict[str, Any]:
    version = (ROOT / "VERSION").read_text(encoding="utf-8", errors="strict").strip()
    dependencies = _requirements()
    refs = [f"pkg:pypi/{name}@{dep_version}" for name, dep_version in dependencies]
    identity = "\n".join([version, *refs])
    serial = uuid.uuid5(NAMESPACE, identity)
    root_ref = f"pkg:pypi/tsao-sci-researcher@{version}"
    components = [
        {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": dep_version,
            "purl": ref,
            "scope": "required",
        }
        for (name, dep_version), ref in zip(dependencies, refs, strict=True)
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": root_ref,
                "name": "tsao-sci-researcher",
                "version": version,
                "purl": root_ref,
            },
            "properties": [
                {"name": "tsao:source", "value": "requirements-ci.lock"},
                {"name": "tsao:lock-sha256", "value": hashlib.sha256(LOCK.read_bytes()).hexdigest()},
                {"name": "tsao:truth-boundary", "value": "SBOM inventory is not a vulnerability assessment."},
            ],
        },
        "components": components,
        "dependencies": [
            {"ref": root_ref, "dependsOn": refs},
            *({"ref": ref, "dependsOn": []} for ref in refs),
        ],
    }


def validate(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("bomFormat") != "CycloneDX" or value.get("specVersion") != "1.6":
        errors.append("SBOM identity must be CycloneDX 1.6")
    components = value.get("components")
    if not isinstance(components, list) or len(components) != len(_requirements()):
        errors.append("SBOM component inventory does not match requirements-ci.lock")
    serialized = json.dumps(value, sort_keys=True)
    if hashlib.sha256(LOCK.read_bytes()).hexdigest() not in serialized:
        errors.append("SBOM does not contain the dependency lock digest")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    rendered = json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    errors = validate(expected)
    if errors:
        raise SystemExit("SBOM generation FAIL: " + "; ".join(errors))
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.is_symlink() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("SBOM is stale; run scripts/build_sbom.py --write")
        print(f"deterministic SBOM PASS ({len(expected['components'])} components)")
        return
    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
