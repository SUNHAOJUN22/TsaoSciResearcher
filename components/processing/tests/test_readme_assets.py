from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
ASSET_PATTERN = re.compile(r"!\[([^\]]+)\]\((docs/assets/readme/[^)]+\.svg)\)")


def legacy_asset_names() -> set[str]:
    from scripts.generate_decision_readme_assets import ASSETS as DECISION_ASSETS
    from scripts.generate_extended_readme_assets import EXTRA_ASSETS
    from scripts.generate_performance_readme_assets import ASSETS as PERFORMANCE_ASSETS
    from scripts.generate_readme_assets import ASSETS

    return set(ASSETS) | set(EXTRA_ASSETS) | set(DECISION_ASSETS) | set(PERFORMANCE_ASSETS)


def declared_asset_names() -> set[str]:
    from scripts.generate_acceptance_readme_assets import ASSETS as ACCEPTANCE_ASSETS
    from scripts.generate_uiux_readme_assets import ASSETS as CORE_ASSETS

    return set(CORE_ASSETS) | set(ACCEPTANCE_ASSETS)


def test_master_generator_covers_the_complete_legacy_asset_contract() -> None:
    assert legacy_asset_names().issubset(declared_asset_names())
    assert len(declared_asset_names()) == 32


def test_bilingual_readmes_reference_every_declared_local_svg_asset() -> None:
    declared_names = declared_asset_names()
    expected_names: set[str] | None = None
    for readme_name in ("README.md", "README.zh-CN.md"):
        readme_text = (ROOT / readme_name).read_text(encoding="utf-8")
        matches = ASSET_PATTERN.findall(readme_text)
        assert len(matches) == len(declared_names)
        assert all(alt.strip() for alt, _ in matches)

        asset_paths = [ROOT / relative for _, relative in matches]
        assert all(path.is_file() for path in asset_paths)
        for path in asset_paths:
            document = ElementTree.parse(path)
            root = document.getroot()
            assert root.tag.endswith("svg")
            assert root.find("{http://www.w3.org/2000/svg}title") is not None
            assert root.find("{http://www.w3.org/2000/svg}desc") is not None

        current_names = {path.name for path in asset_paths}
        assert current_names == declared_names
        if expected_names is None:
            expected_names = current_names
        else:
            assert current_names == expected_names


def test_readme_assets_are_deterministically_declared_by_generators() -> None:
    from scripts.generate_uiux_readme_assets import OUT

    committed_names = {path.name for path in OUT.glob("*.svg")}
    assert declared_asset_names() == committed_names
    assert len(committed_names) == 32


def test_visual_system_is_persisted_and_linked() -> None:
    visual_system = ROOT / "docs/README_VISUAL_SYSTEM.md"
    assert visual_system.is_file()
    text = visual_system.read_text(encoding="utf-8")
    assert "Scientific Midnight Bento" in text
    assert "UI/UX Pro Max" in text
    for readme_name in ("README.md", "README.zh-CN.md"):
        assert "docs/README_VISUAL_SYSTEM.md" in (ROOT / readme_name).read_text(encoding="utf-8")


def test_ai_native_visual_family_is_complete() -> None:
    expected = {
        "ai-scientific-reasoning-loop.svg",
        "multiscale-digital-thread.svg",
        "agentic-qualification-orchestrator.svg",
        "uncertainty-decision-landscape.svg",
        "law-to-grade-inverse-design.svg",
        "autonomous-experiment-loop.svg",
        "process-knowledge-graph.svg",
        "model-risk-governance.svg",
        "epdm-canonical-publication-pipeline.svg",
        "governed-math-stack.svg",
        "acceptance-readiness-map.svg",
    }
    assert expected.issubset(declared_asset_names())
