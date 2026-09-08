from __future__ import annotations

from pathlib import Path

from tsao.core import audit_project, bootstrap_project, route

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").casefold()


def test_poe_subskill_preserves_original_sjtu_method_chain() -> None:
    text = _text("skills/poe/SKILL.md")
    required = {
        "catalyst",
        "kinetics",
        "thermodynamics",
        "reactor",
        "steady",
        "dynamic",
        "devolatilization",
        "scale-up",
        "acceptance",
        "historical evidence",
    }
    assert sorted(item for item in required if item not in text) == []


def test_polymer_general_preserves_original_route_space() -> None:
    text = _text("skills/polymer-general/SKILL.md")
    required = {
        "free-radical",
        "ionic",
        "coordination",
        "polycondensation",
        "ring-opening",
        "emulsion",
        "suspension",
        "gas-phase",
        "reactive extrusion",
        "scale-up",
    }
    assert sorted(item for item in required if item not in text) == []


def test_epdm_preserves_v9_causal_chain_and_benchmark() -> None:
    text = _text("skills/epdm/SKILL.md")
    required = {
        "active-site",
        "e/p/diene",
        "mwd",
        "ccd",
        "long-chain branching",
        "recycle impurities",
        "customer line",
        "vanadium",
    }
    assert sorted(item for item in required if item not in text) == []


def test_process_general_covers_non_polymer_domains() -> None:
    text = _text("skills/process-general/SKILL.md")
    required = {
        "bioprocess",
        "electrochemical",
        "solids",
        "fine-chemical batch",
        "petrochemical",
        "thermodynamics",
        "separation",
        "control",
        "reliability",
        "scale-up",
    }
    assert sorted(item for item in required if item not in text) == []


def test_non_polymer_project_activates_process_general(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    brief.write_text(
        "project_id: BIO-1\ntitle: Fermentation and downstream recovery\n"
        "summary: aerobic fermentation bioreactor with extraction and crystallization\n",
        encoding="utf-8",
    )
    project = tmp_path / "project"
    manifest = bootstrap_project(brief, project)
    assert "bioprocess" in manifest["domain"]
    assert "process-general" in manifest["subskills"]
    assert audit_project(project) == []


def test_unclassified_project_activates_process_general(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    brief.write_text("project_id: GEN-1\ntitle: Novel process opportunity\n", encoding="utf-8")
    project = tmp_path / "project"
    manifest = bootstrap_project(brief, project)
    assert manifest["domain"] == ["generic-process"]
    assert manifest["subskills"] == ["process-general"]


def test_polymer_routes_do_not_lose_master_polymer_subskill() -> None:
    selected = dict(route("metallocene EPDM ENB solution polymerization"))
    assert selected["epdm"] > 0
    assert selected["polymer-general"] > 0
