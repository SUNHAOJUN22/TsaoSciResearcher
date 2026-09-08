#!/usr/bin/env python3
"""Validate curated README image references and the AI/deterministic visual boundary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import yaml
from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
AI_MANIFEST = ROOT / "assets/ai/manifest.yaml"
MATH_VALIDATOR = ROOT / "scripts/validate_readme_math.py"

MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_IMAGE_RE = re.compile(r"<img\s+[^>]*src=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
REQUIRED_DEMOS = {
    "assets/demo/workflow-architecture.svg",
    "assets/demo/wavefunction-esp-gallery.svg",
    "assets/demo/dft-ml-dashboard.svg",
    "assets/demo/periodic-dft-materials.svg",
    "assets/demo/multiscale-kinetics.svg",
    "assets/demo/hybrid-compute-architecture.svg",
    "assets/demo/cuda-x-decision-map.svg",
    "assets/demo/edge-hpc-closed-loop.svg",
    "assets/demo/native-acceleration-roadmap.svg",
    "assets/demo/evidence-qualification-pipeline.svg",
    "assets/demo/acceleration-registry-governance.svg",
    "assets/demo/backend-portability-stack.svg",
    "assets/demo/windows-linux-execution-matrix.svg",
    "assets/demo/scientific-acceleration-funnel.svg",
    "assets/demo/dft-mathematical-core.svg",
    "assets/demo/qualification-mathematics.svg",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_refs(text: str) -> set[str]:
    return set(MD_IMAGE_RE.findall(text)) | set(HTML_IMAGE_RE.findall(text))


def load_math_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tsao_readme_math_validation", MATH_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MATH_VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate() -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    if not README.is_file() or not README_EN.is_file():
        missing = [str(path.relative_to(ROOT)) for path in (README, README_EN) if not path.is_file()]
        return [f"missing README file(s): {missing}"], warnings

    readmes = {
        "README.md": README.read_text(encoding="utf-8"),
        "README_EN.md": README_EN.read_text(encoding="utf-8"),
    }
    refs_by_readme = {name: image_refs(text) for name, text in readmes.items()}

    for name, refs in refs_by_readme.items():
        local_refs = {ref for ref in refs if not ref.startswith(("http://", "https://"))}
        for ref in sorted(local_refs):
            rel = Path(ref)
            if rel.is_absolute() or ".." in rel.parts:
                failures.append(f"{name} contains unsafe image path: {ref}")
                continue
            path = ROOT / rel
            if not path.is_file():
                failures.append(f"{name} references missing image: {ref}")
                continue
            if path.suffix.lower() == ".svg":
                try:
                    ET.fromstring(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    failures.append(f"invalid SVG referenced by {name}: {ref}: {exc}")

    try:
        manifest = yaml.safe_load(AI_MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        return [*failures, f"AI manifest parse failed: {exc}"], warnings
    assets = manifest.get("assets", []) if isinstance(manifest, dict) else []
    if len(assets) != 1:
        failures.append("AI manifest must contain exactly one governed cover")

    for item in assets:
        if not isinstance(item, dict):
            failures.append("AI manifest asset entry must be mapping")
            continue
        path_value = item.get("path")
        if not path_value:
            failures.append("AI manifest entry has no path")
            continue
        path = ROOT / str(path_value)
        for name, refs in refs_by_readme.items():
            if str(path_value) not in refs:
                failures.append(f"governed AI cover is not embedded in {name}: {path_value}")
            if any(ref.startswith("assets/ai/modules/") for ref in refs):
                failures.append(f"{name} embeds deprecated AI module cards")
        if not path.is_file():
            failures.append(f"AI cover missing: {path_value}")
            continue
        if item.get("sha256") != digest(path):
            failures.append(f"AI cover hash mismatch: {path_value}")
        text = path.read_text(encoding="utf-8", errors="strict")
        if "NOT COMPUTATIONAL DATA" not in text and "NOT SCIENTIFIC DATA" not in text:
            failures.append(f"AI cover lacks visible non-data label: {path_value}")
        for key, expected in {
            "illustrative_only": True,
            "quantitative": False,
            "computed_surface": False,
        }.items():
            if item.get(key) is not expected:
                failures.append(f"AI cover {path_value} has invalid {key}")

    for name, refs in refs_by_readme.items():
        for ref in sorted(REQUIRED_DEMOS - refs):
            failures.append(f"curated README demo is not embedded in {name}: {ref}")

    chinese = readmes["README.md"]
    english = readmes["README_EN.md"]
    if "AI图像声明" not in chinese:
        failures.append("README.md lacks AI图像声明")
    if "AI image declaration" not in english:
        failures.append("README_EN.md lacks AI image declaration")
    for name, text in readmes.items():
        if "AI-GENERATED CONCEPTUAL ILLUSTRATION" not in text:
            failures.append(f"{name} lacks explicit AI-generated conceptual disclosure")
        first_ai = text.find("assets/ai/")
        declaration = text.find("AI图像声明") if name == "README.md" else text.find("AI image declaration")
        if first_ai >= 0 and declaration > first_ai + 800:
            warnings.append(f"{name} AI declaration should appear beside the cover")

    forbidden_phrases = ("AI生成的真实计算结果", "AI-generated computational result", "AI calculated orbital")
    for name, text in readmes.items():
        for phrase in forbidden_phrases:
            if phrase.lower() in text.lower():
                failures.append(f"{name} contains forbidden AI-result wording: {phrase}")

    try:
        report = load_math_validator().validate()
    except (OSError, ImportError, RuntimeError, AttributeError) as exc:
        failures.append(f"README math validator unavailable: {exc}")
    else:
        failures.extend(f"README math contract: {error}" for error in report.get("errors", []))
        if report.get("ok") is not True:
            failures.append("README math contract did not pass")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    failures, warnings = validate()
    for warning in warnings:
        print(f"WARN: {warning}")
    if args.strict and warnings:
        failures.extend(f"strict warning: {warning}" for warning in warnings)
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"README visual validation: {'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
