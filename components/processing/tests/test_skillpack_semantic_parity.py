from __future__ import annotations

from tsao.skillpacks import (
    EXPECTED_SUBSKILLS,
    POLYMER_SCRIPTS,
    PROCESS_MODULES,
    PROCESS_WORKFLOWS,
    README_ASSET_MINIMUM,
    skillpack_inventory,
)


def test_skillpack_inventory_semantic_parity_contract() -> None:
    result = skillpack_inventory()

    assert result["pass"] is True
    assert result["errors"] == []
    assert result["subskills"] == sorted(EXPECTED_SUBSKILLS)
    assert result["process_general_modules_present"] == len(PROCESS_MODULES)
    assert result["process_general_modules_expected"] == len(PROCESS_MODULES)
    assert result["process_general_workflows_present"] == len(PROCESS_WORKFLOWS)
    assert result["process_general_workflows_expected"] == len(PROCESS_WORKFLOWS)
    assert result["polymer_general_scripts_present"] == len(POLYMER_SCRIPTS)
    assert result["polymer_general_scripts_expected"] == len(POLYMER_SCRIPTS)
    assert result["readme_svg_assets"] >= README_ASSET_MINIMUM
    assert result["readme_svg_assets_expected_minimum"] == README_ASSET_MINIMUM
    assert result["scientific_technical_approval"] == "NOT_EVALUATED"
    assert result["engineering_design_approval"] == "NOT_EVALUATED"
    assert result["industrial_performance_guarantee"] == "NOT_EVALUATED"
