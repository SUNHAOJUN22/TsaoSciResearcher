#!/usr/bin/env python3
"""Executable schemas, policy enforcement, signed reviews and atomic evidence bundles."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from shell_contract import (  # noqa: E402 -- standalone Skill import contract
    canonical_json,
    sha256_bytes,
    sha256_file,
    verify_signed_attestation,
)

POLICY_FIELDS = {
    "schema_version",
    "policy_id",
    "minimum_successful_repeats",
    "require_independent_review",
    "require_real_engine_source",
    "require_verified_artifacts",
    "require_performance_improvement",
    "numerical_equivalence",
    "performance",
    "acceleration_l3_required_evidence",
    "qualification_statuses",
}


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} root must be an object")
    return loaded


def load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} root must be a mapping")
    return loaded


def schema_errors(instance: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "root"
        errors.append(f"{location}: {error.message}")
    return errors


def validate_policy(policy: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors = schema_errors(policy, schema)
    unknown = sorted(set(policy) - POLICY_FIELDS)
    if unknown:
        errors.append(f"policy contains unsupported fields: {unknown}")
    required_evidence = set(policy.get("acceleration_l3_required_evidence") or [])
    expected = {
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
        "independent_review_approved",
    }
    if required_evidence != expected:
        errors.append("acceleration_l3_required_evidence does not match the executable contract")
    return sorted(set(errors))


def scientific_identity_digest(record: dict[str, Any]) -> str:
    engine = record.get("engine") or {}
    scientific = record.get("scientific") or {}
    payload = {
        "engine": engine.get("name"),
        "engine_version": engine.get("version"),
        "input_sha256": scientific.get("input_sha256"),
        "method_fingerprint_id": scientific.get("method_fingerprint_id"),
        "model_identity": scientific.get("model_identity"),
        "convergence_thresholds": scientific.get("convergence_thresholds"),
        "observable_set": sorted(scientific.get("observable_set") or []),
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def topology_digest(record: dict[str, Any]) -> str:
    hardware = record.get("hardware") or {}
    payload = {
        "hardware_fingerprint_id": hardware.get("hardware_fingerprint_id"),
        "cpu_model": hardware.get("cpu_model"),
        "cpu_arch": hardware.get("cpu_arch"),
        "nodes": hardware.get("nodes"),
        "ranks_per_node": hardware.get("ranks_per_node"),
        "threads_per_rank": hardware.get("threads_per_rank"),
        "gpu_vendor": hardware.get("gpu_vendor"),
        "gpu_model": hardware.get("gpu_model"),
        "gpu_uuids": sorted(hardware.get("gpu_uuids") or []),
        "driver_version": hardware.get("driver_version"),
        "gpu_binding": hardware.get("gpu_binding"),
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def validate_record_schema(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    return schema_errors(record, schema)


def isolate_benchmark_plan(records: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    plans = sorted({str(record.get("benchmark_plan_id", "")) for record in records})
    if len(plans) != 1 or not plans[0]:
        return None, [f"exactly one non-empty benchmark_plan_id is required, found {plans}"]
    errors: list[str] = []
    identities: dict[tuple[str, str], tuple[str, str, str]] = {}
    for record in records:
        candidate = str(record.get("candidate_id", ""))
        role = str(record.get("role", ""))
        engine = record.get("engine") or {}
        key = (plans[0], candidate)
        identity = (
            scientific_identity_digest(record),
            str(engine.get("build_fingerprint_id", "")),
            topology_digest(record),
        )
        previous = identities.get(key)
        if previous is not None and previous != identity:
            errors.append(f"candidate {candidate} mixes scientific, build or topology identities")
        identities[key] = identity
        if role == "scientific-reference" and (record.get("hardware") or {}).get("gpu_uuids"):
            errors.append(f"scientific reference {candidate} must not carry GPU UUIDs")
    return plans[0], sorted(set(errors))


def enforce_policy(
    candidate: dict[str, Any],
    reference_status: str,
    policy: dict[str, Any],
    review_errors: list[str],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    minimum_repeats = int(policy["minimum_successful_repeats"])
    if reference_status != "PASS":
        return "REFERENCE_MISSING", ["accepted CPU reference with sufficient repeats is missing"]
    if not candidate.get("build_identity_consistent"):
        return "BUILD_IDENTITY_MISSING", ["build fingerprint is missing or inconsistent"]
    if not candidate.get("hardware_identity_consistent"):
        return "HARDWARE_IDENTITY_MISSING", ["hardware fingerprint or topology is missing or inconsistent"]
    parser_runs = int(candidate.get("parser_accepted_runs", 0))
    total_runs = int(candidate.get("total_runs", 0))
    if total_runs >= minimum_repeats and parser_runs < minimum_repeats:
        return "PARSER_NOT_ACCEPTED", ["insufficient parser-accepted successful runs"]
    if policy["require_verified_artifacts"] and not candidate.get("all_artifacts_verified"):
        return "ARTIFACT_HASH_MISMATCH", ["one or more artifacts are not verified"]
    if not candidate.get("minimum_repeats_pass"):
        return "INSUFFICIENT_REPEATS", ["minimum successful repeat count is not met"]
    if candidate.get("numerical_equivalence", {}).get("status") != "PASS":
        return "NUMERICAL_MISMATCH", candidate.get("numerical_equivalence", {}).get("reasons", [])
    speedup = candidate.get("cpu_to_candidate_speedup")
    minimum_speedup = float(policy["performance"]["minimum_cpu_to_candidate_speedup"])
    if policy["require_performance_improvement"] and (speedup is None or float(speedup) <= minimum_speedup):
        return "PERFORMANCE_NOT_IMPROVED", [f"speedup must be greater than {minimum_speedup}"]
    minimum_efficiency = float(policy["performance"]["minimum_strong_scaling_efficiency"])
    efficiency = candidate.get("strong_scaling_efficiency")
    gpu_total = int((candidate.get("resources") or {}).get("gpus_total", 0))
    if gpu_total > 1 and minimum_efficiency > 0 and (efficiency is None or float(efficiency) < minimum_efficiency):
        return "PERFORMANCE_POLICY_FAILED", [f"strong-scaling efficiency must be at least {minimum_efficiency}"]
    if policy["require_real_engine_source"] and not candidate.get("all_sources_real_engine"):
        reasons.append("all records must declare evidence_source.kind=real-engine")
    if policy["require_independent_review"] and review_errors:
        reasons.extend(review_errors)
    if reasons:
        return "L2_ONLY", sorted(set(reasons))
    return "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE", []


def prequalification_payload(
    records: list[dict[str, Any]], summary: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "tool": "TsaoDFT",
        "policy": policy,
        "benchmark_plan_id": summary.get("benchmark_plan_id"),
        "records_sha256": sha256_bytes(canonical_json(records).encode("utf-8")),
        "summary_sha256": sha256_bytes(canonical_json(summary).encode("utf-8")),
        "candidate_ids": sorted(
            candidate_id
            for candidate_id, candidate in (summary.get("candidates") or {}).items()
            if candidate.get("role") != "scientific-reference"
        ),
    }


def verify_review(
    review: dict[str, Any],
    public_key_pem: bytes,
    prequalification_root: str,
    policy_id: str,
    benchmark_plan_id: str,
    candidate_ids: list[str],
) -> list[str]:
    expected = {
        "policy_id": policy_id,
        "benchmark_plan_id": benchmark_plan_id,
        "candidate_ids": candidate_ids,
        "evidence_root_sha256": prequalification_root,
    }
    errors = verify_signed_attestation(review, public_key_pem, expected)
    if review.get("decision") != "approved":
        errors.append("review decision is not approved")
    if review.get("scope") != "scoped-performance-evidence":
        errors.append("review scope is not scoped-performance-evidence")
    return sorted(set(errors))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def build_root_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "files": {
            name: {"sha256": sha256_bytes(content), "size_bytes": len(content)}
            for name, content in sorted(files.items())
        },
    }


def publish_content_addressed_bundle(
    output_parent: Path,
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    policy: dict[str, Any],
    review: dict[str, Any],
    qualification: dict[str, Any],
) -> dict[str, Any]:
    output_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".evidence-stage-", dir=output_parent))
    try:
        documents = {
            "records.json": (json.dumps(records, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
            "benchmark-summary.json": (
                json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode(),
            "policy.json": (json.dumps(policy, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
            "review-attestation.json": (
                json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode(),
            "qualification-report.json": (
                json.dumps(qualification, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode(),
        }
        root_manifest = build_root_manifest(documents)
        root_bytes = (json.dumps(root_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        root_sha = sha256_bytes(root_bytes)
        documents["evidence-root.json"] = root_bytes
        for name, content in documents.items():
            (stage / name).write_bytes(content)
        target = output_parent / f"evidence-{root_sha}"
        if target.exists():
            report = verify_content_addressed_bundle(target)
            if not report["ok"] or report.get("root_sha256") != root_sha:
                raise ValueError(f"content-addressed target already exists with different content: {target}")
            shutil.rmtree(stage)
            return {"ok": True, "out_dir": str(target), "root_sha256": root_sha, "reused": True}
        os.replace(stage, target)
        report = verify_content_addressed_bundle(target)
        if not report["ok"]:
            shutil.rmtree(target, ignore_errors=True)
            raise ValueError(f"published evidence bundle failed verification: {report['errors']}")
        return {"ok": True, "out_dir": str(target), "root_sha256": root_sha, "reused": False}
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_content_addressed_bundle(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    root_path = path / "evidence-root.json"
    if not root_path.is_file():
        return {"ok": False, "errors": ["evidence-root.json is missing"]}
    try:
        root_manifest = load_json(root_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [str(exc)]}
    root_sha = sha256_file(root_path)
    if path.name != f"evidence-{root_sha}":
        errors.append("directory name does not match evidence root SHA-256")
    files = root_manifest.get("files")
    if not isinstance(files, dict):
        errors.append("evidence root files must be a mapping")
    else:
        expected_names = set(files) | {"evidence-root.json"}
        observed_names = {item.name for item in path.iterdir() if item.is_file()}
        if observed_names != expected_names:
            errors.append(
                f"bundle file set mismatch: expected {sorted(expected_names)}, found {sorted(observed_names)}"
            )
        for name, metadata in files.items():
            file_path = path / name
            if not file_path.is_file():
                errors.append(f"bundle file is missing: {name}")
                continue
            if not isinstance(metadata, dict) or sha256_file(file_path) != metadata.get("sha256"):
                errors.append(f"bundle file digest mismatch: {name}")
            elif file_path.stat().st_size != metadata.get("size_bytes"):
                errors.append(f"bundle file size mismatch: {name}")
    return {"ok": not errors, "errors": sorted(set(errors)), "root_sha256": root_sha}
