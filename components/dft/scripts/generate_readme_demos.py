#!/usr/bin/env python3
"""Validate all versioned synthetic README SVG demonstrations without modifying them.

The historical command name is retained for compatibility. The command is deliberately
read-only: a missing, malformed, undersized, unlabeled, or placeholder asset fails the
quality gate instead of being silently replaced with low-quality fallback artwork.
README curation is validated separately by ``validate_readme_visuals.py``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "demo"
NOTICE = "SYNTHETIC DEMO · NOT SCIENTIFIC DATA"
PLACEHOLDER_MARKERS = ("offline placeholder", "replace this compact", "re-run the repository renderer", "todo", "tbd")
DEMO_SPECS: dict[str, tuple[str, int, int]] = {
    "workflow-architecture.svg": ("TsaoDFT auditable research loop", 1180, 430),
    "wavefunction-esp-gallery.svg": ("Wavefunction and surface figure contract", 1120, 470),
    "free-energy-profile.svg": ("Free-energy profile with explicit validation gates", 1080, 500),
    "dft-ml-dashboard.svg": ("DFT + ML: provenance-aware evaluation", 1120, 500),
    "periodic-dft-materials.svg": ("Periodic DFT and materials evidence chain", 1120, 460),
    "active-learning-loop.svg": ("DFT + ML active-learning loop", 1080, 480),
    "hpc-provenance.svg": ("HPC execution and provenance", 1120, 450),
    "multiscale-kinetics.svg": ("DFT to kinetics and multiscale models", 1120, 470),
    "hybrid-compute-architecture.svg": ("Hybrid Python native and engine compute architecture", 1120, 520),
    "cuda-x-decision-map.svg": ("CUDA-X library decision map for TsaoDFT", 1120, 520),
    "edge-hpc-closed-loop.svg": ("Edge to HPC scientific feedback loop", 1120, 500),
    "native-acceleration-roadmap.svg": ("Profile gated native acceleration roadmap", 1120, 500),
    "evidence-qualification-pipeline.svg": ("Scoped L3 acceleration evidence qualification pipeline", 1120, 500),
    "acceleration-registry-governance.svg": ("Canonical acceleration registry governance", 1120, 520),
    "backend-portability-stack.svg": ("Backend portability stack for TsaoDFT", 1120, 520),
    "windows-linux-execution-matrix.svg": ("Windows and Linux execution matrix", 1120, 520),
    "scientific-acceleration-funnel.svg": ("Scientific acceleration qualification funnel", 1120, 520),
}
DIMENSION_RE = re.compile(r"^(\d+)(?:px)?$")


def svg_dimension(root: ET.Element, name: str) -> int:
    value = root.attrib.get(name, "")
    match = DIMENSION_RE.fullmatch(value)
    if not match:
        raise ValueError(f"SVG {name} must be an integer pixel value, got {value!r}")
    return int(match.group(1))


def child_text(root: ET.Element, local_name: str) -> str:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == local_name:
            return "".join(element.itertext()).strip()
    return ""


def validate() -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    checked: list[dict[str, Any]] = []
    if not OUT.is_dir():
        failures.append(f"missing demo asset directory: {OUT.relative_to(ROOT)}")
        return failures, checked
    for filename, (expected_title, expected_width, expected_height) in DEMO_SPECS.items():
        path = OUT / filename
        rel = path.relative_to(ROOT)
        if not path.is_file():
            failures.append(f"missing demo asset: {rel}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            failures.append(f"non-UTF8 demo asset {rel}: {exc}")
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            failures.append(f"invalid SVG XML {rel}: {exc}")
            continue
        if root.tag.rsplit("}", 1)[-1] != "svg":
            failures.append(f"demo root is not SVG: {rel}")
            continue
        try:
            width = svg_dimension(root, "width")
            height = svg_dimension(root, "height")
        except ValueError as exc:
            failures.append(f"{rel}: {exc}")
            continue
        if (width, height) != (expected_width, expected_height):
            failures.append(
                f"demo dimensions changed for {rel}: {(width, height)} != {(expected_width, expected_height)}"
            )
        if root.attrib.get("role") != "img":
            failures.append(f"demo lacks role=img: {rel}")
        title = child_text(root, "title")
        description = child_text(root, "desc")
        if title != expected_title:
            failures.append(f"demo title mismatch for {rel}: {title!r}")
        if not description:
            failures.append(f"demo lacks accessible description: {rel}")
        elif "synthetic" not in description.lower() or "scientific data" not in description.lower():
            failures.append(f"demo description does not disclose synthetic status: {rel}")
        if NOTICE not in text:
            failures.append(f"demo lacks visible synthetic-data notice: {rel}")
        lower = text.lower()
        for marker in PLACEHOLDER_MARKERS:
            if marker in lower:
                failures.append(f"demo contains placeholder marker {marker!r}: {rel}")
        checked.append({"path": rel.as_posix(), "width": width, "height": height, "title": title})
    return failures, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    failures, checked = validate()
    payload = {"ok": not failures, "checked": checked, "failures": failures}
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(
            f"README demo asset validation: {'PASS' if not failures else 'FAIL'} ({len(checked)}/{len(DEMO_SPECS)} checked)"
        )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
