#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import json
import zipfile
from email.parser import Parser
from pathlib import Path

from tsao import __version__

_REQUIRED = {
    "tsao/process_package.py",
    "tsao/skillpacks.py",
    "tsao/data/process_package.schema.json",
    "skills/epdm/__init__.py",
    "skills/epdm/SKILL.md",
    "skills/epdm/STATUS.md",
    "skills/epdm/core.py",
    "skills/epdm/batch.py",
    "skills/epdm/kinetics.py",
    "skills/epdm/process.py",
    "skills/epdm/qualification.py",
    "skills/epdm/package_audit.py",
    "skills/epdm/contracts.py",
    "skills/epdm/registry.py",
    "skills/epdm/qualification_v2.py",
    "skills/epdm/validation_v2.py",
    "skills/epdm/migration.py",
    "skills/epdm/state_generator.py",
    "skills/epdm/reaction_network.py",
    "skills/epdm/executable_rhs.py",
    "skills/epdm/numerical_integration.py",
    "skills/epdm/data/module_contracts.json",
    "skills/epdm/data/requirements.json",
    "skills/epdm/data/module_contracts_v2.json",
    "skills/epdm/data/requirements_v2.json",
    "skills/epdm/data/reaction_class_catalog_v2.json",
    "skills/epdm/data/state_variable_catalog_v2.json",
    "skills/epdm/fixtures/reference_cases.json",
    "skills/epdm/fixtures/v2_phase_a1_reference_project.json",
    "skills/epdm/fixtures/v2_phase_a2_reference_state.json",
    "skills/epdm/fixtures/v2_phase_a2_reference_network.json",
    "skills/epdm/fixtures/v2_phase_a2_reference_project.json",
    "skills/epdm/fixtures/v2_phase_a3_reference_rate_package.json",
    "skills/epdm/fixtures/v2_phase_a4_reference_integration_request.json",
    "skills/epdm/schemas/epdm_case.schema.json",
    "skills/epdm/schemas/epdm_package.schema.json",
    "skills/epdm/schemas/epdm-project-v2.schema.json",
    "skills/epdm/schemas/epdm-case-v2.schema.json",
    "skills/epdm/schemas/generated-state-definition.schema.json",
    "skills/epdm/schemas/reaction-network-v2.schema.json",
    "skills/epdm/schemas/rate-package-a3.schema.json",
    "skills/epdm/schemas/integration-request-a15.schema.json",
    "skills/epdm/schemas/integration-result-a15.schema.json",
    "skills/epdm/docs/PHASE_A1_CONTRACTS.md",
    "skills/epdm/docs/PHASE_A2_REACTION_NETWORK.md",
    "skills/epdm/docs/PHASE_A3_EXECUTABLE_RHS.md",
    "skills/epdm/docs/PHASE_A4_NUMERICAL_INTEGRATION.md",
    "skills/poe/__init__.py",
    "skills/poe/SKILL.md",
    "skills/poe/ARCHITECTURE.md",
    "skills/poe/STATUS.md",
    "skills/poe/core.py",
    "skills/poe/governance.py",
    "skills/poe/kinetics.py",
    "skills/poe/qualification.py",
    "skills/poe/package_audit.py",
    "skills/poe/estimation.py",
    "skills/poe/reactors.py",
    "skills/poe/dynamics.py",
    "skills/poe/properties.py",
    "skills/poe/scaleup.py",
    "skills/poe/model_passport.py",
    "skills/poe/data/model_asset_passports.json",
    "skills/poe/schemas/model_asset_passport.schema.json",
    "skills/poe/scripts/audit_p1.py",
    "skills/poe/data/source_asset_registry.json",
    "skills/poe/data/requirement_trace.json",
    "skills/poe/data/conflict_ledger.json",
    "skills/poe/fixtures/scientific_fixtures.json",
    "skills/poe/schemas/asset_registry.schema.json",
    "skills/poe/schemas/requirement_trace.schema.json",
    "skills/poe/schemas/conflict_ledger.schema.json",
    "skills/poe/schemas/property_method.schema.json",
    "skills/poe/schemas/process_case.schema.json",
    "skills/poe/schemas/package_manifest.schema.json",
}
_POE_MODULES = (
    "01_product_cqa",
    "02_catalyst_impurity",
    "03_kinetics_network",
    "04_parameter_estimation",
    "05_thermodynamics_properties",
    "06_rheology_transport",
    "07_reactor_cfd_heat_removal",
    "08_steady_flowsheet_balances",
    "09_devolatilization_finishing",
    "10_recovery_recycle_purge",
    "11_dynamics_control_transitions",
    "12_scaleup_package_acceptance",
)
_PROCESS_MODULES = (
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
_PROCESS_WORKFLOWS = (
    "00_one_shot_orchestrator.md",
    "01_evidence_and_route_selection.md",
    "02_measurement_and_experiment.md",
    "03_models_and_process_synthesis.md",
    "04_scaleup_control_hse.md",
    "05_package_acceptance_transfer.md",
)
_POLYMER_SCRIPTS = (
    "audit_evidence.py",
    "check_balance.py",
    "common.py",
    "generate_doe.py",
    "generate_master_plan.py",
    "scaleup_numbers.py",
)
_README_ASSETS = (
    "model-risk-governance.svg",
    "process-knowledge-graph.svg",
    "autonomous-experiment-loop.svg",
    "law-to-grade-inverse-design.svg",
    "uncertainty-decision-landscape.svg",
    "agentic-qualification-orchestrator.svg",
    "multiscale-digital-thread.svg",
    "ai-scientific-reasoning-loop.svg",
    "batch-parameter-scan.svg",
    "control-safety-cause-effect.svg",
    "dependency-lock-supply-chain.svg",
    "epdm-catalyst-kinetics-network.svg",
    "epdm-identifiability-uncertainty.svg",
    "epdm-multiscale-chain.svg",
    "epdm-process-flowsheet.svg",
    "epdm-product-customer-bridge.svg",
    "epdm-reactor-mode-map.svg",
    "epdm-three-level-models.svg",
    "evidence-gate-system.svg",
    "main-only-delivery-lifecycle.svg",
    "performance-regression-gate.svg",
    "process-package-architecture.svg",
    "process-package-data-model.svg",
    "recovery-recycle-risk-loop.svg",
    "simulation-integration-contract.svg",
    "source-snapshot-self-validation.svg",
    "tsao-process-intelligence-os.svg",
    "universal-process-package.svg",
    "verification-pipeline.svg",
)
_MAINTENANCE_SCRIPTS = (
    "audit_capabilities.py",
    "benchmark_performance.py",
    "benchmark_performance_v2.py",
    "build_source_asset_manifest.py",
    "compare_performance.py",
    "compare_performance_v2.py",
    "export_source_snapshot.py",
    "generate_decision_readme_assets.py",
    "generate_extended_readme_assets.py",
    "generate_performance_readme_assets.py",
    "generate_readme_assets.py",
    "generate_uiux_readme_assets.py",
    "harden_readme_svg_accessibility.py",
    "run_ci.py",
    "sync_readme_visuals.py",
    "update_performance_readme.py",
    "update_source_overlay.py",
    "verify_dependency_lock.py",
    "verify_readme_visual_accessibility.py",
    "verify_wheel_contents.py",
    "verify_wheel_runtime.py",
)
_SHARE_ROOT = "share/tsao-processing-skill"
_EXPECTED_DIST_NAME = "tsao-processing-skill"
_EXPECTED_PEP440_VERSION = __version__.replace("-alpha.", "a")
_EXPECTED_CONSOLE_SCRIPTS = {
    "tsao": "tsao.cli:main",
    "tsao-skillpacks": "tsao.skillpacks:main",
}


def _choose_wheel(wheel: Path | None, wheel_dir: Path | None) -> Path:
    if wheel is not None:
        if not wheel.is_file():
            raise ValueError(f"wheel does not exist: {wheel}")
        return wheel
    if wheel_dir is None or not wheel_dir.is_dir():
        raise ValueError("--wheel or a valid --wheel-dir is required")
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"expected exactly one wheel in {wheel_dir}, found {len(wheels)}")
    return wheels[0]


