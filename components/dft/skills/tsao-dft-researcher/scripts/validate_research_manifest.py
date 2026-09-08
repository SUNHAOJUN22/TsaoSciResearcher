#!/usr/bin/env python3
"""Validate a computational-chemistry research/evidence manifest.

The validator is deterministic and intentionally stricter than a JSON Schema alone:
it checks calculation-artifact-claim relationships and evidence-grade promotion rules.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STATUSES = {
    "planned",
    "awaiting-prerequisite",
    "prepared",
    "ready",
    "running",
    "completed",
    "validated",
    "accepted",
    "inconclusive",
    "needs-follow-up",
    "contradicted",
    "rejected",
}
TASK_TYPES = {
    "minimum",
    "transition_state",
    "irc",
    "single_point",
    "tddft",
    "excited_opt",
    "nmr",
    "scan",
    "conformer",
    "counterpoise",
    "thermochemistry",
    "redox",
    "bond_dissociation",
    "trajectory",
    "analysis",
    "render",
    "report",
}
ARTIFACT_SOURCE_TYPES = {"calculation", "experiment", "literature", "external", "mock"}
ARTIFACT_STATUSES = {"raw", "completed", "validated", "accepted", "rejected"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required for YAML manifests; use JSON or install pyyaml") from exc
    return yaml.safe_load(text)


def _require_string(item: dict[str, Any], field: str, where: str, errors: list[str]) -> None:
    if not isinstance(item.get(field), str) or not item[field].strip():
        errors.append(f"{where}: missing non-empty string field {field}")


def _ideal_s2(multiplicity: int) -> float:
    spin = (multiplicity - 1) / 2.0
    return spin * (spin + 1.0)


def validate_manifest(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"], warnings

    _require_string(data, "project_id", "root", errors)
    _require_string(data, "research_question", "root", errors)
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str):
        warnings.append("root: schema_version is missing")

    calculations = data.get("calculations", [])
    artifacts = data.get("artifacts", [])
    claims = data.get("claims", [])
    if not isinstance(calculations, list):
        errors.append("root: calculations must be an array")
        calculations = []
    if not isinstance(artifacts, list):
        errors.append("root: artifacts must be an array")
        artifacts = []
    if not isinstance(claims, list):
        errors.append("root: claims must be an array")
        claims = []

    calc_by_id: dict[str, dict[str, Any]] = {}
    artifact_by_id: dict[str, dict[str, Any]] = {}

    for index, calc in enumerate(calculations):
        where = f"calculations[{index}]"
        if not isinstance(calc, dict):
            errors.append(f"{where}: must be an object")
            continue
        for field in ("id", "task_type", "status", "method", "basis", "phase_or_solvent"):
            _require_string(calc, field, where, errors)
        calc_id = calc.get("id")
        if isinstance(calc_id, str):
            if calc_id in calc_by_id:
                errors.append(f"{where}: duplicate calculation id {calc_id}")
            calc_by_id[calc_id] = calc
        if calc.get("task_type") not in TASK_TYPES:
            errors.append(f"{where}: unknown task_type {calc.get('task_type')!r}")
        if calc.get("status") not in STATUSES:
            errors.append(f"{where}: unknown status {calc.get('status')!r}")
        if not isinstance(calc.get("charge"), int):
            errors.append(f"{where}: charge must be an integer")
        multiplicity = calc.get("multiplicity")
        if not isinstance(multiplicity, int) or multiplicity < 1:
            errors.append(f"{where}: multiplicity must be a positive integer")
        temperature = calc.get("temperature_K")
        if temperature is not None and (not isinstance(temperature, (int, float)) or temperature <= 0):
            errors.append(f"{where}: temperature_K must be positive")
        if not calc.get("structure_sha256"):
            warnings.append(f"{where}: structure_sha256 is not recorded")
        elif not isinstance(calc.get("structure_sha256"), str) or not SHA256_RE.fullmatch(calc["structure_sha256"]):
            errors.append(f"{where}: structure_sha256 must be 64 lowercase hexadecimal characters")

        parent_id = calc.get("parent_id")
        if calc.get("task_type") == "single_point" and not isinstance(parent_id, str):
            errors.append(f"{where}: single_point requires parent_id")
        if calc.get("task_type") in {"thermochemistry", "redox", "bond_dissociation"}:
            if not calc.get("reference_state"):
                warnings.append(f"{where}: reference_state is missing")
            if not calc.get("standard_state"):
                warnings.append(f"{where}: standard_state is missing")

        validation = calc.get("validation", {})
        accepted = calc.get("status") == "accepted"
        if accepted and not isinstance(validation, dict):
            errors.append(f"{where}: accepted calculation requires validation object")
            validation = {}
        if accepted and validation.get("normal_termination") is not True:
            errors.append(f"{where}: accepted calculation requires normal_termination=true")
        if accepted and validation.get("scf_converged") is not True:
            errors.append(f"{where}: accepted calculation requires scf_converged=true")
        if (
            accepted
            and calc.get("task_type") in {"minimum", "transition_state", "excited_opt", "conformer"}
            and validation.get("optimization_converged") is not True
        ):
            errors.append(f"{where}: accepted optimized structure requires optimization_converged=true")
        if (
            accepted
            and calc.get("task_type") in {"minimum", "conformer"}
            and validation.get("imaginary_frequency_count") != 0
        ):
            errors.append(f"{where}: accepted minimum/conformer must have zero imaginary frequencies")
        if accepted and calc.get("task_type") == "transition_state":
            if validation.get("imaginary_frequency_count") != 1:
                errors.append(f"{where}: accepted transition state must have exactly one imaginary frequency")
            if validation.get("mode_reviewed") is not True:
                errors.append(f"{where}: accepted transition state requires mode_reviewed=true")
            forward = validation.get("irc_forward_artifact_id")
            reverse = validation.get("irc_reverse_artifact_id")
            if not forward or not reverse:
                errors.append(f"{where}: accepted transition state requires forward and reverse IRC artifacts")
            elif forward == reverse:
                errors.append(f"{where}: forward and reverse IRC artifacts must be different")
            if validation.get("irc_endpoints_confirmed") is not True:
                errors.append(f"{where}: accepted transition state requires irc_endpoints_confirmed=true")
        if accepted and isinstance(multiplicity, int) and multiplicity > 1:
            if validation.get("wavefunction_stable") is not True:
                errors.append(f"{where}: accepted open-shell calculation requires wavefunction_stable=true")
            s2_after = validation.get("s2_after")
            if not isinstance(s2_after, (int, float)):
                warnings.append(f"{where}: accepted open-shell calculation has no s2_after")
            else:
                deviation = abs(float(s2_after) - _ideal_s2(multiplicity))
                if deviation > 0.20:
                    warnings.append(f"{where}: S^2 deviation from ideal is {deviation:.3f}; review spin contamination")
        artifact_ids = calc.get("artifact_ids")
        if accepted and (not isinstance(artifact_ids, list) or not artifact_ids):
            errors.append(f"{where}: accepted calculation must link artifact_ids")

    for index, artifact in enumerate(artifacts):
        where = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{where}: must be an object")
            continue
        for field in ("id", "kind", "path", "sha256", "source_type", "status"):
            _require_string(artifact, field, where, errors)
        artifact_id = artifact.get("id")
        if isinstance(artifact_id, str):
            if artifact_id in artifact_by_id:
                errors.append(f"{where}: duplicate artifact id {artifact_id}")
            artifact_by_id[artifact_id] = artifact
        source_type = artifact.get("source_type")
        if source_type not in ARTIFACT_SOURCE_TYPES:
            errors.append(f"{where}: source_type must be one of {sorted(ARTIFACT_SOURCE_TYPES)}")
        if artifact.get("status") not in ARTIFACT_STATUSES:
            errors.append(f"{where}: invalid artifact status {artifact.get('status')!r}")
        calculation_id = artifact.get("calculation_id")
        if source_type == "calculation":
            if not isinstance(calculation_id, str) or calculation_id not in calc_by_id:
                errors.append(f"{where}: calculation artifact requires a valid calculation_id")
        elif calculation_id is not None and calculation_id not in calc_by_id:
            errors.append(f"{where}: calculation_id is not defined")
        sha256 = artifact.get("sha256")
        if isinstance(sha256, str) and not SHA256_RE.fullmatch(sha256):
            errors.append(f"{where}: sha256 must be 64 lowercase hexadecimal characters")
        if source_type == "experiment" and not artifact.get("measurement_provenance"):
            warnings.append(f"{where}: experimental artifact lacks measurement_provenance")
        if source_type == "literature" and not artifact.get("source_locator"):
            warnings.append(f"{where}: literature artifact lacks source_locator")

    for calc_id, calc in calc_by_id.items():
        parent_id = calc.get("parent_id")
        if isinstance(parent_id, str) and parent_id not in calc_by_id:
            errors.append(f"calculation {calc_id}: parent_id {parent_id} does not exist")
        for artifact_id in calc.get("artifact_ids", []) if isinstance(calc.get("artifact_ids"), list) else []:
            if artifact_id not in artifact_by_id:
                errors.append(f"calculation {calc_id}: artifact {artifact_id} does not exist")
            elif artifact_by_id[artifact_id].get("calculation_id") not in {None, calc_id}:
                errors.append(f"calculation {calc_id}: artifact {artifact_id} belongs to another calculation")
        validation = calc.get("validation", {})
        if isinstance(validation, dict):
            for key, expected_kind in (
                ("irc_forward_artifact_id", "irc_forward"),
                ("irc_reverse_artifact_id", "irc_reverse"),
            ):
                value = validation.get(key)
                if value:
                    artifact = artifact_by_id.get(value)
                    if artifact is None:
                        errors.append(f"calculation {calc_id}: {key}={value} does not exist")
                    elif artifact.get("kind") not in {expected_kind, "irc_log", "gaussian_log"}:
                        errors.append(
                            f"calculation {calc_id}: {key}={value} has incompatible kind {artifact.get('kind')!r}"
                        )
                    elif artifact.get("status") not in {"validated", "accepted"}:
                        errors.append(f"calculation {calc_id}: {key}={value} is not validated")

    for index, claim in enumerate(claims):
        where = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{where}: must be an object")
            continue
        for field in ("id", "text", "scope", "evidence_grade"):
            _require_string(claim, field, where, errors)
        grade = claim.get("evidence_grade")
        if grade not in {"A", "B", "C", "D"}:
            errors.append(f"{where}: evidence_grade must be A/B/C/D")
        linked = claim.get("artifact_ids")
        if not isinstance(linked, list) or not linked:
            errors.append(f"{where}: at least one artifact must be linked")
            linked = []
        linked_artifacts: list[dict[str, Any]] = []
        for artifact_id in linked:
            artifact = artifact_by_id.get(artifact_id)
            if artifact is None:
                errors.append(f"{where}: artifact {artifact_id} does not exist")
            else:
                linked_artifacts.append(artifact)
        if claim.get("is_mock") is True and grade in {"A", "B"}:
            errors.append(f"{where}: mock evidence cannot receive grade A or B")
        if claim.get("paper_ready") is True and grade == "D":
            errors.append(f"{where}: grade D evidence cannot be paper_ready")
        if not claim.get("limitations"):
            warnings.append(f"{where}: limitations are not recorded")
        if not claim.get("falsification_condition"):
            warnings.append(f"{where}: falsification_condition is not recorded")

        if grade == "A" and linked_artifacts:
            for artifact in linked_artifacts:
                if artifact.get("source_type") != "calculation" or artifact.get("status") != "accepted":
                    errors.append(f"{where}: grade A requires accepted calculation artifacts")
                    break
                calc = calc_by_id.get(str(artifact.get("calculation_id")))
                if calc is None or calc.get("status") != "accepted":
                    errors.append(f"{where}: grade A artifact is not backed by an accepted calculation")
                    break
        if (
            grade == "B"
            and linked_artifacts
            and not any(
                artifact.get("source_type") == "experiment" and artifact.get("status") == "accepted"
                for artifact in linked_artifacts
            )
        ):
            errors.append(f"{where}: grade B requires at least one accepted experimental artifact")
        if (
            grade == "C"
            and linked_artifacts
            and not any(artifact.get("source_type") in {"literature", "external"} for artifact in linked_artifacts)
        ):
            warnings.append(f"{where}: grade C usually links literature or external evidence")

    return errors, warnings


def _self_test() -> int:
    structure_hash = "b" * 64
    valid = {
        "schema_version": "1.0",
        "project_id": "demo",
        "research_question": "Is structure A a minimum?",
        "calculations": [
            {
                "id": "calc-1",
                "task_type": "minimum",
                "status": "accepted",
                "method": "wB97X-D",
                "basis": "def2-SVP",
                "charge": 0,
                "multiplicity": 1,
                "phase_or_solvent": "SMD(acetonitrile)",
                "temperature_K": 298.15,
                "structure_sha256": structure_hash,
                "artifact_ids": ["art-1"],
                "validation": {
                    "normal_termination": True,
                    "scf_converged": True,
                    "optimization_converged": True,
                    "imaginary_frequency_count": 0,
                },
            }
        ],
        "artifacts": [
            {
                "id": "art-1",
                "calculation_id": "calc-1",
                "kind": "gaussian_log",
                "path": "calc-1.log",
                "sha256": "a" * 64,
                "source_type": "calculation",
                "status": "accepted",
            }
        ],
        "claims": [
            {
                "id": "claim-1",
                "text": "A is a validated minimum.",
                "scope": "specified method",
                "evidence_grade": "A",
                "artifact_ids": ["art-1"],
                "limitations": ["static model"],
                "falsification_condition": "a reproducible imaginary mode appears",
                "paper_ready": True,
                "is_mock": False,
            }
        ],
    }
    errors, _ = validate_manifest(valid)
    broken = json.loads(json.dumps(valid))
    broken["calculations"][0]["validation"]["imaginary_frequency_count"] = 1
    broken_errors, _ = validate_manifest(broken)
    if errors or not broken_errors:
        print("SELF-TEST FAIL")
        if errors:
            print("Unexpected:", errors)
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if args.manifest is None:
        parser.error("manifest is required unless --self-test is used")
    try:
        data = _load(args.manifest)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read manifest: {exc}")
        return 2
    errors, warnings = validate_manifest(data)
    result = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"FAIL: {error}")
        print(f"RESULT: {'PASS' if not errors else 'FAIL'} ({len(errors)} errors, {len(warnings)} warnings)")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
