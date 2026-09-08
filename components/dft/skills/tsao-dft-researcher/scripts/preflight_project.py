#!/usr/bin/env python3
"""Preflight a TsaoDFT project before expensive calculation or publication work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import load_yaml, print_result  # noqa: E402 -- script-local import follows an explicit sys.path setup
from validate_figure_manifest import (  # noqa: E402 -- local validator import follows SCRIPT_DIR path setup
    validate_manifest as validate_figure_manifest,
)
from validate_research_manifest import (  # noqa: E402 -- local validator import follows SCRIPT_DIR path setup
    validate_manifest as validate_research_manifest,
)

VALID_STATUSES = {
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Promote unresolved scientific fields to failures")
    return parser.parse_args()


def find_cycle(tasks: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> list[str] | None:
        if node in visiting:
            idx = stack.index(node) if node in stack else 0
            return [*stack[idx:], node]
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for dep in tasks.get(node, []):
            cycle = visit(dep, stack)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in tasks:
        cycle = visit(node, [])
        if cycle:
            return cycle
    return None


def _unknown(value: Any) -> bool:
    return value in (None, "", "unknown", "UNKNOWN", "TBD", "tbd")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


def _load_yaml_mapping(path: Path, label: str, failures: list[str]) -> dict[str, Any] | None:
    try:
        return load_yaml(path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        failures.append(f"{label} parse failed: {exc}")
        return None


def main() -> int:
    args = parse_args()
    root = args.project_dir.resolve()
    failures: list[str] = []
    warnings: list[str] = []

    project_path = root / ".research/project.yaml"
    passport_path = root / "calculation-passport.yaml"
    if not project_path.exists():
        failures.append("missing .research/project.yaml")
    if not passport_path.exists():
        failures.append("missing calculation-passport.yaml")
    if failures:
        print_result({"ok": False, "failures": failures, "warnings": warnings}, args.json)
        return 1

    project = _load_yaml_mapping(project_path, ".research/project.yaml", failures)
    passport = _load_yaml_mapping(passport_path, "calculation-passport.yaml", failures)
    if project is None or passport is None:
        print_result({"ok": False, "failures": failures, "warnings": warnings}, args.json)
        return 1

    required = [
        "project_id",
        "name",
        "status",
        "research_question",
        "objective",
        "observable",
        "model_system",
        "method_fingerprint",
        "success_criteria",
        "execution",
    ]
    for key in required:
        if key not in project:
            failures.append(f"project missing required field: {key}")
    if project.get("status") not in VALID_STATUSES:
        failures.append(f"invalid project status: {project.get('status')}")
    if passport.get("project_id") != project.get("project_id"):
        failures.append("calculation passport project_id does not match project.yaml")

    unresolved: list[str] = []
    for key in ["research_question", "objective", "observable"]:
        if _unknown(project.get(key)):
            unresolved.append(key)
    for section, keys in {
        "model_system": [
            "identity",
            "charge",
            "multiplicity",
            "electronic_state",
            "phase_or_solvent",
            "conformer_scope",
        ],
        "method_fingerprint": [
            "code",
            "code_version",
            "functional_or_method",
            "basis_or_ecp",
            "temperature_K",
            "standard_state",
        ],
        "execution": [
            "target",
            "task_count_estimate",
            "cpu_assumption",
            "memory_assumption",
            "disk_assumption",
            "wall_time_estimate",
        ],
    }.items():
        value = project.get(section, {})
        if not isinstance(value, dict):
            failures.append(f"{section} must be a mapping")
            continue
        for key in keys:
            if _unknown(value.get(key)):
                unresolved.append(f"{section}.{key}")
    if unresolved:
        message = "unresolved scientific/execution fields: " + ", ".join(unresolved)
        (failures if args.strict else warnings).append(message)

    execution = project.get("execution", {}) if isinstance(project.get("execution"), dict) else {}
    if execution.get("dry_run_default") is not True:
        warnings.append("execution.dry_run_default should normally be true")
    if execution.get("approval_required") is not True:
        warnings.append("execution.approval_required should be true for production work")

    task_dir = root / ".research/tasks"
    task_files = sorted(task_dir.glob("*.yaml")) if task_dir.exists() else []
    if not task_files:
        failures.append("no task manifests in .research/tasks")
    tasks: dict[str, list[str]] = {}
    ready_without_approval: list[str] = []
    for path in task_files:
        task = _load_yaml_mapping(path, f"task {path.name}", failures)
        if task is None:
            continue
        tid = task.get("task_id")
        if not isinstance(tid, str) or not tid.strip():
            failures.append(f"{path.name}: missing or invalid task_id")
            continue
        if tid in tasks:
            failures.append(f"duplicate task_id: {tid}")
        status = task.get("status")
        if status not in VALID_STATUSES:
            failures.append(f"{tid}: invalid status {status}")
        deps = task.get("depends_on", [])
        if not isinstance(deps, list):
            failures.append(f"{tid}: depends_on must be a list")
            deps = []
        valid_deps: list[str] = []
        for index, dependency in enumerate(deps):
            if not isinstance(dependency, str) or not dependency.strip():
                failures.append(f"{tid}: depends_on[{index}] must be a non-empty task_id")
            else:
                valid_deps.append(dependency)
        tasks[tid] = valid_deps
        approval = task.get("approval", {}) if isinstance(task.get("approval"), dict) else {}
        if status in {"ready", "running"} and approval.get("required") is True and approval.get("status") != "approved":
            ready_without_approval.append(tid)
    for tid, deps in tasks.items():
        for dep in deps:
            if dep not in tasks:
                failures.append(f"{tid}: unknown dependency {dep}")
    cycle = find_cycle(tasks)
    if cycle:
        failures.append("task dependency cycle: " + " -> ".join(cycle))
    if ready_without_approval:
        failures.append("tasks require approval before ready/running: " + ", ".join(ready_without_approval))

    required_dirs = [
        "00_input",
        "01_structures",
        "02_calculations",
        "03_wavefunctions",
        "04_analysis",
        "05_figures",
        "06_tables",
        "07_reports",
        "08_logs",
        "09_provenance",
        "10_source_data",
    ]
    for rel in required_dirs:
        if not (root / rel).exists():
            warnings.append(f"recommended directory missing: {rel}")

    manifests_dir = root / ".research/manifests"
    research_path = manifests_dir / "research-manifest.json"
    figure_path = manifests_dir / "figure-manifest.json"
    research_data: dict[str, Any] | None = None
    if research_path.exists():
        try:
            research_data = _load_json(research_path)
            manifest_errors, manifest_warnings = validate_research_manifest(research_data)
            failures.extend(f"research manifest: {item}" for item in manifest_errors)
            warnings.extend(f"research manifest: {item}" for item in manifest_warnings)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"research manifest parse failed: {exc}")
    else:
        warnings.append("research manifest not initialized")
    if figure_path.exists():
        try:
            figure_data = _load_json(figure_path)
            figure_errors, figure_warnings = validate_figure_manifest(
                figure_data, figure_path.parent, research_data, False
            )
            failures.extend(f"figure manifest: {item}" for item in figure_errors)
            warnings.extend(f"figure manifest: {item}" for item in figure_warnings)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"figure manifest parse failed: {exc}")
    else:
        warnings.append("figure manifest not initialized")

    success_criteria = project.get("success_criteria")
    criteria_ready = isinstance(success_criteria, list) and bool(success_criteria)
    if not criteria_ready:
        warnings.append("success_criteria is empty")

    result = {
        "ok": not failures,
        "project": str(root),
        "task_count": len(tasks),
        "unresolved_fields": unresolved,
        "failures": failures,
        "warnings": warnings,
        "execution_ready": not failures and not unresolved and criteria_ready,
        "publication_ready": not failures and not unresolved and criteria_ready and project.get("status") == "accepted",
    }
    print_result(result, args.json)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
