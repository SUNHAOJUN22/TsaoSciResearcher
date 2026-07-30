#!/usr/bin/env python3
"""Build and verify machine-readable facts used by the bilingual README files."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, atomic_write_text

FACTS_PATH = ROOT / "docs/README_FACTS.json"
VISUAL_ATLAS_ASSETS = (
    "docs/assets/ai/research_os_architecture.svg",
    "docs/assets/ai/multi_agent_orchestration.svg",
    "docs/assets/ai/evidence_claim_graph.svg",
    "docs/assets/ai/multiscale_science_pipeline.svg",
    "docs/assets/ai/reproducibility_quality_gates.svg",
    "docs/assets/ai/computation_handoff_boundary.svg",
    "docs/assets/ai/project_state_machine.svg",
    "docs/assets/ai/capability_landscape.svg",
    "docs/assets/ai/original_requirements_coverage.svg",
    "docs/assets/ai/capability_implementation_levels.svg",
    "docs/assets/ai/progressive_routing_loading.svg",
    "docs/assets/ai/project_ledgers_provenance.svg",
    "docs/assets/ai/evidence_citation_integrity_loop.svg",
    "docs/assets/ai/research_production_pipeline.svg",
    "docs/assets/ai/installation_compatibility_matrix.svg",
    "docs/assets/ai/supply_chain_release_attestation.svg",
    "docs/assets/ai/first_principles_strategy_ladder.svg",
    "docs/assets/ai/scientific_problem_method_decision_tree.svg",
    "docs/assets/ai/uncertainty_quantification_validation.svg",
    "docs/assets/ai/scientific_integrity_causality_guard.svg",
    "docs/assets/ai/laboratory_data_quality.svg",
    "docs/assets/ai/scientific_writing_evidence_chain.svg",
    "docs/assets/ai/scientific_figure_edit_guard.svg",
    "docs/assets/ai/human_approval_acceptance_boundary.svg",
    "docs/assets/ai/polymer_multiscale_case_study.svg",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def build_facts(root: Path = ROOT) -> dict[str, Any]:
    manifest = _load_json(root / "manifest.json")
    v2_index = _load_json(root / "capabilities/v2/index.json")
    legacy_stats = _load_json(root / "capability-index/stats.json")

    workflows = sorted(path.name for path in (root / "workflows").iterdir() if path.is_dir())
    schemas = sorted(path.relative_to(root).as_posix() for path in (root / "schemas").rglob("*.schema.json"))
    domain_packs = sorted(path.name for path in (root / "domain-packs").iterdir() if path.is_dir())
    test_modules = sorted(path.name for path in (root / "tests").glob("test_*.py"))
    references = sorted(
        path.relative_to(root).as_posix() for path in (root / "references").rglob("*") if path.is_file()
    )
    templates = sorted(
        path.relative_to(root).as_posix() for path in (root / "templates").rglob("*") if path.is_file()
    )

    facts: dict[str, Any] = {
        "schema_version": "1.0",
        "version": (root / "VERSION").read_text(encoding="utf-8", errors="strict").strip(),
        "license": manifest["license"],
        "python": manifest["compatibility"]["python"],
        "capabilities": {
            "v2_total": v2_index["total"],
            "legacy_named": v2_index["legacy_preserved"],
            "workbook_named": v2_index["workbook_named_total"],
            "domain_named": v2_index["domain_named"],
            "generic_domain_slots": v2_index["generic_domain_slots"],
            "runtime_core": v2_index["core_added"],
            "by_implementation_level": v2_index["by_implementation_level"],
            "legacy_by_category": legacy_stats["by_category"],
            "by_workflow": v2_index["by_workflow"],
        },
        "workflows": {"count": len(workflows), "items": workflows},
        "schemas": {"count": len(schemas), "items": schemas},
        "domain_packs": {"count": len(domain_packs), "items": domain_packs},
        "repository_assets": {
            "test_modules": len(test_modules),
            "ai_diagrams": len(VISUAL_ATLAS_ASSETS),
            "references": len(references),
            "templates": len(templates),
        },
    }
    return facts


def _readme_errors(facts: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    english = (root / "README.md").read_text(encoding="utf-8", errors="strict")
    english_mirror = (root / "README_EN.md").read_text(encoding="utf-8", errors="strict")
    chinese = (root / "README.zh-CN.md").read_text(encoding="utf-8", errors="strict")

    if english != english_mirror:
        errors.append("README_EN.md is not an exact mirror of README.md")

    required_tokens = [
        facts["version"],
        str(facts["capabilities"]["v2_total"]),
        str(facts["capabilities"]["legacy_named"]),
        str(facts["capabilities"]["workbook_named"]),
        str(facts["capabilities"]["domain_named"]),
        str(facts["capabilities"]["generic_domain_slots"]),
        str(facts["capabilities"]["runtime_core"]),
        str(facts["workflows"]["count"]),
        str(facts["schemas"]["count"]),
        str(facts["domain_packs"]["count"]),
        str(facts["repository_assets"]["ai_diagrams"]),
    ]
    for token in required_tokens:
        if token not in english:
            errors.append(f"README.md missing fact token: {token}")
        if token not in chinese:
            errors.append(f"README.zh-CN.md missing fact token: {token}")

    required_docs = [
        "docs/README_AUDIT_REPORT.md",
        "docs/CAPABILITY_COVERAGE_MATRIX.md",
        "docs/README_ARCHITECTURE_MAPPING.md",
        "docs/VALIDATION_EVIDENCE.json",
        "docs/test-dashboard.html",
        "docs/test-dashboard.svg",
    ]
    for relative in required_docs:
        if not (root / relative).is_file():
            errors.append(f"required README evidence document missing: {relative}")
        if relative not in english:
            errors.append(f"README.md does not link to {relative}")
        if relative not in chinese:
            errors.append(f"README.zh-CN.md does not link to {relative}")
    english_atlas = (root / "docs/VISUAL_ATLAS.md").read_text(encoding="utf-8", errors="strict")
    chinese_atlas = (root / "docs/VISUAL_ATLAS.zh-CN.md").read_text(encoding="utf-8", errors="strict")
    if len(VISUAL_ATLAS_ASSETS) < 25 or len(set(VISUAL_ATLAS_ASSETS)) != len(VISUAL_ATLAS_ASSETS):
        errors.append("visual atlas must contain at least 25 unique AI diagrams")
    for relative in VISUAL_ATLAS_ASSETS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"visual atlas asset missing or unsafe: {relative}")
            continue
        try:
            svg_root = ET.fromstring(path.read_text(encoding="utf-8", errors="strict"))
        except ET.ParseError as exc:
            errors.append(f"visual atlas SVG is invalid: {relative}: {exc}")
            continue
        if not svg_root.tag.endswith("svg"):
            errors.append(f"visual atlas asset is not SVG: {relative}")
        child_tags = {child.tag.rsplit("}", 1)[-1] for child in svg_root}
        if "title" not in child_tags or "desc" not in child_tags:
            errors.append(f"visual atlas SVG lacks title/desc accessibility metadata: {relative}")
        if relative not in english:
            errors.append(f"README.md does not embed {relative}")
        if relative not in chinese:
            errors.append(f"README.zh-CN.md does not embed {relative}")
        if path.name not in english_atlas:
            errors.append(f"VISUAL_ATLAS.md does not embed {path.name}")
        if path.name not in chinese_atlas:
            errors.append(f"VISUAL_ATLAS.zh-CN.md does not embed {path.name}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = build_facts()
    rendered = json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        atomic_write_text(FACTS_PATH, rendered)
        print(f"wrote {FACTS_PATH.relative_to(ROOT)}")
        return

    if not FACTS_PATH.is_file() or FACTS_PATH.is_symlink():
        raise SystemExit("docs/README_FACTS.json is missing or unsafe")
    actual = FACTS_PATH.read_text(encoding="utf-8", errors="strict")
    if actual != rendered:
        raise SystemExit("README facts are stale; run scripts/build_readme_facts.py --write")
    errors = _readme_errors(expected)
    if errors:
        raise SystemExit("README consistency check failed:\n- " + "\n- ".join(errors))
    print("README facts and bilingual documentation PASS")


if __name__ == "__main__":
    main()
