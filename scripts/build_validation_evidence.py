#!/usr/bin/env python3
"""Write or verify non-self-referential repository validation evidence schema 1.6."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/VALIDATION_EVIDENCE.json"
SCHEMA = ROOT / "schemas/v2/validation-evidence.schema.json"
LOCK_FILE = ROOT / "requirements-ci.lock"
BASELINE = ROOT / "docs/VALIDATION_BASELINE.json"
FOCUSED = ROOT / "docs/CURRENT_CHANGE_REGRESSION.json"
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tsao-research",
    "artifacts",
    "build",
    "dist",
    "site",
    "__pycache__",
}
GENERATED_PREFIXES = ("dist-", "dist_", "build-", "build_", "release-", "release_")
EXCLUDED_PATHS = {
    "SHA256SUMS",
    "docs/QUALITY_HISTORY.json",
    "docs/VALIDATION_EVIDENCE.json",
    "docs/test-dashboard.html",
    "docs/test-dashboard.svg",
    "docs/engineering-audit-report.pdf",
}
COVERAGE_RUNTIME_PATTERNS = (".coverage", ".coverage.*")
DEFAULT_COMPATIBILITY = {
    "macos_python_3_12": "PASS",
    "ubuntu_python_3_10": "PASS",
    "ubuntu_python_3_13": "PASS",
    "windows_python_3_12": "PASS",
}
REQUIRED_CURRENT_GATES = {
    "validation_tree_digest",
    "scientific_quality_guards",
    "deterministic_visual_reports",
    "coverage_line_and_branch",
    "dependency_vulnerability_audit",
    "deterministic_sbom",
    "wheel_and_sdist_install",
    "docs_build",
    "reproducibility_capsule",
    "execution_receipts",
}
CI_ONLY_GATES = {
    "bandit_high_severity",
    "complete_regression",
    "coverage_line_and_branch",
    "critical_mutation_killed",
    "dependency_vulnerability_audit",
    "docs_build",
    "mypy_strict",
    "reverse_order_regression",
    "ruff_format_and_lint",
    "seeded_random_order_regression",
    "wheel_and_sdist_install",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


def _is_coverage_runtime_file(path: Path) -> bool:
    return path.name == ".coverage" or path.name.startswith(".coverage.")


def _source_files() -> list[Path]:
    rows: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if relative.parts and relative.parts[0].startswith(GENERATED_PREFIXES):
            continue
        if not path.is_file() or path.is_symlink():
            continue
        if _is_coverage_runtime_file(path):
            continue
        if relative.as_posix() in EXCLUDED_PATHS or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(path)
    return sorted(rows, key=lambda item: item.relative_to(ROOT).as_posix())


def tree_digest() -> tuple[str, int]:
    digest = hashlib.sha256()
    files = _source_files()
    for path in files:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        file_digest = hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii")
        digest.update(relative + b"\0" + file_digest + b"\n")
    return digest.hexdigest(), len(files)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def _compatibility(current: dict[str, Any]) -> dict[str, str]:
    value = current.get("compatibility")
    if not isinstance(value, dict):
        return dict(DEFAULT_COMPATIBILITY)
    rows = {str(key): str(status) for key, status in value.items()}
    return rows or dict(DEFAULT_COMPATIBILITY)


def _inventory() -> dict[str, Any]:
    v2 = json.loads((ROOT / "capabilities/v2/index.json").read_text(encoding="utf-8"))
    return {
        "capability_records": int(v2["total"]),
        "domain_packs": len([path for path in (ROOT / "domain-packs").iterdir() if path.is_dir()]),
        "generic_domain_placeholders": int(v2["generic_domain_slots"]),
        "runtime_core_capabilities": int(v2["core_added"]),
        "schemas": len(list((ROOT / "schemas").rglob("*.schema.json"))),
        "test_modules": len(list((ROOT / "tests").glob("test_*.py"))),
        "workbook_named_capabilities": int(v2["workbook_named_total"]),
        "workflows": len([path for path in (ROOT / "workflows").iterdir() if path.is_dir()]),
    }


def _attested_gates() -> dict[str, str]:
    return {
        "bandit_high_severity": "PASS",
        "bounded_performance": "PASS",
        "byte_identical_release_builds": "PASS",
        "complete_regression": "PASS",
        "coverage_line_and_branch": "PASS",
        "critical_mutation_killed": "24/24",
        "dependency_vulnerability_audit": "PASS",
        "deterministic_sbom": "PASS",
        "deterministic_visual_reports": "PASS",
        "docs_build": "PASS",
        "execution_receipts": "PASS",
        "json_schemas_19": "PASS",
        "mypy_strict": "PASS",
        "repository_and_contract_audit": "PASS",
        "reproducibility_capsule": "PASS",
        "reverse_order_regression": "PASS",
        "ruff_format_and_lint": "PASS",
        "scientific_quality_guards": "PASS",
        "seeded_random_order_regression": "PASS",
        "validation_tree_digest": "PASS",
        "wheel_and_sdist_install": "PASS",
    }


def _preflight_gates() -> dict[str, str]:
    return {
        "bandit_high_severity": "NOT_RUN",
        "bounded_performance": "LOCAL_PREFLIGHT",
        "byte_identical_release_builds": "LOCAL_PREFLIGHT",
        "complete_regression": "PARTIAL",
        "coverage_line_and_branch": "LOCAL_PREFLIGHT",
        "critical_mutation_killed": "NOT_RUN",
        "dependency_vulnerability_audit": "NOT_RUN",
        "deterministic_sbom": "PASS",
        "deterministic_visual_reports": "PASS",
        "docs_build": "NOT_RUN",
        "execution_receipts": "LOCAL_PREFLIGHT",
        "json_schemas_19": "PASS",
        "mypy_strict": "NOT_RUN",
        "repository_and_contract_audit": "PASS",
        "reproducibility_capsule": "LOCAL_PREFLIGHT",
        "reverse_order_regression": "NOT_RUN",
        "ruff_format_and_lint": "NOT_RUN",
        "scientific_quality_guards": "PASS",
        "seeded_random_order_regression": "NOT_RUN",
        "validation_tree_digest": "PASS",
        "wheel_and_sdist_install": "NOT_RUN",
    }


def _composite_gates() -> dict[str, str]:
    return {
        "baseline_repository_and_contract_audit": "PASS",
        "baseline_complete_regression": "PASS",
        "baseline_reverse_order_regression": "PASS",
        "baseline_seeded_random_order_regression": "PASS",
        "baseline_ruff_format_and_lint": "PASS",
        "baseline_mypy_strict": "PASS",
        "baseline_bandit_high_severity": "PASS",
        "baseline_critical_mutation_killed": "24/24",
        "baseline_bounded_performance": "PASS",
        "baseline_byte_identical_release_builds": "PASS",
        "scientific_quality_guard_regression": "PASS",
        "deterministic_visual_report_contract": "PASS",
        "readme_version_and_mirror_alignment": "PASS",
        "focused_current_change_regression": "PASS",
        "current_end_to_end_ci": "NOT_RUN",
    }


def _validate_composite_inputs(baseline: dict[str, Any], focused: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    commit = baseline.get("commit")
    if baseline.get("status") != "PASS" or not isinstance(commit, str) or not SHA40.fullmatch(commit):
        errors.append("composite baseline must be a PASS record with a 40-character commit SHA")
    if not isinstance(baseline.get("workflow_run_id"), int) or baseline.get("workflow_run_id", 0) < 1:
        errors.append("composite baseline must record a positive workflow run id")
    baseline_digest = baseline.get("validation_tree_sha256")
    if not isinstance(baseline_digest, str) or not SHA64.fullmatch(baseline_digest):
        errors.append("composite baseline must record a validation tree SHA-256")
    if not isinstance(baseline.get("validated_file_count"), int) or baseline.get("validated_file_count", 0) < 1:
        errors.append("composite baseline must record a positive validated file count")
    compatibility = baseline.get("compatibility")
    if not isinstance(compatibility, dict) or not compatibility or any(str(value) != "PASS" for value in compatibility.values()):
        errors.append("composite baseline compatibility matrix must be fully PASS")
    if focused.get("status") != "PASS":
        errors.append("focused current-change regression must be PASS")
    if focused.get("base_commit") != commit:
        errors.append("focused regression base_commit must match the composite baseline commit")
    changed_files = focused.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        errors.append("focused regression must record changed_files")
    else:
        seen: set[str] = set()
        for row in changed_files:
            if not isinstance(row, dict):
                errors.append("focused changed_files entries must be objects")
                continue
            relative = row.get("path")
            digest = row.get("sha256")
            if not isinstance(relative, str) or not relative or relative in seen:
                errors.append("focused changed_files paths must be unique non-empty strings")
                continue
            seen.add(relative)
            if not isinstance(digest, str) or not SHA64.fullmatch(digest):
                errors.append(f"focused changed file has invalid SHA-256: {relative}")
                continue
            path = ROOT / relative
            if path.is_symlink() or not path.is_file():
                errors.append(f"focused changed file is missing or unsafe: {relative}")
            elif _sha256(path) != digest:
                errors.append(f"focused changed file digest is stale: {relative}")
    return errors


def _build_composite(evidence_date: str, baseline_path: Path, focused_path: Path) -> dict[str, Any]:
    baseline = _load_object(baseline_path)
    focused = _load_object(focused_path)
    errors = _validate_composite_inputs(baseline, focused)
    if errors:
        raise ValueError("; ".join(errors))
    compatibility = {str(key): str(value) for key, value in baseline["compatibility"].items()}
    return {
        "schema_version": "1.6",
        "validation_scope": "composite",
        "release": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "status": "PARTIAL",
        "evidence_date": evidence_date or date.today().isoformat(),
        "compatibility": compatibility,
        "compatibility_scope": (
            "Platform results and full-repository quality gates are inherited from the pinned exact-tree "
            "baseline; the current delta is covered by the focused regression record and has not received "
            "a fresh end-to-end current-tree CI attestation."
        ),
        "gates": _composite_gates(),
        "verified_inventory": _inventory(),
        "provenance": {
            "digest_algorithm": "composite baseline tree SHA-256 plus focused changed-file SHA-256 manifest",
            "digest_exclusions": sorted([*EXCLUDED_PATHS, *COVERAGE_RUNTIME_PATTERNS]),
            "evidence_generated_from_commit": None,
            "publication_parent_commit": None,
            "validated_file_count": baseline["validated_file_count"],
            "validated_tree_sha256": baseline["validation_tree_sha256"],
            "dependency_lock_sha256": _sha256(LOCK_FILE),
            "workflow_run_id": None,
            "workflow_run_attempt": None,
            "workflow_job_id": None,
            "external_attestation": f"baseline GitHub Actions run {baseline['workflow_run_id']} plus focused current-change regression",
            "commit_resolution": "pending-external-attestation",
        },
        "workflow": {
            "name": "Composite baseline plus focused current-change regression",
            "run_id": None,
            "attempt": None,
            "source_commit_context": None,
        },
        "interpretation": [
            "The pinned baseline is an exact-tree full-repository software qualification.",
            "The current change is bounded by a SHA-256 manifest and a focused regression record.",
            "Composite evidence does not claim that the current tree received a fresh end-to-end CI run.",
            "Software validation does not establish scientific truth or prove external computation or experiment execution.",
        ],
        "limitations": [
            "Current-tree end-to-end CI remains NOT_RUN for this acceptance hardening delta.",
            "External scientific execution requires a checksum-verifiable execution receipt.",
        ],
        "baseline_full_repository_run": baseline,
        "focused_current_change_regression": focused,
    }


def build(
    source_commit: str = "",
    publication_parent: str = "",
    run_id: int = 0,
    run_attempt: int = 0,
    evidence_date: str = "",
    *,
    job_id: int | None = None,
    attested: bool = False,
    composite: bool = False,
    baseline_path: Path = BASELINE,
    focused_path: Path = FOCUSED,
    existing_path: Path = OUTPUT,
) -> dict[str, Any]:
    """Build preflight, current-tree, or composite validation evidence."""

    if composite:
        if attested:
            raise ValueError("composite and attested evidence modes are mutually exclusive")
        return _build_composite(evidence_date, baseline_path, focused_path)
    if attested:
        if not SHA40.fullmatch(source_commit) or not SHA40.fullmatch(publication_parent):
            raise ValueError("attested evidence requires lowercase 40-character commit SHAs")
        if run_id < 1 or run_attempt < 1:
            raise ValueError("attested evidence requires positive workflow run id and attempt")
    digest, file_count = tree_digest()
    current = _load_object(existing_path)
    date_value = evidence_date or date.today().isoformat()
    if attested:
        scope = "current-tree"
        status = "PASS"
        gates = _attested_gates()
        compatibility_scope = (
            "The compatibility matrix completed before the dependent full-validation job and is bound "
            "to the exact commit by the external CI attestation."
        )
        commit_resolution = "external-attestation"
        external_attestation = "artifacts/publication-attestation.json"
        workflow_name = "Main-branch full integration audit"
        interpretation = [
            "The source-tree digest is authoritative for the checked repository content.",
            "A commit cannot safely contain its own SHA; the exact tested commit is linked by an external CI attestation.",
            "Generated evidence, dashboards, the PDF report, quality history and aggregate checksum are excluded from the non-self-referential digest.",
            "Software validation does not imply scientific acceptance of external calculations, experiments, medical claims, legal conclusions or safety decisions.",
        ]
    else:
        scope = "preflight"
        status = "PARTIAL"
        gates = _preflight_gates()
        compatibility_scope = (
            "Recorded compatibility results are a prior release baseline. CI-only gates for this source tree "
            "remain explicitly NOT_RUN or PARTIAL until an external attestation is created."
        )
        commit_resolution = "pending-external-attestation"
        external_attestation = "NOT_AVAILABLE_UNTIL_CI_COMPLETES"
        workflow_name = "Local preflight and generated-artifact audit"
        interpretation = [
            "This checked-in record is intentionally PARTIAL and must not be interpreted as a completed CI run.",
            "The source-tree digest records the candidate content before external CI attestation.",
            "CI-only gates remain NOT_RUN or PARTIAL until GitHub Actions produces artifacts/VALIDATION_EVIDENCE.json and publication-attestation.json.",
            "Software checks do not grant scientific acceptance of external calculations or experiments.",
        ]
    return {
        "schema_version": "1.6",
        "validation_scope": scope,
        "release": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "status": status,
        "evidence_date": date_value,
        "compatibility": _compatibility(current),
        "compatibility_scope": compatibility_scope,
        "gates": gates,
        "verified_inventory": _inventory(),
        "provenance": {
            "digest_algorithm": "sha256(path\\0sha256(file)\\n)",
            "digest_exclusions": sorted([*EXCLUDED_PATHS, *COVERAGE_RUNTIME_PATTERNS]),
            "evidence_generated_from_commit": source_commit if attested else None,
            "publication_parent_commit": publication_parent if attested else None,
            "validated_file_count": file_count,
            "validated_tree_sha256": digest,
            "dependency_lock_sha256": _sha256(LOCK_FILE),
            "workflow_run_id": run_id if attested else None,
            "workflow_run_attempt": run_attempt if attested else None,
            "workflow_job_id": job_id if attested else None,
            "external_attestation": external_attestation,
            "commit_resolution": commit_resolution,
        },
        "workflow": {
            "name": workflow_name,
            "run_id": run_id if attested else None,
            "attempt": run_attempt if attested else None,
            "source_commit_context": source_commit if attested else None,
        },
        "interpretation": interpretation,
        "limitations": [
            "Checked-in preflight evidence is not a substitute for the external CI attestation.",
            "External scientific execution requires a checksum-verifiable execution receipt.",
        ],
    }


def validate(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8", errors="strict"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.path) or "root"
        errors.append(f"{location}: {error.message}")
    if value.get("release") != (ROOT / "VERSION").read_text(encoding="utf-8").strip():
        errors.append("release must match VERSION")
    scope = value.get("validation_scope")
    provenance = value.get("provenance")
    if isinstance(provenance, dict):
        actual_lock = provenance.get("dependency_lock_sha256")
        expected_lock = _sha256(LOCK_FILE)
        if actual_lock != expected_lock:
            errors.append(
                f"dependency_lock_sha256 is stale (checked-in={actual_lock}, expected={expected_lock})",
            )
        if scope != "composite":
            expected_digest, expected_count = tree_digest()
            actual_digest = provenance.get("validated_tree_sha256")
            actual_count = provenance.get("validated_file_count")
            if actual_digest != expected_digest:
                errors.append(
                    f"validated_tree_sha256 is stale (checked-in={actual_digest}, expected={expected_digest})",
                )
            if actual_count != expected_count:
                errors.append(
                    f"validated_file_count is stale (checked-in={actual_count}, expected={expected_count})",
                )
    gates = value.get("gates")
    if scope == "current-tree":
        if value.get("status") != "PASS":
            errors.append("current-tree validation status must be PASS")
        if not isinstance(gates, dict) or any(gates.get(key) != "PASS" for key in REQUIRED_CURRENT_GATES):
            errors.append("current-tree validation gates are missing or not PASS")
        if isinstance(provenance, dict) and provenance.get("commit_resolution") != "external-attestation":
            errors.append("current-tree evidence requires external-attestation resolution")
    elif scope == "preflight":
        if value.get("status") != "PARTIAL":
            errors.append("preflight validation status must be PARTIAL")
        if isinstance(gates, dict) and any(gates.get(key) == "PASS" for key in CI_ONLY_GATES):
            errors.append("preflight evidence cannot mark CI-only gates PASS")
        if isinstance(provenance, dict):
            if provenance.get("commit_resolution") != "pending-external-attestation":
                errors.append("preflight evidence must await external attestation")
            if provenance.get("workflow_run_id") is not None:
                errors.append("preflight evidence cannot claim a workflow run id")
    elif scope == "composite":
        baseline = value.get("baseline_full_repository_run")
        focused = value.get("focused_current_change_regression")
        if not isinstance(baseline, dict) or not isinstance(focused, dict):
            errors.append("composite evidence requires baseline and focused regression records")
        else:
            errors.extend(_validate_composite_inputs(baseline, focused))
            if isinstance(provenance, dict):
                if provenance.get("validated_tree_sha256") != baseline.get("validation_tree_sha256"):
                    errors.append("composite provenance tree digest must match the pinned baseline")
                if provenance.get("validated_file_count") != baseline.get("validated_file_count"):
                    errors.append("composite provenance file count must match the pinned baseline")
                if provenance.get("commit_resolution") != "pending-external-attestation":
                    errors.append("composite evidence must remain pending current-tree external attestation")
                if provenance.get("workflow_run_id") is not None:
                    errors.append("composite evidence cannot claim a current-tree workflow run id")
        if value.get("status") != "PARTIAL":
            errors.append("composite validation status must be PARTIAL")
        if not isinstance(gates, dict) or gates.get("focused_current_change_regression") != "PASS":
            errors.append("composite focused current-change gate must be PASS")
        if isinstance(gates, dict) and gates.get("current_end_to_end_ci") != "NOT_RUN":
            errors.append("composite current_end_to_end_ci must remain NOT_RUN")
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True).casefold()
    if "simulated permanent" in serialized or "permanent_tree_simulated" in serialized:
        errors.append("simulated permanent-tree markers are forbidden")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--preflight", action="store_true")
    scope.add_argument("--attested", action="store_true")
    scope.add_argument("--composite", action="store_true")
    parser.add_argument("--baseline", default=str(BASELINE))
    parser.add_argument("--focused", default=str(FOCUSED))
    parser.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--publication-parent", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--run-id", type=int, default=int(os.environ.get("GITHUB_RUN_ID", "0")))
    parser.add_argument("--run-attempt", type=int, default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "0")))
    parser.add_argument("--job-id", type=int)
    parser.add_argument("--evidence-date", default=date.today().isoformat())
    parser.add_argument("--out", default=str(OUTPUT))
    args = parser.parse_args()
    output = Path(args.out)
    if args.write:
        value = build(
            args.source_commit,
            args.publication_parent,
            args.run_id,
            args.run_attempt,
            args.evidence_date,
            job_id=args.job_id,
            attested=args.attested,
            composite=args.composite,
            baseline_path=Path(args.baseline),
            focused_path=Path(args.focused),
            existing_path=output if output.is_file() else OUTPUT,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {output}: {value['validation_scope']} {value['provenance']['validated_tree_sha256']}")
        return
    value = _load_object(output)
    errors = validate(value)
    if errors:
        raise SystemExit("validation evidence FAIL: " + "; ".join(errors))
    print(f"validation evidence PASS ({value['validation_scope']})")


if __name__ == "__main__":
    main()
