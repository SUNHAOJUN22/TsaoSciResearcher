from __future__ import annotations

from pathlib import Path

from scripts.harden_readme_svg_accessibility import ROOT_ATTRIBUTES, harden_svg_text
from scripts.verify_readme_visual_accessibility import (
    MINIMUM_TEXT_SIZE_PX,
    contrast_ratio,
    verify,
    verify_svg,
)

ROOT = Path(__file__).resolve().parents[1]


def test_svg_hardener_is_idempotent_and_adds_required_root_attributes() -> None:
    raw = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" '
        'viewBox="0 0 1200 720" role="img" aria-labelledby="title desc">'
        '<title id="title">Example</title><desc id="desc">Example SVG</desc>'
        '<text x="10" y="20" font-size="12">label</text></svg>\n'
    )
    once = harden_svg_text(raw)
    twice = harden_svg_text(once)
    assert once == twice
    for name, value in ROOT_ATTRIBUTES.items():
        assert f'{name}="{value}"' in once


def test_committed_readme_visuals_pass_accessibility_contract() -> None:
    result = verify(ROOT / "docs/assets/readme")
    assert result["pass"] is True, result["errors"]
    assert result["asset_count"] == 32
    assert result["minimum_text_size_px"] == MINIMUM_TEXT_SIZE_PX
    assert all(row["pass"] for row in result["contrast"].values())


def test_contrast_reference_values_meet_wcag_thresholds() -> None:
    assert contrast_ratio("#F8FAFC", "#07111F") >= 4.5
    assert contrast_ratio("#A8B5C7", "#101E33") >= 3.0
    assert contrast_ratio("#4F7CFF", "#101E33") >= 3.0


def test_visual_verifier_rejects_external_resources_and_tiny_text(tmp_path: Path) -> None:
    svg = tmp_path / "bad.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" '
        'viewBox="0 0 1200 720" role="img" aria-labelledby="title desc" '
        'focusable="false" preserveAspectRatio="xMidYMid meet" '
        'shape-rendering="geometricPrecision" text-rendering="optimizeLegibility" '
        'data-design-system="scientific-midnight-bento" data-design-version="2">'
        '<title id="title">Bad</title><desc id="desc">Bad asset</desc>'
        '<image href="https://example.com/image.png"/>'
        '<text x="10" y="20" font-size="10">tiny</text></svg>\n',
        encoding="utf-8",
    )
    errors = verify_svg(svg)
    assert any("forbidden SVG element <image>" in item for item in errors)
    assert any("href attributes are forbidden" in item for item in errors)
    assert any("font-size 10px" in item for item in errors)
