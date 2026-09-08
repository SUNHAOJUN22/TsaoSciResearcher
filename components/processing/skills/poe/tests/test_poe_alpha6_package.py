from __future__ import annotations

import hashlib
import json
from pathlib import Path

from skills.poe.core import audit_process_package
from skills.poe.scripts import audit_process_package as cli_audit

GROUPS = (
    "design_basis",
    "pfd",
    "material_energy_balance",
    "equipment",
    "instrument_control",
    "utilities",
    "model_validation",
    "acceptance",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualified_property() -> dict:
    return {
        "method": "PC-SAFT",
        "selection_basis": "synthetic package fixture",
        "components": ["ethylene", "solvent"],
        "parameter_sources": ["SYNTHETIC"],
        "temperature_K": [330.0, 430.0],
        "pressure_Pa": [100000.0, 20000000.0],
        "composition_domain": {"ethylene": [0.0, 0.5]},
        "polymer_mass_fraction": [0.0, 0.0],
        "benchmarks": [{"property": "density", "source": "synthetic", "points": 3}],
        "error_metrics": {"density_relative": 0.01},
        "unit_system": "SI",
        "extrapolation_status": "NONE",
    }


def process_case() -> dict:
    return {
        "case_id": "PACKAGE-SYNTHETIC",
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
        "acceptance_criteria": ["balance closed"],
        "mass_balance_tolerance_fraction": 0.001,
    }


def build_manifested_package(root: Path, *, placeholders: bool = False) -> None:
    root.mkdir()
    files = []
    for index, group in enumerate(GROUPS, start=1):
        path = root / f"{group}.md"
        text = (
            "qualified placeholder"
            if placeholders
            else f"# {group}\n\nThis synthetic alpha.6 deliverable contains a traceable design decision, evidence identifier, SI unit basis, acceptance criterion, deviation state and cross-reference to the structured process record."
        )
        path.write_text(text, encoding="utf-8")
        files.append(
            {
                "deliverable_id": f"D{index:02d}",
                "group": group,
                "path": path.name,
                "sha256": sha(path),
                "bytes": path.stat().st_size,
                "language": "en",
                "content_type": "text/markdown",
                "evidence_ids": ["SYNTHETIC-EVIDENCE"],
            }
        )
    records = {
        "property_method.json": qualified_property(),
        "process_case.json": process_case(),
        "acceptance.json": {
            "result": "CONDITIONAL",
            "approver": "Qualified Reviewer",
            "evidence_ids": ["SYNTHETIC-EVIDENCE"],
        },
        "requirement_trace.json": {
            "requirements": [
                {
                    "requirement_id": "PKG-REQ-001",
                    "criterion": "All eight deliverable groups are content-qualified",
                    "verification_method": "manifest/hash/content audit",
                    "status": "CONDITIONAL",
                    "approver": "Qualified Reviewer",
                    "evidence_ids": ["SYNTHETIC-EVIDENCE"],
                }
            ]
        },
        "conflict_ledger.json": {"conflicts": []},
        "evidence_ledger.json": {
            "evidence": [
                {
                    "evidence_id": "SYNTHETIC-EVIDENCE",
                    "source_id": "SYNTHETIC",
                    "locator": "fixture",
                    "applicability": "software test only",
                    "status": "QUALIFIED",
                    "decision_use": True,
                }
            ]
        },
        "model_passports.json": {
            "models": [
                {
                    "model_id": "POE-MODEL-900",
                    "model_type": "PYTHON_REFERENCE",
                    "software": "TSAO POE",
                    "software_version": "test",
                    "purpose": "synthetic package test",
                    "unit_system": "SI",
                    "applicability_domain": "synthetic software fixture",
                    "dependencies": [],
                    "evidence_ids": ["SYNTHETIC-EVIDENCE"],
                    "execution_status": "QUALIFIED_REFERENCE",
                    "validation_status": "PASS",
                    "approver": "Qualified Reviewer",
                }
            ]
        },
    }
    for name, data in records.items():
        (root / name).write_text(json.dumps(data), encoding="utf-8")
    manifest = {
        "package_id": "POE-PACKAGE-SYNTHETIC",
        "version": "1",
        "files": files,
        "structured_records": {
            "property_method": "property_method.json",
            "process_case": "process_case.json",
            "acceptance": "acceptance.json",
            "requirement_trace": "requirement_trace.json",
            "conflict_ledger": "conflict_ledger.json",
            "evidence_ledger": "evidence_ledger.json",
            "model_passports": "model_passports.json",
        },
        "structured_record_integrity": {
            key.removesuffix(".json"): {
                "path": key,
                "sha256": sha(root / key),
                "bytes": (root / key).stat().st_size,
            }
            for key in records
        },
        "approvals": {"package_approver": "Qualified Reviewer"},
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_eight_placeholder_files_cannot_pass(tmp_path: Path):
    root = tmp_path / "placeholder"
    build_manifested_package(root, placeholders=True)
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("placeholder" in item for item in result["errors"])


def test_manifested_content_level_package_can_pass_software_audit(tmp_path: Path):
    root = tmp_path / "qualified"
    build_manifested_package(root)
    result = audit_process_package(root)
    assert result["status"] == "PASS", result
    assert cli_audit.audit(root)["status"] == "PASS"


def test_hash_tampering_and_cross_reference_fail(tmp_path: Path):
    root = tmp_path / "tamper"
    build_manifested_package(root)
    (root / "pfd.md").write_text(
        "tampered content with enough text to avoid placeholder detection " * 3
    )
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any(
        "SHA-256 mismatch" in item or "byte-count mismatch" in item for item in result["errors"]
    )
    case = json.loads((root / "process_case.json").read_text())
    case["streams"][0]["to"] = "MISSING-EQUIPMENT"
    (root / "process_case.json").write_text(json.dumps(case))
    result = audit_process_package(root)
    assert result["status"] == "FAIL"
    assert any("unknown destination" in item for item in result["errors"])


def test_rich_chinese_legacy_package_is_mapped_not_all_missing(tmp_path: Path):
    root = tmp_path / "中文验收包"
    root.mkdir()
    names = [
        "工艺设计基础说明.md",
        "工艺流程图PFD.md",
        "物料和能量衡算.md",
        "设备表.md",
        "仪表控制说明.md",
        "公用工程数据.md",
        "稳态模拟报告与模型验证.md",
        "项目验收报告.md",
    ]
    for name in names:
        (root / name).write_text(
            "# 受控历史材料\n\n该文件用于测试中文交付物映射，不代表真实工程批准。" * 5,
            encoding="utf-8",
        )
    result = audit_process_package(root)
    assert result["status"] == "HOLD"
    assert not result["errors"]
    assert all(result["legacy_discovery"][group] for group in GROUPS)


def test_unclosed_recycle_and_missing_dynamic_asset_hold(tmp_path: Path):
    root = tmp_path / "holds"
    build_manifested_package(root)
    case = json.loads((root / "process_case.json").read_text())
    case["streams"].append(
        {
            "stream_id": "RECYCLE",
            "from": "R1",
            "to": "R1",
            "flow_kg_h": 10.0,
            "composition": {"ethylene": 0.1, "solvent": 0.9},
            "is_recycle": True,
            "closed": False,
        }
    )
    case["mode"] = "dynamic"
    case["claims"] = {"dynamic_validated": True}
    case_path = root / "process_case.json"
    case_path.write_text(json.dumps(case))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["structured_record_integrity"]["process_case"] = {
        "path": "process_case.json",
        "sha256": sha(case_path),
        "bytes": case_path.stat().st_size,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = audit_process_package(root)
    assert result["status"] == "HOLD"
    assert any("recycle" in item for item in result["holds"])
    assert any("dynamic" in item for item in result["holds"])
