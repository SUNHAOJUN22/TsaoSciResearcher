from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills.epdm.state_generator import generate_state_definition
from tsao.process_package import validate_process_package
from tsao.project import audit_project, bootstrap_project
from tsao.provenance import verify_manifest


def _package() -> dict[str, object]:
    return {
        "package_id": "P-1",
        "process_family": "generic",
        "status": "PASS",
        "design_basis": {
            "basis_version": "1",
            "capacity_kg_h": 100.0,
            "operating_hours_h_y": 8000.0,
            "components": ["A", "B"],
        },
        "streams": [
            {
                "stream_id": "S-IN",
                "source": "BOUNDARY_IN",
                "destination": "E-1",
                "total_mass_kg_h": 100.0,
                "enthalpy_kW": 10.0,
                "composition": {"A": 0.5, "B": 0.5},
                "evidence_ids": ["EV-1"],
            },
            {
                "stream_id": "S-OUT",
                "source": "E-1",
                "destination": "BOUNDARY_OUT",
                "total_mass_kg_h": 100.0,
                "enthalpy_kW": 10.0,
                "composition": {"A": 0.5, "B": 0.5},
                "evidence_ids": ["EV-1"],
            },
        ],
        "equipment": [
            {
                "equipment_id": "E-1",
                "inlet_stream_ids": ["S-IN"],
                "outlet_stream_ids": ["S-OUT"],
                "duty_kW": 0.0,
                "design_status": "PASS",
            }
        ],
        "utilities": [],
        "controls": [],
        "hse": [{"hazard_id": "H-1", "safeguards": ["trip"], "status": "PASS"}],
        "evidence_ledger": [
            {
                "evidence_id": "EV-1",
                "status": "QUALIFIED",
                "locator": "fixture",
                "applicability": "test",
            }
        ],
        "acceptance": [
            {
                "criterion_id": "A-1",
                "status": "PASS",
                "evidence_ids": ["EV-1"],
                "approver": "reviewer",
            }
        ],
        "approvals": {
            "package_approver": "reviewer",
            "process": "reviewer",
            "controls": "reviewer",
            "hse": "reviewer",
        },
    }


def test_process_package_rejects_component_swap_with_total_mass_closed() -> None:
    package = _package()
    package["streams"][1]["composition"] = {"A": 0.4, "B": 0.6}  # type: ignore[index]
    result = validate_process_package(package)
    assert result["status"] == "FAIL"
    assert "UNDECLARED_COMPONENT_CHANGE" in result["reason_codes"]
    assert result["metrics"]["max_component_balance_relative_error"] > 0


def test_process_package_rejects_topology_mismatch_and_duplicate_reference() -> None:
    package = _package()
    package["streams"][0]["destination"] = "BOUNDARY_OUT"  # type: ignore[index]
    package["equipment"][0]["inlet_stream_ids"] = ["S-IN", "S-IN"]  # type: ignore[index]
    result = validate_process_package(package)
    assert result["status"] == "FAIL"
    assert "STREAM_TOPOLOGY_MISMATCH" in result["reason_codes"]
    assert "DUPLICATE_STREAM_REFERENCE" in result["reason_codes"]


def test_state_pack_rejects_boolean_values() -> None:
    state = generate_state_definition(
        source_state_definition_id="TEST",
        model_level=1,
        site_family_ids=("S1",),
    )
    values = {state_id: 0.0 for state_id in state.state_ids}
    values[state.state_ids[0]] = True
    with pytest.raises(ValueError, match="boolean"):
        state.pack(values)


def test_project_modes_allow_progress_but_initialization_does_not(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    brief.write_text("project_id: P-1\ntitle: Test\n", encoding="utf-8")
    root = tmp_path / "project"
    bootstrap_project(brief, root)
    assert audit_project(root, mode="initialization") == []
    packages = json.loads((root / "00_governance/work_packages.json").read_text(encoding="utf-8"))
    packages[0]["approval_status"] = "APPROVED"
    (root / "00_governance/work_packages.json").write_text(json.dumps(packages), encoding="utf-8")
    assert any("initialization" in issue for issue in audit_project(root, mode="initialization"))
    assert audit_project(root, mode="project") == []


def test_manifest_rejects_path_escape(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "path\tsha256\tbytes\tspecialist\tartifact_class\tlicense_scope\n"
        "../escape\t0\t0\tmaster\tPUBLIC_SOURCE\tPROJECT_OWNED_OR_COMPATIBLE\n",
        encoding="utf-8",
    )
    issues = verify_manifest(tmp_path, manifest)
    assert any("unsafe manifest path" in issue for issue in issues)
