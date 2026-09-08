from __future__ import annotations

from pathlib import Path
from typing import Any

GATES = tuple(f"G{index}" for index in range(19))
MATURITY_LEVELS = (
    "M0 idea",
    "M1 evidence-framed",
    "M2 chemistry-proven",
    "M3 laboratory-process-proven",
    "M4 bench-integrated",
    "M5 pilot-ready",
    "M6 pilot-proven",
    "M7 demo-proven",
    "M8 industrial-ready",
    "M9 operationally-validated",
)
WORKSTREAMS = (
    ("governance", "Governance and decision rights", "Research Director"),
    ("evidence-ip", "Evidence, standards, patents and research graph", "Evidence Lead"),
    ("product-quality", "Product, application, CQA and customer needs", "Product Lead"),
    ("chemistry", "Raw materials, catalysts, impurities and chemistry", "Chemistry Lead"),
    ("analytics-data", "Sampling, analytical methods and data systems", "Analytical/Data Lead"),
    ("statistics-doe", "DoE, statistics, inference and uncertainty", "Statistician/DoE Lead"),
    (
        "kinetics-properties",
        "Mechanism, kinetics, properties and distributions",
        "Property/Kinetics Modeler",
    ),
    (
        "reactor-multiphysics",
        "Reactors, transport and multiphysics",
        "Reactor/Multiphysics Lead",
    ),
    (
        "process-synthesis",
        "Separation, recycle, utilities and process synthesis",
        "Process Systems Lead",
    ),
    (
        "scaleup-pilot",
        "Lab, bench, pilot, demonstration and scale-up",
        "Scale-up/Pilot Lead",
    ),
    (
        "control-operations",
        "Steady state, dynamics, control and operations",
        "Control/Operations Lead",
    ),
    (
        "hse-reliability",
        "Safety, environment, reliability and integrity",
        "HSE/Reliability Lead",
    ),
    (
        "tea-supply-ip",
        "Economics, lifecycle, supply chain and IP interface",
        "TEA/Supply/IP Lead",
    ),
    (
        "reporting-transfer",
        "Reports, process package, acceptance and transfer",
        "Package Publisher",
    ),
)
SUBSKILLS = ("process-general", "epdm", "poe", "polymer-general")
POE_MODULES = (
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
UNIVERSAL_PACKAGE_REQUIRED_ARTIFACTS = (
    "tsao/process_package.py",
    "tsao/data/process_package.schema.json",
    "skills/process-general/PACKAGE_PLATFORM.md",
)
EPDM_REQUIRED_ARTIFACTS = (
    "skills/epdm/STATUS.md",
    "skills/epdm/__init__.py",
    "skills/epdm/core.py",
    "skills/epdm/kinetics.py",
    "skills/epdm/process.py",
    "skills/epdm/qualification.py",
    "skills/epdm/package_audit.py",
    "skills/epdm/data/module_contracts.json",
    "skills/epdm/data/requirements.json",
    "skills/epdm/fixtures/reference_cases.json",
    "skills/epdm/schemas/epdm_case.schema.json",
    "skills/epdm/schemas/epdm_package.schema.json",
    "skills/epdm/scripts/audit_epdm.py",
)
POE_REQUIRED_ARTIFACTS = (
    "skills/poe/STATUS.md",
    "skills/poe/core.py",
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
    "skills/poe/schemas/model_asset_passport.schema.json",
    "skills/poe/data/model_asset_passports.json",
    "skills/poe/estimation.py",
    "skills/poe/reactors.py",
    "skills/poe/dynamics.py",
    "skills/poe/properties.py",
    "skills/poe/scaleup.py",
    "skills/poe/model_passport.py",
    "skills/poe/scripts/audit_p1.py",
)


def build_work_packages(project_id: str) -> list[dict[str, Any]]:
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")
    packages: list[dict[str, Any]] = []
    for gate_index, gate_id in enumerate(GATES):
        for stream_index, (stream_id, title, owner_role) in enumerate(WORKSTREAMS, start=1):
            packages.append(
                {
                    "work_package_id": f"{project_id}-{gate_id}-{stream_index:02d}",
                    "gate_id": gate_id,
                    "workstream_id": stream_id,
                    "title": title,
                    "owner_role": owner_role,
                    "status": "PLANNED",
                    "approval_status": "NOT_EVALUATED",
                    "inputs": [],
                    "outputs": [],
                    "blockers": [],
                    "external_execution": False,
                    "dependency_gate": None if gate_index == 0 else GATES[gate_index - 1],
                }
            )
    return packages


def initial_maturity_record() -> dict[str, Any]:
    return {
        "current_level": "M0",
        "status": "NOT_EVALUATED",
        "evidence_ids": [],
        "approver": None,
        "levels": [
            {
                "level": value.split()[0],
                "definition": value.split(" ", 1)[1],
                "status": "NOT_EVALUATED",
            }
            for value in MATURITY_LEVELS
        ],
    }


def capability_contract_issues(root: Path) -> list[str]:
    root = Path(root)
    required = [
        "SKILL.md",
        "README.md",
        "README.zh-CN.md",
        "skills/process-general/SKILL.md",
        "skills/epdm/SKILL.md",
        "skills/poe/SKILL.md",
        "skills/polymer-general/SKILL.md",
        "schemas/work_package.schema.json",
        "schemas/maturity.schema.json",
        "schemas/scaleup_claim.schema.json",
        "schemas/external_execution.schema.json",
        "schemas/acceptance.schema.json",
        *UNIVERSAL_PACKAGE_REQUIRED_ARTIFACTS,
        *EPDM_REQUIRED_ARTIFACTS,
        *POE_REQUIRED_ARTIFACTS,
    ]
    issues = [
        f"missing capability artifact: {item}" for item in required if not (root / item).is_file()
    ]
    modules = list((root / "skills/process-general/modules").glob("*.md"))
    if len(modules) != 14:
        issues.append(f"process-general must contain 14 modules, found {len(modules)}")
    epdm_modules = root / "skills/epdm/data/module_contracts.json"
    if epdm_modules.is_file():
        import json

        data = json.loads(epdm_modules.read_text(encoding="utf-8"))
        if len(data.get("modules", [])) != 14:
            issues.append("EPDM must contain fourteen machine-readable modules")
    epdm_skill = root / "skills/epdm/SKILL.md"
    if epdm_skill.is_file():
        text = epdm_skill.read_text(encoding="utf-8").casefold()
        for token in (
            "9.1.0-tsao.2",
            "active-site",
            "e/p/diene",
            "recycle",
            "customer",
            "not_evaluated",
        ):
            if token not in text:
                issues.append(f"EPDM skill missing truthful capability token: {token}")
    poe_root = root / "skills/poe/modules"
    found_poe_modules = (
        {path.name for path in poe_root.iterdir() if path.is_dir()} if poe_root.is_dir() else set()
    )
    missing_poe_modules = sorted(set(POE_MODULES) - found_poe_modules)
    extra_poe_modules = sorted(found_poe_modules - set(POE_MODULES))
    if missing_poe_modules:
        issues.append(f"POE is missing required modules: {missing_poe_modules}")
    if extra_poe_modules:
        issues.append(f"POE contains unregistered modules: {extra_poe_modules}")
    for module in POE_MODULES:
        for filename in ("README.md", "contract.schema.json"):
            path = poe_root / module / filename
            if not path.is_file():
                issues.append(f"POE module missing {module}/{filename}")
    poe_skill = root / "skills/poe/SKILL.md"
    if poe_skill.is_file():
        text = poe_skill.read_text(encoding="utf-8").casefold()
        for token in (
            "1.2.0-tsao.3",
            "under_distillation",
            "content_and_evidence_audit_v2_alpha",
            "p1_reference_kernel_alpha",
            "blocked_controlled_metadata_classification",
            "registered_139_of_139",
            "controlled_historical_evidence",
            "not_evaluated",
        ):
            if token not in text:
                issues.append(f"POE skill missing truthful status token: {token}")
    root_skill = root / "SKILL.md"
    if root_skill.is_file():
        text = root_skill.read_text(encoding="utf-8").casefold()
        for token in (
            "g0",
            "g18",
            "m0 idea",
            "m9 operationally-validated",
            "parallel professional workstreams",
        ):
            if token not in text:
                issues.append(f"root skill missing capability token: {token}")
    return issues
