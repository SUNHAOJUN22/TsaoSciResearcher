from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from ._utils import atomic_write_text, nonempty, required_or_default_string
from .capabilities import build_work_packages, initial_maturity_record
from .gates import (
    ApprovalStatus,
    GateRecord,
    GateStatus,
    validate_gate_events,
    validate_gate_sequence,
)
from .routing import route

PROJECT_DIRS = (
    "00_governance",
    "01_evidence",
    "02_requirements",
    "03_measurement_data",
    "04_chemistry",
    "05_models",
    "06_lab",
    "07_bench",
    "08_separation_recycle",
    "09_pilot",
    "10_demonstration",
    "11_industrial",
    "12_control",
    "13_hse_reliability",
    "14_tea_lca_ip",
    "15_qualification",
    "16_technology_package",
    "17_transfer",
    "18_field_learning",
    "data/raw",
    "data/processed",
    "models",
    "reports",
    "logs",
)
_VALID_SUBSKILLS = {"process-general", "epdm", "poe", "polymer-general"}
_POLYMER_SUBSKILLS = {"epdm", "poe", "polymer-general"}


def _select_subskills(routed: list[tuple[str, float]]) -> list[str]:
    domains = [item[0] for item in routed]
    selected = [domain for domain in domains if domain in _POLYMER_SUBSKILLS]
    if not selected or any(domain not in _POLYMER_SUBSKILLS for domain in domains):
        selected.insert(0, "process-general")
    return list(dict.fromkeys(selected))


