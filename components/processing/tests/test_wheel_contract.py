from __future__ import annotations

import math
import zipfile
from pathlib import Path

from scripts.verify_wheel_contents import _REQUIRED, _relative_share_members, verify
from scripts.verify_wheel_runtime import _evaluate_payload


def test_wheel_share_member_index_preserves_relative_contract() -> None:
    names = {
        "pkg.data/data/share/tsao-processing-skill/SKILL.md",
        "share/tsao-processing-skill/docs/CAPABILITY_MATRIX.md",
        "unrelated/share/other/file.txt",
    }
    assert _relative_share_members(names) == {
        "share/tsao-processing-skill/SKILL.md",
        "share/tsao-processing-skill/docs/CAPABILITY_MATRIX.md",
    }


def test_wheel_verifier_rejects_missing_skill(tmp_path: Path) -> None:
    wheel = tmp_path / "empty.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("tsao/__init__.py", "")
    result = verify(wheel)
    assert result["pass"] is False
    assert any("skills/poe" in item for item in result["errors"])
    assert any("installed skillpack member" in item for item in result["errors"])


def test_wheel_verifier_rejects_missing_a2_contract_member(tmp_path: Path) -> None:
    missing_member = "skills/epdm/reaction_network.py"
    wheel = tmp_path / "tsao_processing_skill-0.1.0a11-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for member in sorted(_REQUIRED - {missing_member}):
            archive.writestr(member, "")
        archive.writestr(
            "tsao_processing_skill-0.1.0a11.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: tsao-processing-skill\nVersion: 0.1.0a11\n",
        )
        archive.writestr(
            "tsao_processing_skill-0.1.0a11.dist-info/entry_points.txt",
            "[console_scripts]\ntsao = tsao.cli:main\ntsao-skillpacks = tsao.skillpacks:main\n",
        )
    result = verify(wheel)
    assert result["pass"] is False
    assert f"missing wheel member: {missing_member}" in result["errors"]


def test_wheel_verifier_rejects_controlled_binary(tmp_path: Path) -> None:
    wheel = tmp_path / "binary.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("skills/poe/historical.apw", b"binary")
    result = verify(wheel)
    assert result["pass"] is False
    assert any("controlled historical binary" in item for item in result["errors"])


def test_wheel_verifier_rejects_metadata_version_mismatch(tmp_path: Path) -> None:
    wheel = tmp_path / "tsao_processing_skill-9.9-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "tsao_processing_skill-9.9.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: tsao-processing-skill\nVersion: 9.9\n",
        )
        archive.writestr(
            "tsao_processing_skill-9.9.dist-info/entry_points.txt",
            "[console_scripts]\ntsao = tsao.cli:main\ntsao-skillpacks = tsao.skillpacks:main\n",
        )
    result = verify(wheel)
    assert result["pass"] is False
    assert any("wheel metadata version mismatch" in item for item in result["errors"])


def test_wheel_verifier_rejects_missing_console_scripts(tmp_path: Path) -> None:
    wheel = tmp_path / "missing-entrypoints.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "tsao_processing_skill-0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: tsao-processing-skill\nVersion: 0\n",
        )
    result = verify(wheel)
    assert result["pass"] is False
    assert any("missing wheel console script: tsao" in item for item in result["errors"])
    assert any("missing wheel console script: tsao-skillpacks" in item for item in result["errors"])


def _valid_runtime_payload(install_root: Path) -> dict[str, object]:
    return {
        "tsao_module_path": str(install_root / "site-packages/tsao/__init__.py"),
        "epdm_module_path": str(install_root / "site-packages/skills/epdm/__init__.py"),
        "poe_module_path": str(install_root / "site-packages/skills/poe/__init__.py"),
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
            "root": str(install_root / "share/tsao-processing-skill"),
            "readme_svg_assets": 29,
            "process_general_modules_present": 14,
            "process_general_workflows_present": 6,
        },
        "installed_readme_link_failures": [],
    }


def test_runtime_payload_accepts_only_install_root_members(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    payload = _valid_runtime_payload(install_root)
    assert _evaluate_payload(payload, "TEST", expected_root=install_root) == []


def test_runtime_payload_rejects_incomplete_readme_assets(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    payload = _valid_runtime_payload(install_root)
    skillpacks = payload["skillpacks"]
    assert isinstance(skillpacks, dict)
    skillpacks["readme_svg_assets"] = 28
    errors = _evaluate_payload(payload, "TEST", expected_root=install_root)
    assert "TEST does not contain all 29 README assets" in errors


def test_runtime_payload_rejects_host_editable_import(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    payload = _valid_runtime_payload(install_root)
    payload["tsao_module_path"] = str(tmp_path / "host-checkout/tsao/__init__.py")
    errors = _evaluate_payload(payload, "TEST", expected_root=install_root)
    assert "TEST imported tsao_module_path outside the installed root" in errors


def test_runtime_payload_rejects_host_skillpack_data(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    payload = _valid_runtime_payload(install_root)
    skillpacks = payload["skillpacks"]
    assert isinstance(skillpacks, dict)
    skillpacks["root"] = str(tmp_path / "host-checkout")
    errors = _evaluate_payload(payload, "TEST", expected_root=install_root)
    assert "TEST resolved Skillpack data outside the installed root" in errors


def test_runtime_payload_rejects_incomplete_a2_and_a3_install_contract(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    payload = _valid_runtime_payload(install_root)
    payload["a2_propagation_channel_count"] = 8
    payload["a2_numerical_execution"] = "IMPLEMENTED"
    payload["a3_binding_count"] = 40
    payload["a3_scientific_status"] = "CALIBRATED"
    errors = _evaluate_payload(payload, "TEST", expected_root=install_root)
    assert "TEST A2 propagation matrix is incomplete" in errors
    assert "TEST A2 numerical-execution boundary mismatch" in errors
    assert "TEST A3 rate-package binding count mismatch" in errors
    assert "TEST A3 scientific-status boundary mismatch" in errors
