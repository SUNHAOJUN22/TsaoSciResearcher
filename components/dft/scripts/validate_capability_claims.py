#!/usr/bin/env python3
"""Cross-check capability support levels, implementation evidence, and public claim boundaries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_PATH = ROOT / "docs" / "CAPABILITY_STATUS.yaml"
POLICY_PATH = ROOT / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SUPPORT_LEVELS = {"L0_REFERENCE", "L1_HANDOFF", "L2_VALIDATED_ADAPTER", "L3_EXECUTION_TESTED"}
GENERIC_L3_REQUIRED = {"engine", "version", "site", "run_id", "artifact_sha256"}
ACCELERATION_L3_REQUIRED = {
    "engine",
    "engine_version",
    "build_fingerprint",
    "site",
    "hardware_fingerprint",
    "run_ids",
    "artifact_sha256",
    "cpu_reference",
    "minimum_repeats",
    "numerical_equivalence_pass",
    "parser_acceptance_pass",
    "performance_policy_pass",
    "evidence_bundle_sha256",
    "evidence_root_sha256",
    "review_attestation_id",
    "reviewer_identity",
    "review_scope",
    "review_signature_algorithm",
    "review_signature_verified",
    "independent_review_approved",
}
ACCELERATION_BOUNDARIES = {
    "signed review attestation must bind policy plan candidates and evidence root",
    "content addressed evidence root must verify every formal bundle file",
    "scoped L3 performance eligibility does not automatically change the public capability level",
}


def load_mapping(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"cannot parse {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {exc}"
    if not isinstance(data, dict):
        return None, f"{path.name} root must be a mapping"
    return data, None


def string_set(value: Any) -> set[str]:
    return set(value) if isinstance(value, list) and all(isinstance(item, str) for item in value) else set()


def validate_digest(evidence: dict[str, Any], field: str, prefix: str, failures: list[str]) -> None:
    digest = evidence.get(field)
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        failures.append(f"{prefix} {field} must be 64 lowercase hexadecimal characters")


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    capability_path = root / "docs" / "CAPABILITY_STATUS.yaml"
    policy_path = root / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml"
    capability, error = load_mapping(capability_path)
    if error is not None or capability is None:
        return [error or "capability status unavailable"]
    policy, error = load_mapping(policy_path)
    if error is not None or policy is None:
        return [error or "scientific claim policy unavailable"]

    release_path = root / "VERSION"
    release = release_path.read_text(encoding="utf-8").strip() if release_path.is_file() else None
    for name, data in (("CAPABILITY_STATUS", capability), ("SCIENTIFIC_CLAIM_POLICY", policy)):
        if release and data.get("release") != release:
            failures.append(f"{name} release does not match VERSION")

    allowed_levels = string_set(policy.get("support_levels"))
    if allowed_levels != SUPPORT_LEVELS:
        failures.append("scientific claim policy must define the exact L0-L3 support levels")

    required_evidence = string_set(policy.get("l3_required_evidence"))
    if required_evidence != GENERIC_L3_REQUIRED:
        failures.append("scientific claim policy has an incomplete L3 evidence contract")

    entries = capability.get("capabilities")
    if not isinstance(entries, list) or not entries:
        return [*failures, "CAPABILITY_STATUS capabilities must be a non-empty list"]
    has_hpc = any(isinstance(entry, dict) and entry.get("id") == "hpc" for entry in entries)
    acceleration_declared = policy.get("acceleration_l3_required_evidence") is not None
    acceleration_contract_required = has_hpc or acceleration_declared
    acceleration_required = string_set(policy.get("acceleration_l3_required_evidence"))
    if acceleration_contract_required and acceleration_required != ACCELERATION_L3_REQUIRED:
        failures.append("scientific claim policy has an incomplete signed acceleration L3 evidence contract")

    boundaries = string_set(policy.get("required_boundaries"))
    if acceleration_contract_required:
        for required_boundary in sorted(ACCELERATION_BOUNDARIES):
            if required_boundary not in boundaries:
                failures.append(f"scientific claim policy is missing required boundary: {required_boundary}")

    identifiers: set[str] = set()
    for index, entry in enumerate(entries):
        prefix = f"capability[{index}]"
        if not isinstance(entry, dict):
            failures.append(f"{prefix} must be a mapping")
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier:
            failures.append(f"{prefix} id must be a non-empty string")
        elif identifier in identifiers:
            failures.append(f"duplicate capability id: {identifier}")
        else:
            identifiers.add(identifier)
        skill = entry.get("skill")
        level = entry.get("support_level")
        if level not in allowed_levels:
            failures.append(f"{prefix} has invalid support_level: {level!r}")
        scripts = entry.get("scripts")
        if not isinstance(scripts, list) or not scripts or not all(isinstance(item, str) and item for item in scripts):
            failures.append(f"{prefix} scripts must be a non-empty string list")
        elif isinstance(skill, str):
            for script in scripts:
                path = root / "skills" / skill / "scripts" / script
                if not path.is_file():
                    failures.append(f"{prefix} implementation script missing: {path.relative_to(root)}")
        else:
            failures.append(f"{prefix} skill must be a non-empty string")

        execution_evidence = entry.get("execution_evidence")
        acceleration_evidence = entry.get("acceleration_execution_evidence")
        if level == "L3_EXECUTION_TESTED":
            if not isinstance(execution_evidence, dict):
                failures.append(f"{prefix} L3 capability lacks execution_evidence")
            else:
                missing = required_evidence - set(execution_evidence)
                if missing:
                    failures.append(f"{prefix} L3 execution_evidence missing fields: {sorted(missing)}")
                validate_digest(execution_evidence, "artifact_sha256", f"{prefix} L3", failures)

            if identifier == "hpc":
                if not isinstance(acceleration_evidence, dict):
                    failures.append(f"{prefix} HPC L3 capability lacks acceleration_execution_evidence")
                else:
                    missing = acceleration_required - set(acceleration_evidence)
                    if missing:
                        failures.append(f"{prefix} acceleration_execution_evidence missing fields: {sorted(missing)}")
                    for field in ("artifact_sha256", "evidence_bundle_sha256", "evidence_root_sha256"):
                        validate_digest(acceleration_evidence, field, f"{prefix} acceleration L3", failures)
                    if acceleration_evidence.get("review_signature_verified") is not True:
                        failures.append(f"{prefix} acceleration L3 review_signature_verified must be true")
                    if acceleration_evidence.get("independent_review_approved") is not True:
                        failures.append(f"{prefix} acceleration L3 independent_review_approved must be true")
        else:
            if execution_evidence is not None:
                failures.append(f"{prefix} non-L3 capability must not carry execution_evidence")
            if acceleration_evidence is not None:
                failures.append(f"{prefix} non-L3 capability must not carry acceleration_execution_evidence")

    forbidden = policy.get("forbidden_claim_phrases")
    forbidden_phrases = (
        [item.lower() for item in forbidden]
        if isinstance(forbidden, list) and all(isinstance(item, str) and item.strip() for item in forbidden)
        else []
    )
    if len(forbidden_phrases) < 5:
        failures.append("scientific claim policy must define at least five forbidden claim phrases")

    public_paths = [root / "README.md", root / "README_EN.md", *sorted((root / "skills").glob("*/SKILL.md"))]
    for path in public_paths:
        if not path.is_file():
            failures.append(f"missing public capability document: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden_phrases:
            if phrase in text:
                failures.append(f"forbidden unsupported claim in {path.relative_to(root)}: {phrase}")
    for readme_name in ("README.md", "README_EN.md"):
        path = root / readme_name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in ("L2_VALIDATED_ADAPTER", "L3_EXECUTION_TESTED"):
            if token not in text:
                failures.append(f"{readme_name} must explain {token}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures = validate()
    if args.json_output:
        print(json.dumps({"ok": not failures, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"Capability claim validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
