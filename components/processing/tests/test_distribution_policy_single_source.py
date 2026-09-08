from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType

from tsao.distribution_policy import (
    BLOCKED_STATUS,
    audit_public_distribution,
    evaluate_public_distribution,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_public_distribution_policy.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("distribution_policy_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_registry(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "source_asset_registry.part01.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "asset_id": "controlled-1",
                        "confidentiality": "CONTROLLED_INTERNAL",
                        "evidence_class": "CONTROLLED_HISTORICAL_EVIDENCE",
                        "license_scope": "PROJECT_CONTROLLED",
                        "public_fixture_eligible": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "source_asset_registry.json").write_text(
        json.dumps(
            {
                "expected_asset_count": 1,
                "asset_count": 1,
                "asset_files": ["source_asset_registry.part01.json"],
            }
        ),
        encoding="utf-8",
    )


def test_compatibility_cli_delegates_to_the_canonical_policy(tmp_path: Path) -> None:
    module = _load_script()
    assert module.evaluate is evaluate_public_distribution
    _write_registry(tmp_path)
    result = module.evaluate(tmp_path, ["wheel", "source-snapshot"])
    assert result["status"] == BLOCKED_STATUS
    assert result["pass"] is False
    assert result["blocked_surfaces"] == ["source-snapshot", "wheel"]


def test_public_apis_share_one_registry_scan(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    registry = repository / "skills/poe/data"
    _write_registry(registry)

    audit = audit_public_distribution(repository)
    evaluated = evaluate_public_distribution(registry, ["wheel"])

    assert audit.record_count == evaluated["record_count"] == 1
    assert audit.controlled_record_count == evaluated["controlled_record_count"] == 1
    assert audit.part_count == evaluated["part_count"] == 1
    assert audit.registry_sha256 == evaluated["registry_sha256"]
    assert audit.part_set_sha256 == evaluated["part_set_sha256"]


def test_compatibility_cli_and_module_contain_no_second_policy_engine() -> None:
    script_source = SCRIPT.read_text(encoding="utf-8")
    assert "import hashlib" not in script_source
    assert "json.loads" not in script_source
    assert "def evaluate(" not in script_source
    assert "evaluate_public_distribution" in script_source

    module = importlib.import_module("tsao.distribution_policy")
    module_source = inspect.getsource(module)
    assert module_source.count("def _scan_registry(") == 1
    assert "_policy_safe_part_name" not in module_source
    assert "_policy_record_is_controlled" not in module_source
