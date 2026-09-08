from __future__ import annotations

import math
from pathlib import Path

from scripts.verify_wheel_contents import _REQUIRED
from scripts.verify_wheel_runtime import _evaluate_payload


def _payload(root: Path) -> dict[str, object]:
    return {
        "tsao_module_path": str(root / "site-packages/tsao/__init__.py"),
        "epdm_module_path": str(root / "site-packages/skills/epdm/__init__.py"),
        "poe_module_path": str(root / "site-packages/skills/poe/__init__.py"),
        "pfr": 1.0 - math.exp(-1.0),
        "fit": 0.2,
        "epdm_status": "PASS",
        "package_status": "PASS",
        "a2_state_count": 20,
        "a2_reaction_count": 41,
        "a2_propagation_channel_count": 9,
        "a2_network_status": "PASS",
        "a2_numerical_execution": "NOT_IMPLEMENTED_PHASE_A2",
        "a3_binding_count": 41,
        "a3_rhs_decision": "PASS",
        "a3_rhs_reason_code": "A3_RHS_SOFTWARE_VERIFIED",
        "a3_scientific_status": "CALCULATED_REFERENCE_ONLY",
        "a3_scientific_technical_approval": "NOT_EVALUATED",
        "a15_integration_decision": "PASS",
        "a15_integration_reason_code": "A15_ADAPTIVE_INTEGRATION_COMPLETE",
        "a15_integration_method": "ADAPTIVE_DORMAND_PRINCE_54",
        "a15_time_monotonic": True,
        "a15_scientific_status": "CALCULATED_REFERENCE_ONLY",
        "a15_scientific_technical_approval": "NOT_EVALUATED",
        "skillpacks": {
            "pass": True,
            "delivery": "INSTALLED_SKILLPACK",
            "root": str(root / "share/tsao-processing-skill"),
            "readme_svg_assets": 29,
            "process_general_modules_present": 14,
            "process_general_workflows_present": 6,
        },
        "installed_readme_link_failures": [],
    }


def test_a3_members_are_mandatory_wheel_contracts() -> None:
    assert {
        "skills/epdm/executable_rhs.py",
        "skills/epdm/docs/PHASE_A3_EXECUTABLE_RHS.md",
        "skills/epdm/fixtures/v2_phase_a3_reference_rate_package.json",
        "skills/epdm/schemas/rate-package-a3.schema.json",
    } <= _REQUIRED


def test_a3_installed_runtime_contract_accepts_reference_only_boundary(tmp_path: Path) -> None:
    assert _evaluate_payload(_payload(tmp_path), "TEST", expected_root=tmp_path) == []


def test_a3_installed_runtime_contract_rejects_false_calibration(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["a3_binding_count"] = 40
    payload["a3_scientific_status"] = "CALIBRATED"
    payload["a3_scientific_technical_approval"] = "APPROVED"
    errors = _evaluate_payload(payload, "TEST", expected_root=tmp_path)
    assert "TEST A3 rate-package binding count mismatch" in errors
    assert "TEST A3 scientific-status boundary mismatch" in errors
    assert "TEST A3 scientific approval boundary mismatch" in errors
