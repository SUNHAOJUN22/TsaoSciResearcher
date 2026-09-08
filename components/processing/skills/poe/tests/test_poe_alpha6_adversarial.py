from __future__ import annotations

import json
from pathlib import Path

from skills.poe.core import (
    audit_process_package,
    load_asset_registry,
    qualify_property_method,
    validate_asset_registry,
    validate_process_case,
)

POE = Path(__file__).resolve().parents[1]


def qualified_property() -> dict:
    return {
        "method": "PC-SAFT",
        "selection_basis": "synthetic adversarial fixture",
        "components": ["ethylene", "solvent"],
        "parameter_sources": ["SYNTHETIC"],
        "temperature_K": [330.0, 430.0],
        "pressure_Pa": [100000.0, 20000000.0],
        "composition_domain": {"ethylene": [0.0, 0.5], "solvent": [0.5, 1.0]},
        "polymer_mass_fraction": [0.0, 0.25],
        "benchmarks": [{"property": "density", "source": "synthetic", "points": 3}],
        "error_metrics": {"density_relative": 0.01},
        "unit_system": "SI",
        "extrapolation_status": "NONE",
    }


def valid_case() -> dict:
    return {
        "case_id": "ADV-CASE",
        "mode": "steady",
        "components": ["ethylene", "solvent"],
        "equipment": [{"equipment_id": "R1", "type": "CSTR"}],
        "streams": [
            {
                "stream_id": "F",
                "from": "EXTERNAL",
                "to": "R1",
                "flow_kg_h": 100.0,
                "composition": {"ethylene": 0.1, "solvent": 0.9},
            },
            {
                "stream_id": "P",
                "from": "R1",
                "to": "EXTERNAL",
                "flow_kg_h": 100.0,
                "composition": {"ethylene": 0.1, "solvent": 0.9},
            },
        ],
        "property_method": qualified_property(),
        "convergence": True,
        "source_asset_sha256": ["0" * 64],
        "acceptance_criteria": ["mass balance closes"],
        "mass_balance_tolerance_fraction": 0.001,
    }


def test_asset_registry_rejects_unsafe_path_and_bad_duplicate_reference() -> None:
    registry = load_asset_registry(POE / "data/source_asset_registry.json")
    registry["assets"][0]["original_relative_path"] = "../escape.bin"
    registry["assets"][1]["duplicate_asset_ids"] = ["POE-ASSET-9999"]
    result = validate_asset_registry(registry)
    assert result["status"] == "FAIL"
    assert any("unsafe" in item for item in result["errors"])
    assert any("unknown duplicate_asset_ids" in item for item in result["errors"])


def test_property_qualification_rejects_nonfinite_and_unknown_composition() -> None:
    record = qualified_property()
    record["error_metrics"] = {"density_relative": float("nan")}
    record["composition_domain"]["mystery"] = [0.0, 1.0]
    result = qualify_property_method(record)
    assert result["status"] == "FAIL"
    assert any("error_metrics" in item for item in result["errors"])
    assert any("unknown components" in item for item in result["errors"])
    assert (
        qualify_property_method(qualified_property(), {"temperature_K": "hot"})["status"] == "FAIL"
    )


def test_process_case_rejects_duplicate_equipment_bad_composition_and_tolerance() -> None:
    case = valid_case()
    case["equipment"].append({"equipment_id": "R1", "type": "PFR"})
    case["streams"][0]["composition"] = {"ethylene": "bad", "solvent": 0.9}
    case["mass_balance_tolerance_fraction"] = -1.0
    result = validate_process_case(case)
    assert result["status"] == "FAIL"
    assert any("duplicate equipment_id" in item for item in result["errors"])
    assert any("finite fractions" in item for item in result["errors"])
    assert any("tolerance" in item for item in result["errors"])


def test_package_auditor_rejects_nonobject_file_records_and_path_traversal(tmp_path: Path) -> None:
    root = tmp_path / "package"
    root.mkdir()
    manifest = {
        "package_id": "ADV-PKG",
        "version": "1",
        "files": ["not-an-object"],
        "structured_records": {
            "property_method": "../property.json",
            "process_case": "process.json",
            "acceptance": "acceptance.json",
            "requirement_trace": "requirements.json",
            "conflict_ledger": "conflicts.json",
        },
        "approvals": {"package_approver": None},
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("file record" in item or "schema" in item for item in result["errors"])
    assert any(
        "unsafe structured record path" in item or "schema" in item for item in result["errors"]
    )


def test_package_auditor_holds_empty_requirement_trace(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    for name in (
        "工艺设计基础说明.md",
        "工艺流程图PFD.md",
        "物料和能量衡算.md",
        "设备表.md",
        "仪表控制说明.md",
        "公用工程数据.md",
        "稳态模拟报告与模型验证.md",
        "项目验收报告.md",
    ):
        (root / name).write_text("# 受控历史材料\n\n" + "可追溯内容。" * 30, encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "HOLD" and not result["errors"]