def _relative_share_members(names: set[str]) -> set[str]:
    """Index installed Skillpack members once relative to the shared-data root."""
    marker = f"{_SHARE_ROOT}/"
    relative: set[str] = set()
    for name in names:
        position = name.find(marker)
        if position >= 0:
            relative.add(name[position:])
    return relative


def _unique_dist_info_member(
    names: set[str],
    suffix: str,
    *,
    label: str,
    errors: list[str],
) -> str | None:
    matches = sorted(name for name in names if name.endswith(f".dist-info/{suffix}"))
    if len(matches) != 1:
        errors.append(f"expected exactly one Wheel {label}, found {len(matches)}")
        return None
    return matches[0]


def _verify_wheel_identity(
    archive: zipfile.ZipFile,
    wheel: Path,
    names: set[str],
    errors: list[str],
) -> dict[str, object]:
    identity: dict[str, object] = {
        "expected_name": _EXPECTED_DIST_NAME,
        "expected_version": _EXPECTED_PEP440_VERSION,
        "console_scripts": {},
    }
    if f"-{_EXPECTED_PEP440_VERSION}-" not in wheel.name:
        errors.append(
            f"wheel filename version mismatch: expected {_EXPECTED_PEP440_VERSION} in {wheel.name}"
        )

    metadata_member = _unique_dist_info_member(
        names,
        "METADATA",
        label="METADATA member",
        errors=errors,
    )
    if metadata_member is not None:
        try:
            metadata = Parser().parsestr(archive.read(metadata_member).decode("utf-8"))
        except (KeyError, UnicodeDecodeError) as exc:
            errors.append(f"could not read Wheel METADATA: {exc}")
        else:
            actual_name = (metadata.get("Name") or "").casefold().replace("_", "-")
            actual_version = metadata.get("Version") or ""
            identity["metadata_name"] = actual_name
            identity["metadata_version"] = actual_version
            if actual_name != _EXPECTED_DIST_NAME:
                errors.append(
                    "wheel metadata name mismatch: "
                    f"expected {_EXPECTED_DIST_NAME}, found {actual_name or '<missing>'}"
                )
            if actual_version != _EXPECTED_PEP440_VERSION:
                errors.append(
                    "wheel metadata version mismatch: "
                    f"expected {_EXPECTED_PEP440_VERSION}, found {actual_version or '<missing>'}"
                )

    entry_member = _unique_dist_info_member(
        names,
        "entry_points.txt",
        label="entry_points.txt member",
        errors=errors,
    )
    scripts: dict[str, str] = {}
    if entry_member is not None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        try:
            parser.read_string(archive.read(entry_member).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, configparser.Error) as exc:
            errors.append(f"could not read Wheel entry points: {exc}")
        else:
            if parser.has_section("console_scripts"):
                scripts = dict(parser.items("console_scripts"))
    identity["console_scripts"] = scripts
    for name, target in _EXPECTED_CONSOLE_SCRIPTS.items():
        if name not in scripts:
            errors.append(f"missing wheel console script: {name}")
        elif scripts[name] != target:
            errors.append(
                f"wheel console script mismatch for {name}: "
                f"expected {target}, found {scripts[name]}"
            )
    return identity


