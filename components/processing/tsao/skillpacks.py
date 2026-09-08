from __future__ import annotations

import argparse
import json
import sysconfig
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path
from typing import Any

import yaml

DISTRIBUTION_NAME = "tsao-processing-skill"
INSTALLED_SHARE = Path("share") / DISTRIBUTION_NAME
EXPECTED_SUBSKILLS = {"process-general", "epdm", "poe", "polymer-general"}
README_ASSET_MINIMUM = 32
PROCESS_MODULES = (
    "01_chemistry_reaction_basis.md",
    "02_measurement_data.md",
    "03_thermodynamics_properties.md",
    "04_reactors_transport.md",
    "05_separation_recycle.md",
    "06_control_operability.md",
    "07_hse_reliability.md",
    "08_scaleup_pilot.md",
    "09_tea_lca_supply.md",
    "10_bioprocess.md",
    "11_electrochemical.md",
    "12_solids_crystallization.md",
    "13_fine_batch.md",
    "14_petrochemical.md",
)
PROCESS_WORKFLOWS = (
    "00_one_shot_orchestrator.md",
    "01_evidence_and_route_selection.md",
    "02_measurement_and_experiment.md",
    "03_models_and_process_synthesis.md",
    "04_scaleup_control_hse.md",
    "05_package_acceptance_transfer.md",
)
POLYMER_SCRIPTS = (
    "audit_evidence.py",
    "check_balance.py",
    "common.py",
    "generate_doe.py",
    "generate_master_plan.py",
    "scaleup_numbers.py",
)


def _valid_root(candidate: Path) -> bool:
    return (candidate / "manifest.yaml").is_file() and (candidate / "SKILL.md").is_file()


def _deduplicate_paths(candidates: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve(strict=False)
        key = str(resolved)
        if key not in seen:
            unique.append(resolved)
            seen.add(key)
    return unique


def _distribution_skillpack_candidates(installed: Distribution) -> list[Path]:
    candidates: list[Path] = []
    skill_marker = (INSTALLED_SHARE / "SKILL.md").as_posix()
    for member in installed.files or ():
        if Path(member).as_posix().endswith(skill_marker):
            candidates.append(Path(installed.locate_file(member)).resolve(strict=False).parent)

    candidates.append(Path(installed.locate_file(INSTALLED_SHARE)))
    data_path = sysconfig.get_path("data")
    if data_path:
        candidates.append(Path(data_path) / INSTALLED_SHARE)
    return _deduplicate_paths(candidates)


def resolve_skillpack_root(root: str | Path | None = None) -> Path:
    if root is not None:
        candidate = Path(root).expanduser().resolve()
        if not _valid_root(candidate):
            raise FileNotFoundError(f"not a TSAO skillpack root: {candidate}")
        return candidate

    source_root = Path(__file__).resolve().parents[1]
    if _valid_root(source_root):
        return source_root

    try:
        installed = distribution(DISTRIBUTION_NAME)
    except PackageNotFoundError as exc:
        raise FileNotFoundError("TSAO skillpack distribution is not installed") from exc

    candidates = _distribution_skillpack_candidates(installed)
    for candidate in candidates:
        if _valid_root(candidate):
            return candidate
    checked = ", ".join(str(candidate) for candidate in candidates) or "no candidates"
    raise FileNotFoundError(f"installed TSAO skillpack root is incomplete; checked: {checked}")


def _present_count(root: Path, relative_paths: tuple[str, ...]) -> int:
    return sum((root / relative).is_file() for relative in relative_paths)


def _missing_files(root: Path, relative_paths: tuple[str, ...]) -> list[str]:
    return [relative for relative in relative_paths if not (root / relative).is_file()]


def _subskill_root(root: Path, path: str) -> Path:
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"subskill path escapes Skillpack root: {path}") from exc
    return candidate


def skillpack_inventory(root: str | Path | None = None) -> dict[str, Any]:
    resolved = resolve_skillpack_root(root)
    manifest = yaml.safe_load((resolved / "manifest.yaml").read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(manifest, dict):
        raise ValueError("manifest.yaml must contain an object")

    subskill_rows = manifest.get("subskills")
    if not isinstance(subskill_rows, list):
        raise ValueError("manifest.yaml subskills must be a list")
    subskills: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(subskill_rows, start=1):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            errors.append(f"invalid subskill row {index}")
            continue
        subskill_id = row["id"]
        if subskill_id in subskills:
            errors.append(f"duplicate subskill id: {subskill_id}")
            continue
        subskills[subskill_id] = row

    missing_subskills = sorted(EXPECTED_SUBSKILLS - set(subskills))
    errors.extend(f"missing subskill manifest entry: {item}" for item in missing_subskills)
    for subskill_id, row in subskills.items():
        path = row.get("path")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"subskill {subskill_id} has no path")
            continue
        try:
            subskill_root = _subskill_root(resolved, path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not (subskill_root / "SKILL.md").is_file():
            errors.append(f"subskill {subskill_id} is missing SKILL.md at {path}")

    module_root = resolved / "skills/process-general/modules"
    workflow_root = resolved / "skills/process-general/workflows"
    polymer_script_root = resolved / "skills/polymer-general/scripts"
    errors.extend(
        f"missing process-general module: {item}"
        for item in _missing_files(module_root, PROCESS_MODULES)
    )
    errors.extend(
        f"missing process-general workflow: {item}"
        for item in _missing_files(workflow_root, PROCESS_WORKFLOWS)
    )
    errors.extend(
        f"missing polymer-general script: {item}"
        for item in _missing_files(polymer_script_root, POLYMER_SCRIPTS)
    )

    readme_assets = sorted((resolved / "docs/assets/readme").glob("*.svg"))
    if len(readme_assets) < README_ASSET_MINIMUM:
        errors.append(
            f"expected at least {README_ASSET_MINIMUM} README SVG assets, "
            f"found {len(readme_assets)}"
        )

    return {
        "pass": not errors,
        "root": str(resolved),
        "delivery": "SOURCE_CHECKOUT"
        if resolved == Path(__file__).resolve().parents[1]
        else "INSTALLED_SKILLPACK",
        "version": manifest.get("version"),
        "subskills": sorted(subskills),
        "process_general_modules_present": _present_count(module_root, PROCESS_MODULES),
        "process_general_modules_expected": len(PROCESS_MODULES),
        "process_general_workflows_present": _present_count(workflow_root, PROCESS_WORKFLOWS),
        "process_general_workflows_expected": len(PROCESS_WORKFLOWS),
        "polymer_general_scripts_present": _present_count(polymer_script_root, POLYMER_SCRIPTS),
        "polymer_general_scripts_expected": len(POLYMER_SCRIPTS),
        "readme_svg_assets": len(readme_assets),
        "readme_svg_assets_expected_minimum": README_ASSET_MINIMUM,
        "errors": errors,
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tsao-skillpacks")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    try:
        result = skillpack_inventory(args.root)
    except (OSError, TypeError, ValueError) as exc:
        result = {"pass": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