def bootstrap_project(
    brief: Path, output: Path, template_root: Path | None = None
) -> dict[str, Any]:
    brief = Path(brief)
    output = Path(output)
    if not brief.is_file():
        raise FileNotFoundError(f"brief file not found: {brief}")
    if output.is_symlink():
        raise ValueError("output path must not be a symlink")
    if output.exists():
        if not output.is_dir():
            raise FileExistsError("output path exists and is not a directory")
        if any(output.iterdir()):
            raise FileExistsError("output directory is not empty")
    text = brief.read_text(encoding="utf-8")
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML brief: {exc}") from exc
    data: Mapping[str, Any]
    if loaded is None:
        data = {}
    elif isinstance(loaded, Mapping):
        data = loaded
    else:
        raise ValueError("brief root must be a YAML mapping")
    project_id = required_or_default_string(data, "project_id", "TSAO-PROJECT")
    title = required_or_default_string(data, "title", "Untitled process project")
    if template_root is not None:
        template_root = Path(template_root)
        if template_root.exists() and not template_root.is_dir():
            raise ValueError("template root must be a directory")
        if template_root.is_symlink():
            raise ValueError("template root must not be a symlink")
        if template_root.exists():
            for path in template_root.rglob("*"):
                if path.is_symlink():
                    raise ValueError(f"template tree contains symlink: {path}")
    output.mkdir(parents=True, exist_ok=True)
    for directory in PROJECT_DIRS:
        (output / directory).mkdir(parents=True, exist_ok=True)
    if template_root and template_root.exists():
        for path in sorted(template_root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(template_root)
                destination = output / "00_governance" / "templates" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
    routed = route(text)
    manifest: dict[str, Any] = {
        "project_id": project_id,
        "title": title,
        "version": __version__,
        "domain": [item[0] for item in routed],
        "subskills": _select_subskills(routed),
        "technical_approval_status": "NOT_EVALUATED",
        "gates": [
            {
                "gate_id": f"G{index}",
                "status": "NOT_EVALUATED",
                "owner": None,
                "evidence_ids": [],
                "approval_status": "NOT_EVALUATED",
                "approver": None,
            }
            for index in range(19)
        ],
    }
    atomic_write_text(
        output / "project_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(output / "brief.yaml", text)
    atomic_write_text(
        output / "00_governance/work_packages.json",
        json.dumps(build_work_packages(project_id), ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(
        output / "00_governance/maturity.json",
        json.dumps(initial_maturity_record(), ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(
        output / "00_governance/execution_status.json",
        json.dumps(
            {
                "artifact_status": "INITIALIZED",
                "technical_approval_status": "NOT_EVALUATED",
                "real_experiment_status": "NOT_EVALUATED",
                "commercial_simulation_status": "NOT_EVALUATED",
                "process_safety_status": "NOT_EVALUATED",
                "customer_qualification_status": "NOT_EVALUATED",
                "industrial_performance_status": "NOT_EVALUATED",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    atomic_write_text(output / "00_governance/gate_events.jsonl", "")
    return manifest


def _load_gate_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        return [], ["missing execution artifact: 00_governance/gate_events.jsonl"]
    events: list[dict[str, Any]] = []
    issues: list[str] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                issues.append(f"gate event line {line_number} must be an object")
            else:
                events.append(value)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(f"invalid gate event ledger: {exc}")
    return events, issues


def audit_project(root: Path, mode: str = "initialization") -> list[str]:
    if mode not in {"initialization", "project", "transition", "release"}:
        raise ValueError("audit mode must be initialization, project, transition or release")
    root = Path(root)
    if not root.exists():
        return ["project root does not exist"]
    if not root.is_dir():
        return ["project root is not a directory"]
    issues: list[str] = []
    if root.is_symlink():
        issues.append("project root must not be a symlink")
    for path in root.rglob("*"):
        if path.is_symlink():
            issues.append(f"project contains symlink: {path.relative_to(root).as_posix()}")
    issues.extend(
        f"missing directory: {directory}"
        for directory in PROJECT_DIRS
        if not (root / directory).is_dir()
    )
    for artifact in (
        "00_governance/work_packages.json",
        "00_governance/maturity.json",
        "00_governance/execution_status.json",
        "00_governance/gate_events.jsonl",
    ):
        if not (root / artifact).is_file():
            issues.append(f"missing execution artifact: {artifact}")

    work_packages_path = root / "00_governance/work_packages.json"
    if work_packages_path.is_file():
        try:
            packages = json.loads(work_packages_path.read_text(encoding="utf-8"))
            if not isinstance(packages, list) or len(packages) != 19 * 14:
                issues.append("work package matrix must contain 266 records")
            elif mode == "initialization" and any(
                item.get("approval_status") != "NOT_EVALUATED" for item in packages
            ):
                issues.append("initialization audit requires fail-closed work packages")
            elif mode != "initialization":
                valid_approvals = {item.value for item in ApprovalStatus}
                for index, item in enumerate(packages):
                    if not isinstance(item, dict):
                        issues.append(f"work package {index} must be an object")
                    elif item.get("approval_status") not in valid_approvals:
                        issues.append(f"work package {index} has invalid approval_status")
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError) as exc:
            issues.append(f"invalid work package matrix: {exc}")

    manifest_path = root / "project_manifest.json"
    if not manifest_path.is_file():
        return sorted(set(issues + ["missing project_manifest.json"]))
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return sorted(set(issues + [f"invalid project manifest: {exc}"]))
    if not isinstance(data, dict):
        return sorted(set(issues + ["project manifest must be an object"]))
    for key in ("project_id", "title", "version"):
        if not nonempty(data.get(key)):
            issues.append(f"manifest field must be a non-empty string: {key}")
    if data.get("version") != __version__:
        issues.append("project manifest version does not match TSAO version")
    domain = data.get("domain")
    if not isinstance(domain, list) or not domain or any(not nonempty(item) for item in domain):
        issues.append("domain must be a non-empty string array")
    subskills = data.get("subskills")
    if (
        not isinstance(subskills, list)
        or not subskills
        or len(subskills) != len(set(subskills))
        or any(item not in _VALID_SUBSKILLS for item in subskills)
    ):
        issues.append("subskills must be unique supported subskill names")
    technical_status = data.get("technical_approval_status")
    if mode == "initialization" and technical_status != "NOT_EVALUATED":
        issues.append("project must not claim technical approval")
    elif technical_status not in {"NOT_EVALUATED", "APPROVED", "REJECTED"}:
        issues.append("project technical_approval_status is invalid")

    raw_gates = data.get("gates")
    gate_records: list[GateRecord] = []
    if not isinstance(raw_gates, list):
        issues.append("gates must be an array")
    else:
        for index, raw_gate in enumerate(raw_gates):
            if not isinstance(raw_gate, dict):
                issues.append(f"gate at index {index} must be an object")
                continue
            try:
                evidence_ids = raw_gate.get("evidence_ids", [])
                if not isinstance(evidence_ids, list):
                    raise TypeError("evidence_ids must be an array")
                gate_records.append(
                    GateRecord(
                        gate_id=raw_gate["gate_id"],
                        status=GateStatus(raw_gate["status"]),
                        owner=raw_gate.get("owner"),
                        evidence_ids=list(evidence_ids),
                        approval_status=ApprovalStatus(raw_gate["approval_status"]),
                        approver=raw_gate.get("approver"),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                issues.append(f"invalid gate at index {index}: {exc}")
        if len(gate_records) == len(raw_gates):
            issues.extend(validate_gate_sequence(gate_records))
        if [gate.gate_id for gate in gate_records] != [f"G{i}" for i in range(19)]:
            issues.append("gate sequence must be ordered G0-G18")
        if mode == "initialization" and any(
            gate.status != GateStatus.NOT_EVALUATED
            or gate.approval_status != ApprovalStatus.NOT_EVALUATED
            for gate in gate_records
        ):
            issues.append("initialization audit requires all gates NOT_EVALUATED")
        if mode == "release" and any(
            gate.status not in {GateStatus.PASS, GateStatus.RETIRED} for gate in gate_records
        ):
            issues.append("release audit requires every gate PASS or RETIRED")

    events, event_issues = _load_gate_events(root / "00_governance/gate_events.jsonl")
    issues.extend(event_issues)
    if mode in {"transition", "release"}:
        issues.extend(validate_gate_events(events))
        if mode == "release" and not events:
            issues.append("release audit requires a non-empty gate event ledger")

    return sorted(set(issues))


def audit_project_initialization(root: Path) -> list[str]:
    return audit_project(root, mode="initialization")


def audit_project_transitions(root: Path) -> list[str]:
    return audit_project(root, mode="transition")


def audit_project_release(root: Path) -> list[str]:
    return audit_project(root, mode="release")
