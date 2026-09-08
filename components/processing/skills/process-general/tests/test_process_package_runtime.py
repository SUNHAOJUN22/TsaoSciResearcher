from __future__ import annotations

from tsao.process_package import process_package_template, validate_process_package


def valid_package():
    return {
        "package_id": "GEN-1",
        "process_family": "generic",
        "status": "PASS",
        "design_basis": {
            "basis_version": "1",
            "capacity_kg_h": 100.0,
            "operating_hours_h_y": 8000.0,
            "components": ["A"],
        },
        "streams": [
            {
                "stream_id": "S1",
                "source": "BOUNDARY_IN",
                "destination": "E1",
                "total_mass_kg_h": 100.0,
                "enthalpy_kW": 10.0,
                "composition": {"A": 1.0},
                "evidence_ids": ["EV1"],
            },
            {
                "stream_id": "S2",
                "source": "E1",
                "destination": "BOUNDARY_OUT",
                "total_mass_kg_h": 100.0,
                "enthalpy_kW": 15.0,
                "composition": {"A": 1.0},
                "evidence_ids": ["EV1"],
            },
        ],
        "equipment": [
            {
                "equipment_id": "E1",
                "inlet_stream_ids": ["S1"],
                "outlet_stream_ids": ["S2"],
                "duty_kW": 5.0,
                "design_status": "PASS",
            }
        ],
        "utilities": [],
        "controls": [],
        "hse": [{"hazard_id": "H1", "safeguards": ["trip"], "status": "PASS"}],
        "evidence_ledger": [
            {
                "evidence_id": "EV1",
                "status": "QUALIFIED",
                "locator": "fixture",
                "applicability": "test",
            }
        ],
        "acceptance": [
            {"criterion_id": "C1", "status": "PASS", "evidence_ids": ["EV1"], "approver": "A"}
        ],
        "approvals": {"package_approver": "P", "process": "P", "controls": "C", "hse": "H"},
    }


def test_valid_generic_package_passes():
    assert validate_process_package(valid_package())["status"] == "PASS"


def test_template_is_hold():
    assert validate_process_package(process_package_template("fine chemical"))["status"] == "HOLD"


def test_composition_and_unknown_equipment_fail():
    data = valid_package()
    data["streams"][0]["composition"] = {"A": 0.9}
    data["streams"][1]["destination"] = "UNKNOWN"
    result = validate_process_package(data)
    assert result["status"] == "FAIL"


def test_mass_and_energy_balance_fail_closed():
    data = valid_package()
    data["streams"][1]["total_mass_kg_h"] = 80.0
    data["streams"][1]["enthalpy_kW"] = 25.0
    result = validate_process_package(data)
    assert result["status"] == "FAIL"


def test_pass_requires_qualified_evidence_and_named_approver():
    data = valid_package()
    data["evidence_ledger"][0]["status"] = "REPORTED"
    data["acceptance"][0].pop("approver")
    assert validate_process_package(data)["status"] == "FAIL"


def test_open_hazard_and_missing_controls_hold():
    data = valid_package()
    data["hse"][0]["status"] = "HOLD"
    data["approvals"].pop("controls")
    assert validate_process_package(data)["status"] == "HOLD"


def test_balanced_package_omits_zero_component_error_details() -> None:
    result = validate_process_package(valid_package())
    assert result["component_balance_errors"] == {}
    assert result["failed_component_balances"] == []
    assert result["metrics"]["max_component_balance_relative_error"] == 0.0
