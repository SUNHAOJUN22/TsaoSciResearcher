#!/usr/bin/env python3
"""Validate bilingual mathematical README content, executable strategies and governed diagrams."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README_CN = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
PROMPT = ROOT / "docs" / "ACCEPTANCE_REWRITE_PROMPT.md"
DIAGRAMS = (
    ROOT / "assets" / "demo" / "dft-mathematical-core.svg",
    ROOT / "assets" / "demo" / "qualification-mathematics.svg",
)

COMMON_TOKENS = (
    "SOFTWARE_ACCEPTANCE_READY",
    "EXTERNAL_HOLD",
    "release-acceptance.json",
    "Kohn\u2013Sham",
    "neighbor_list.py",
    "MAX_MINIMUM_IMAGE_CANDIDATES",
    "engine_parser_contract.py",
    "scripts/quality_gate.py",
    "scripts/validate_readme_math.py",
    "assets/demo/dft-mathematical-core.svg",
    "assets/demo/qualification-mathematics.svg",
    "AI-GENERATED CONCEPTUAL ILLUSTRATION",
)
FORMULA_TOKENS = (
    r"\hat H_{\mathrm{KS}}",
    r"\rho(\mathbf r)",
    r"E[\rho]",
    r"\mathbf F_I",
    r"\Omega_{\mathrm{BZ}}",
    r"\mathbf n^\star",
    r"\operatorname*{arg\,min}",
    r"\Delta\mathbf r_{\mathrm{MIC}}",
    r"\Delta\mathbf s_{\mathrm{MIC}}\mathbf H",
    r"a_{\mathrm{tol}}",
    r"\operatorname{median}",
    r"\Delta G^\ddagger",
    r"u_{\max}",
)
COMMAND_TOKENS = (
    "inspect_xyz.py",
    "--backend cell-list",
    "--engine gaussian",
    "validate_benchmark_contract.py",
    "validate_compute_qualification.py",
    "capture_compute_contract_evidence.py",
    "build_release_acceptance.py",
    "quality_gate.ps1",
)


def _read(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""


def _formula_block_count(text: str) -> int:
    return text.count("$$") // 2


def _validate_readme(name: str, text: str, errors: list[str]) -> dict[str, Any]:
    for token in COMMON_TOKENS:
        if token not in text:
            errors.append(f"{name} missing required contract token: {token}")
    for token in FORMULA_TOKENS:
        if token not in text:
            errors.append(f"{name} missing mathematical token: {token}")
    for token in COMMAND_TOKENS:
        if token not in text:
            errors.append(f"{name} missing executable strategy token: {token}")

    blocks = _formula_block_count(text)
    if text.count("$$") % 2:
        errors.append(f"{name} has an unbalanced display-math delimiter")
    if blocks < 10:
        errors.append(f"{name} must contain at least 10 display-math blocks; found {blocks}")
    if len(re.findall(r"```(?:bash|powershell|text)?\n", text)) < 8:
        errors.append(f"{name} must contain at least 8 governed strategy/code blocks")
    if "29/29" not in text:
        errors.append(f"{name} does not declare the 29/29 permanent gate contract")
    return {"display_math_blocks": blocks, "bytes": len(text.encode("utf-8"))}


def validate() -> dict[str, Any]:
    errors: list[str] = []
    chinese = _read(README_CN, errors)
    english = _read(README_EN, errors)
    prompt = _read(PROMPT, errors)

    if "## 数理核心" not in chinese:
        errors.append("README.md lacks the 数理核心 section")
    if "## Mathematical core" not in english:
        errors.append("README_EN.md lacks the Mathematical core section")
    if "必须执行的修改" not in prompt or "不得虚构" not in prompt:
        errors.append("acceptance rewrite prompt is incomplete")

    summaries = {
        "README.md": _validate_readme("README.md", chinese, errors),
        "README_EN.md": _validate_readme("README_EN.md", english, errors),
    }

    for path in DIAGRAMS:
        text = _read(path, errors)
        if text and "SYNTHETIC DEMO" not in text:
            errors.append(f"{path.relative_to(ROOT)} lacks visible synthetic-demo disclosure")
        if text and "NOT SCIENTIFIC DATA" not in text:
            errors.append(f"{path.relative_to(ROOT)} lacks visible non-scientific-data disclosure")
        if text and "<svg" not in text:
            errors.append(f"{path.relative_to(ROOT)} is not an SVG document")

    return {
        "ok": not errors,
        "readmes": summaries,
        "prompt": str(PROMPT.relative_to(ROOT)),
        "diagrams": [str(path.relative_to(ROOT)) for path in DIAGRAMS],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    report = validate()
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        print(f"README math validation: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