def verify(wheel: Path) -> dict[str, object]:
    errors: list[str] = []
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        identity = _verify_wheel_identity(archive, wheel, names, errors)
    missing = sorted(_REQUIRED - names)
    errors.extend(f"missing wheel member: {name}" for name in missing)
    for index in range(1, 13):
        shard = f"skills/poe/data/source_asset_registry.part{index:02d}.json"
        if shard not in names:
            errors.append(f"missing wheel member: {shard}")
    for module in _POE_MODULES:
        for filename in ("README.md", "contract.schema.json"):
            member = f"skills/poe/modules/{module}/{filename}"
            if member not in names:
                errors.append(f"missing wheel member: {member}")

    share_required = {
        f"{_SHARE_ROOT}/SKILL.md",
        f"{_SHARE_ROOT}/manifest.yaml",
        f"{_SHARE_ROOT}/README.md",
        f"{_SHARE_ROOT}/README.zh-CN.md",
        f"{_SHARE_ROOT}/pyproject.toml",
        f"{_SHARE_ROOT}/docs/CAPABILITY_MATRIX.md",
        f"{_SHARE_ROOT}/docs/README_VISUAL_SYSTEM.md",
        f"{_SHARE_ROOT}/reports/QUALIFICATION_BOUNDARY.md",
        f"{_SHARE_ROOT}/reports/BRANCH_CONSOLIDATION_2026-07-23.md",
        f"{_SHARE_ROOT}/reports/FINAL_AUDIT_REPORT.md",
        f"{_SHARE_ROOT}/reports/RELEASE_IDENTITY.json",
        f"{_SHARE_ROOT}/reports/ALPHA11_SOURCE_CORE_STATUS.json",
        f"{_SHARE_ROOT}/reports/ALPHA11_FINAL_QUALIFICATION.json",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_BASELINE_ALPHA10_EXTENDED.json",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_OPTIMIZED_ALPHA11.json",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_COMPARISON_ALPHA11.json",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_TECHNOLOGY_REVIEW.md",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_OPTIMIZATION_PLAN.md",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_BASELINE_ALPHA9.json",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_OPTIMIZED_ALPHA10.json",
        f"{_SHARE_ROOT}/reports/PERFORMANCE_COMPARISON_ALPHA10.json",
        f"{_SHARE_ROOT}/reports/COMPLETE_DISTRIBUTION_REFERENCE.json",
        f"{_SHARE_ROOT}/reports/SOURCE_CORE_MANIFEST.tsv",
        f"{_SHARE_ROOT}/reports/SOURCE_CORE_OVERLAY.tsv",
        f"{_SHARE_ROOT}/reports/ALPHA12_ZERO_FALSE_PASS_QUALIFICATION.json",
        f"{_SHARE_ROOT}/reports/ALPHA13_NUMERICAL_CORRECTNESS_QUALIFICATION.json",
        f"{_SHARE_ROOT}/reports/EPDM_PHASE_A3_QUALIFICATION.json",
        f"{_SHARE_ROOT}/reports/EPDM_PHASE_A4_QUALIFICATION.json",
        f"{_SHARE_ROOT}/schemas/project.schema.json",
        f"{_SHARE_ROOT}/templates/README.md",
        f"{_SHARE_ROOT}/examples/generic-process/brief.yaml",
        f"{_SHARE_ROOT}/skills/process-general/SKILL.md",
        f"{_SHARE_ROOT}/skills/process-general/manifest.yaml",
        f"{_SHARE_ROOT}/skills/epdm/SKILL.md",
        f"{_SHARE_ROOT}/skills/epdm/data/requirements_v2.json",
        f"{_SHARE_ROOT}/skills/epdm/data/reaction_class_catalog_v2.json",
        f"{_SHARE_ROOT}/skills/epdm/data/state_variable_catalog_v2.json",
        f"{_SHARE_ROOT}/skills/epdm/schemas/generated-state-definition.schema.json",
        f"{_SHARE_ROOT}/skills/epdm/schemas/reaction-network-v2.schema.json",
        f"{_SHARE_ROOT}/skills/epdm/fixtures/v2_phase_a2_reference_project.json",
        f"{_SHARE_ROOT}/skills/epdm/fixtures/v2_phase_a3_reference_rate_package.json",
        f"{_SHARE_ROOT}/skills/epdm/fixtures/v2_phase_a4_reference_integration_request.json",
        f"{_SHARE_ROOT}/skills/epdm/schemas/rate-package-a3.schema.json",
        f"{_SHARE_ROOT}/skills/epdm/schemas/integration-request-a15.schema.json",
        f"{_SHARE_ROOT}/skills/epdm/schemas/integration-result-a15.schema.json",
        f"{_SHARE_ROOT}/skills/epdm/docs/PHASE_A3_EXECUTABLE_RHS.md",
        f"{_SHARE_ROOT}/skills/epdm/docs/PHASE_A4_NUMERICAL_INTEGRATION.md",
        f"{_SHARE_ROOT}/skills/poe/SKILL.md",
        f"{_SHARE_ROOT}/skills/polymer-general/SKILL.md",
    }
    share_required.update(
        f"{_SHARE_ROOT}/skills/process-general/modules/{name}" for name in _PROCESS_MODULES
    )
    share_required.update(
        f"{_SHARE_ROOT}/skills/process-general/workflows/{name}" for name in _PROCESS_WORKFLOWS
    )
    share_required.update(
        f"{_SHARE_ROOT}/skills/polymer-general/scripts/{name}" for name in _POLYMER_SCRIPTS
    )
    share_required.update(f"{_SHARE_ROOT}/docs/assets/readme/{name}" for name in _README_ASSETS)
    share_required.update(f"{_SHARE_ROOT}/scripts/{name}" for name in _MAINTENANCE_SCRIPTS)
    installed_share_members = _relative_share_members(names)
    errors.extend(
        f"missing installed skillpack member: {suffix}"
        for suffix in sorted(share_required - installed_share_members)
    )

    if any(name.startswith("skills/poe/tests/") for name in names):
        errors.append("wheel must not contain POE test sources")
    if any(name.endswith((".apw", ".bkp", ".dynf", ".opju", ".mat")) for name in names):
        errors.append("wheel contains controlled historical binary assets")
    return {
        "wheel": str(wheel),
        "pass": not errors,
        "errors": errors,
        "identity": identity,
        "poe_members": len([name for name in names if name.startswith("skills/poe/")]),
        "epdm_members": len([name for name in names if name.startswith("skills/epdm/")]),
        "poe_module_count": len(_POE_MODULES),
        "process_general_module_count": len(_PROCESS_MODULES),
        "process_general_workflow_count": len(_PROCESS_WORKFLOWS),
        "readme_asset_count": len(_README_ASSETS),
        "maintenance_script_count": len(_MAINTENANCE_SCRIPTS),
        "installed_skillpack_members": len(installed_share_members),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--wheel-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(_choose_wheel(args.wheel, args.wheel_dir))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        result = {"pass": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
