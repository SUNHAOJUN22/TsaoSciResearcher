from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = re.compile(r"^- `([^`]+\.svg)` — ", re.MULTILINE)
FONT_SIZE = re.compile(r"font-size:\s*([0-9]+)px")
HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
LAYOUT = re.compile(r'data-layout="([a-z]+)"')
DESIGN_SYSTEM = "uiux-pro-max-scientific-console-v4"
ICON_SYSTEM = "uiux-pro-max-line-v1"
EXPECTED_LAYOUTS = {
    "hero": 1,
    "bento": 7,
    "workflow": 24,
    "loop": 5,
    "risk": 6,
}
FEATURED_FILES = {
    "hero-multiscale.svg",
    "agent-orchestration.svg",
    "capability-landscape.svg",
    "quantum-to-md.svg",
    "reaction-kinetics-network.svg",
    "polymer-process.svg",
    "continuum-multiphysics.svg",
    "process-optimization-uq.svg",
    "uncertainty-sensitivity.svg",
    "hpc-execution-provenance.svg",
    "hpc-failure-recovery.svg",
    "acceleration-opportunity-pipeline.svg",
}
ALLOWED_COLORS = {
    "#07111F",
    "#0F1B2D",
    "#162338",
    "#334865",
    "#F8FAFC",
    "#D1D9E6",
    "#93A4BB",
    "#60A5FA",
    "#22D3EE",
    "#2DD4BF",
    "#4ADE80",
    "#FBBF24",
    "#FB923C",
    "#F87171",
}
BANNED_DECORATIVE_COLORS = {"#8B5CF6", "#D946EF", "#FF7EC7", "#EC4899"}


def _inventory_names() -> tuple[str, ...]:
    inventory = (ROOT / "assets" / "visuals" / "README.md").read_text(encoding="utf-8")
    names = tuple(ENTRY.findall(inventory))
    assert len(names) == len(set(names))
    return names


def test_readme_showcases_featured_visuals_and_links_full_atlas() -> None:
    names = _inventory_names()
    readmes = [
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"),
    ]
    for readme in readmes:
        assert "V13" in readme
        assert "V12_VISUAL_SYSTEM" not in readme
        assert "V11_VISUAL_SYSTEM" not in readme
        assert "VISUAL_SYSTEM_V10" not in readme
        assert readme.count("assets/visuals/hero-multiscale.svg") == 1
        assert readme.count('<td width="50%"><img src="assets/visuals/') == 2
        assert len(FEATURED_FILES) == 12
        assert "assets/visuals/README.md" in readme
        assert "assets/visuals/DESIGN_SYSTEM.md" in readme
        for name in names:
            relative = f"assets/visuals/{name}"
            if name in FEATURED_FILES:
                assert readme.count(relative) == 1
            else:
                assert relative not in readme


def test_readme_visuals_are_readable_accessible_and_self_contained() -> None:
    readmes = [
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"),
    ]
    manifest_in = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    design_system = (ROOT / "assets" / "visuals" / "DESIGN_SYSTEM.md").read_text(encoding="utf-8")
    assert "recursive-include assets *.md *.svg" in manifest_in
    assert "Scientific Research Console V13" in design_system
    assert "minimum 16 px" in design_system.lower()
    assert "nextlevelbuilder/ui-ux-pro-max-skill" in design_system
    assert "bbylw/ui-ux-pro-max-skill-cn" in design_system
    assert all(layout.title() in design_system for layout in EXPECTED_LAYOUTS)

    names = _inventory_names()
    assert len(names) == 43
    visual_root = ROOT / "assets" / "visuals"
    assert {path.name for path in visual_root.glob("*.svg")} == set(names)

    titles: set[str] = set()
    descriptions: set[str] = set()
    layouts: Counter[str] = Counter()
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    for name in names:
        text = (visual_root / name).read_text(encoding="utf-8")
        lowered = text.lower()
        assert text.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
        assert " viewBox=" in text
        assert f'data-design-system="{DESIGN_SYSTEM}"' in text
        assert f'data-icon-system="{ICON_SYSTEM}"' in text
        assert 'data-density="balanced"' in text
        assert 'shape-rendering="geometricPrecision"' in text
        assert 'text-rendering="optimizeLegibility"' in text
        assert " data-family=" in text
        layout_match = LAYOUT.search(text)
        assert layout_match is not None
        layout = layout_match.group(1)
        layouts[layout] += 1

        assert "<script" not in lowered
        assert "<image" not in lowered
        assert "<foreignobject" not in lowered
        assert "onload=" not in lowered
        assert "onclick=" not in lowered
        assert 'href="http' not in lowered
        assert "<lineargradient" not in lowered
        assert "<radialgradient" not in lowered
        assert "<filter" not in lowered
        assert "EVIDENCE BOUND" in text
        assert "NUMERICAL" in text
        assert "CONVERGENCE" in text
        assert "APPLICABILITY" in text
        assert 3_000 <= len(text.encode("utf-8")) <= 30_000

        if layout == "bento":
            assert "DECISION GATE" in text
        elif layout == "loop":
            assert "FEEDBACK LOOP" in text
        elif layout == "risk":
            assert "BARRIER · LIMIT · ESCALATE" in text

        sizes = [int(value) for value in FONT_SIZE.findall(text)]
        assert sizes and min(sizes) >= 16
        colors = {value.upper() for value in HEX_COLOR.findall(text)}
        assert colors <= ALLOWED_COLORS
        assert not colors & BANNED_DECORATIVE_COLORS

        root = ET.fromstring(text)
        title = root.find("svg:title", namespace)
        description = root.find("svg:desc", namespace)
        assert title is not None and title.text and title.text.strip()
        assert description is not None and description.text and description.text.strip()
        assert title.text.strip() not in titles
        assert description.text.strip() not in descriptions
        titles.add(title.text.strip())
        descriptions.add(description.text.strip())

        relative = f"assets/visuals/{name}"
        if name in FEATURED_FILES:
            assert all(relative in readme for readme in readmes)
        else:
            assert all(relative not in readme for readme in readmes)

    assert dict(layouts) == EXPECTED_LAYOUTS
