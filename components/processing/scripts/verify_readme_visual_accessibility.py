#!/usr/bin/env python3
from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import math
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_acceptance_readme_assets import ASSETS as ACCEPTANCE_ASSETS
from scripts.generate_uiux_readme_assets import (
    AMBER,
    ASSETS as CORE_ASSETS,
    BG,
    BLUE,
    CYAN,
    DIM,
    GREEN,
    H,
    MUTED,
    ORANGE,
    OUT,
    PURPLE,
    RED,
    SURFACE,
    TEAL,
    TEXT,
    W,
)
from scripts.harden_readme_svg_accessibility import ROOT_ATTRIBUTES

ASSETS = {**CORE_ASSETS, **ACCEPTANCE_ASSETS}
SVG_NS = "{http://www.w3.org/2000/svg}"
FORBIDDEN_ELEMENTS = {
    "a",
    "animate",
    "animateMotion",
    "animateTransform",
    "foreignObject",
    "image",
    "script",
    "set",
}
EMOJI_PATTERN = re.compile("[\U0001f1e6-\U0001faff]")
MINIMUM_TEXT_SIZE_PX = 12.0


def _linear_channel(value: int) -> float:
    channel = value / 255.0
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    value = hex_color.removeprefix("#")
    if len(value) != 6:
        raise ValueError(f"expected six-digit hex color, found {hex_color}")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return (
        0.2126 * _linear_channel(red)
        + 0.7152 * _linear_channel(green)
        + 0.0722 * _linear_channel(blue)
    )


def contrast_ratio(foreground: str, background: str) -> float:
    brighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)), reverse=True
    )
    return (brighter + 0.05) / (darker + 0.05)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def verify_svg(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        document = ElementTree.parse(path)
    except (ElementTree.ParseError, OSError) as exc:
        return [f"{path.name}: invalid SVG/XML: {exc}"]

    root = document.getroot()
    if root.tag != f"{SVG_NS}svg":
        errors.append(f"{path.name}: root element is not SVG")
    expected_root = {
        "width": str(W),
        "height": str(H),
        "viewBox": f"0 0 {W} {H}",
        "role": "img",
        "aria-labelledby": "title desc",
        **ROOT_ATTRIBUTES,
    }
    for name, expected in expected_root.items():
        if root.attrib.get(name) != expected:
            errors.append(
                f"{path.name}: root attribute {name} must be {expected!r}, "
                f"found {root.attrib.get(name)!r}"
            )

    title = root.find(f"{SVG_NS}title")
    description = root.find(f"{SVG_NS}desc")
    if title is None or not "".join(title.itertext()).strip():
        errors.append(f"{path.name}: missing non-empty <title>")
    if description is None or not "".join(description.itertext()).strip():
        errors.append(f"{path.name}: missing non-empty <desc>")

    for element in root.iter():
        local = _local_name(element.tag)
        if local in FORBIDDEN_ELEMENTS:
            errors.append(f"{path.name}: forbidden SVG element <{local}>")
        for attribute, raw_value in element.attrib.items():
            value = str(raw_value).casefold()
            if attribute.rsplit("}", 1)[-1] == "href":
                errors.append(f"{path.name}: external/linkable href attributes are forbidden")
            if "http://" in value or "https://" in value or "data:" in value:
                errors.append(f"{path.name}: external or embedded resource in {attribute}")
        text_value = "".join(element.itertext())
        if EMOJI_PATTERN.search(text_value):
            errors.append(f"{path.name}: emoji characters are forbidden in structural graphics")
        if local == "text":
            raw_size = element.attrib.get("font-size")
            if raw_size is None:
                errors.append(f"{path.name}: text element has no explicit font-size")
            else:
                try:
                    size = float(raw_size)
                except ValueError:
                    errors.append(f"{path.name}: invalid font-size {raw_size!r}")
                else:
                    if size < MINIMUM_TEXT_SIZE_PX:
                        errors.append(
                            f"{path.name}: font-size {size:g}px is below {MINIMUM_TEXT_SIZE_PX:g}px"
                        )
    return errors


def _contrast_contract() -> dict[str, dict[str, float | bool]]:
    checks = {
        "primary_text_on_background": (TEXT, BG, 4.5),
        "primary_text_on_surface": (TEXT, SURFACE, 4.5),
        "secondary_text_on_background": (MUTED, BG, 3.0),
        "secondary_text_on_surface": (MUTED, SURFACE, 3.0),
        "connector_text_on_background": (DIM, BG, 3.0),
        "blue_on_surface": (BLUE, SURFACE, 3.0),
        "cyan_on_surface": (CYAN, SURFACE, 3.0),
        "teal_on_surface": (TEAL, SURFACE, 3.0),
        "green_on_surface": (GREEN, SURFACE, 3.0),
        "amber_on_surface": (AMBER, SURFACE, 3.0),
        "orange_on_surface": (ORANGE, SURFACE, 3.0),
        "red_on_surface": (RED, SURFACE, 3.0),
        "purple_on_surface": (PURPLE, SURFACE, 3.0),
    }
    result: dict[str, dict[str, float | bool]] = {}
    for name, (foreground, background, minimum) in checks.items():
        ratio = contrast_ratio(foreground, background)
        result[name] = {
            "ratio": round(ratio, 3),
            "minimum": minimum,
            "pass": math.isfinite(ratio) and ratio >= minimum,
        }
    return result


def verify(directory: Path = OUT) -> dict[str, object]:
    expected = set(ASSETS)
    present = {path.name for path in directory.glob("*.svg")}
    errors: list[str] = []
    if present != expected:
        missing = sorted(expected - present)
        unexpected = sorted(present - expected)
        if missing:
            errors.append(f"missing SVG assets: {missing}")
        if unexpected:
            errors.append(f"unexpected SVG assets: {unexpected}")

    for name in sorted(expected & present):
        errors.extend(verify_svg(directory / name))

    contrasts = _contrast_contract()
    for name, row in contrasts.items():
        if not row["pass"]:
            errors.append(f"contrast contract failed for {name}: {row['ratio']} < {row['minimum']}")

    return {
        "pass": not errors,
        "design_system": "Scientific Midnight Bento",
        "asset_count": len(expected),
        "minimum_text_size_px": MINIMUM_TEXT_SIZE_PX,
        "contrast": contrasts,
        "forbidden_elements": sorted(FORBIDDEN_ELEMENTS),
        "errors": errors,
        "qualification_scope": "README_VISUAL_ACCESSIBILITY_ONLY",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify TSAO README visual accessibility")
    parser.add_argument("--directory", type=Path, default=OUT)
    args = parser.parse_args(argv)
    result = verify(args.directory)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
