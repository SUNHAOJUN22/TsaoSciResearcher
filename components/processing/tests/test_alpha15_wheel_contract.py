from __future__ import annotations

from pathlib import Path

from scripts.verify_wheel_contents import _REQUIRED
from scripts.verify_wheel_runtime import _evaluate_payload
from tests.test_wheel_contract import _valid_runtime_payload


def test_alpha15_wheel_members_are_explicitly_locked() -> None:
    required = {
        "skills/epdm/numerical_integration.py",
        "skills/epdm/schemas/integration-request-a15.schema.json",
        "skills/epdm/schemas/integration-result-a15.schema.json",
        "skills/epdm/fixtures/v2_phase_a4_reference_integration_request.json",
        "skills/epdm/docs/PHASE_A4_NUMERICAL_INTEGRATION.md",
    }
    assert required <= _REQUIRED


def test_alpha15_runtime_contract_rejects_boundary_inflation(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    payload = _valid_runtime_payload(install_root)
    payload["a15_integration_decision"] = "HOLD"
    payload["a15_integration_method"] = "REFERENCE_EULER"
    payload["a15_time_monotonic"] = False
    payload["a15_scientific_status"] = "CALIBRATED"
    payload["a15_scientific_technical_approval"] = "PASS"
    errors = _evaluate_payload(payload, "TEST", expected_root=install_root)
    assert "TEST A15 adaptive integration smoke failed" in errors
    assert "TEST A15 integration-method mismatch" in errors
    assert "TEST A15 monotonic-time gate failed" in errors
    assert "TEST A15 scientific-status boundary mismatch" in errors
    assert "TEST A15 scientific approval boundary mismatch" in errors
