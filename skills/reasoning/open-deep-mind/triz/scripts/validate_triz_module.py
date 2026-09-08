#!/usr/bin/env python3
"""Validate the isolated OpenDeepMind TRIZ module without third-party dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "resources"
EXAMPLES = ROOT / "examples"

RESOURCE_NAMES = [
    "modern_problem_identification.md",
    "innovative_benchmarking.md",
    "function_analysis.md",
    "flow_analysis.md",
    "cause_effect_chain.md",
    "trimming.md",
    "feature_transfer.md",
    "multiscreen_operator.md",
    "psychological_inertia_tools.md",
    "ideality_ifr_resources.md",
    "contradictions.md",
    "39_parameters.md",
    "40_principles.md",
    "contradiction_matrix.json",
    "matrix_anomalies.json",
    "separation_principles.md",
    "substance_field_modeling.md",
    "76_standard_solutions.md",
    "ariz_85c.md",
    "clone_problems.md",
    "effects_and_fos.md",
    "evolution_trends.md",
    "s_curve_and_tese.md",
    "concept_substantiation.md",
    "glossary.md",
    "output_template.md",
    "sources.md",
]

REQUIRED = [
    ROOT / "README.md",
    ROOT / "ROUTER.md",
    ROOT / "module.json",
    ROOT / "VENDORED_LICENSE.md",
    *[RES / name for name in RESOURCE_NAMES],
    EXAMPLES / "brake_disc.md",
    EXAMPLES / "battery_pack.md",
    EXAMPLES / "heat_exchanger_fouling.md",
    EXAMPLES / "anti_example_misframed.md",
    ROOT / "scripts" / "lookup_matrix.py",
    ROOT / "scripts" / "lookup_standard_solution.py",
]

PARAM_ROW = re.compile(r"^\|\s*(\d+)\s*\|", re.MULTILINE)
PRINCIPLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|", re.MULTILINE)
SIS_ID = re.compile(r"^\*\*(\d+\.\d+\.\d+)\s+—", re.MULTILINE)
T_STAGE_RE = re.compile(r"^###\s+T(\d+)\b", re.MULTILINE)

ANCHORS = {
    "1,3": [15, 8, 29, 34],
    "1,9": [2, 8, 15, 38],
    "1,14": [28, 27, 18, 40],
    "1,27": [1, 3, 11, 27],
    "14,1": [1, 8, 40, 15],
}

EXPECTED_SIS_BY_CLASS = {1: 13, 2: 23, 3: 6, 4: 17, 5: 17}


def stable_unique(values: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    def fail(message: str) -> None:
        errors.append(message)

    for path in REQUIRED:
        if not path.is_file():
            fail(f"missing: {path.relative_to(ROOT)}")

    # No unresolved placeholder tokens in module-owned text resources.
    for path in [ROOT / "README.md", ROOT / "ROUTER.md", *[RES / n for n in RESOURCE_NAMES if n.endswith(".md")]]:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for token in ("TODO", "TBD", "PLACEHOLDER" + "_CITATION", "INSERT" + "_SOURCE_HERE"):
                if token in text:
                    fail(f"unresolved token {token!r} in {path.relative_to(ROOT)}")

    # Manifest + activation + true T10 protocol.
    manifest_path = ROOT / "module.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    except Exception as exc:
        fail(f"module.json invalid JSON: {exc}")
        manifest = {}
    if manifest.get("id") != "triz":
        fail("module id must be triz")
    if manifest.get("activation") != "explicit-only":
        fail("TRIZ activation must be explicit-only")
    if manifest.get("must_not_auto_activate") is not True:
        fail("TRIZ manifest must set must_not_auto_activate=true")
    expected_t = [f"T{i}" for i in range(1, 11)]
    if manifest.get("protocol", {}).get("stages") != expected_t:
        fail("TRIZ manifest T10 stages must be T1..T10")

    router_path = ROOT / "ROUTER.md"
    router_text = router_path.read_text(encoding="utf-8") if router_path.is_file() else ""
    stages = [int(x) for x in T_STAGE_RE.findall(router_text)]
    if stages != list(range(1, 11)):
        fail(f"T10 stages must be exactly T1..T10 in order; got {stages}")
    if re.search(r"^###\s+T0\b", router_text, re.MULTILINE):
        fail("T10 must not contain T0")
    for marker in ("Explicit opt-in only", "Do not", "Return to OpenDeepMind", "First Principles validation"):
        if marker.lower() not in router_text.lower():
            fail(f"ROUTER.md missing activation/handoff marker: {marker!r}")

    # 39 parameters.
    p39 = RES / "39_parameters.md"
    if p39.is_file():
        ids = [int(x) for x in PARAM_ROW.findall(p39.read_text(encoding="utf-8"))]
        ids = sorted(set(x for x in ids if 1 <= x <= 39))
        if ids != list(range(1, 40)):
            fail(f"39_parameters.md must contain IDs 1..39 exactly; got {ids}")

    # 40 principles.
    p40 = RES / "40_principles.md"
    if p40.is_file():
        ids = [int(x) for x in PRINCIPLE_ROW.findall(p40.read_text(encoding="utf-8"))]
        ids = sorted(set(x for x in ids if 1 <= x <= 40))
        if ids != list(range(1, 41)):
            fail(f"40_principles.md must contain IDs 1..40 exactly; got {ids}")

    # Matrix integrity, preserving source transcription but requiring anomaly documentation.
    matrix_path = RES / "contradiction_matrix.json"
    anomaly_path = RES / "matrix_anomalies.json"
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8")) if matrix_path.is_file() else {}
    except Exception as exc:
        fail(f"matrix JSON parse failed: {exc}")
        matrix = {}
    try:
        anomaly_data = json.loads(anomaly_path.read_text(encoding="utf-8")) if anomaly_path.is_file() else {}
    except Exception as exc:
        fail(f"matrix_anomalies.json parse failed: {exc}")
        anomaly_data = {}

    cells = matrix.get("cells", {}) if isinstance(matrix, dict) else {}
    anomalies = anomaly_data.get("anomalies", {}) if isinstance(anomaly_data, dict) else {}
    if not isinstance(cells, dict):
        fail("matrix cells is not a mapping")
        cells = {}
    if not isinstance(anomalies, dict):
        fail("matrix anomalies is not a mapping")
        anomalies = {}
    if len(cells) != 1190:
        fail(f"expected 1190 populated matrix cells, found {len(cells)}")

    duplicate_cells: dict[str, list[int]] = {}
    for key, values in cells.items():
        try:
            a_s, b_s = key.split(",", 1)
            a, b = int(a_s), int(b_s)
        except Exception:
            fail(f"invalid matrix key: {key!r}")
            continue
        if not (1 <= a <= 39 and 1 <= b <= 39):
            fail(f"matrix key out of range: {key}")
        if a == b:
            fail(f"diagonal matrix cell should not be populated: {key}")
        if not isinstance(values, list) or not 1 <= len(values) <= 4:
            fail(f"matrix cell {key} must contain 1..4 principle IDs")
            continue
        if any(not isinstance(v, int) or not 1 <= v <= 40 for v in values):
            fail(f"matrix cell {key} contains invalid principle ID: {values}")
        if len(values) != len(set(values)):
            duplicate_cells[key] = values

    for key, values in duplicate_cells.items():
        anomaly = anomalies.get(key)
        if not isinstance(anomaly, dict):
            fail(f"duplicate matrix cell {key} is not documented in matrix_anomalies.json")
            continue
        if anomaly.get("vendored_value") != values:
            fail(f"matrix anomaly {key} vendored_value does not match source data")
        if anomaly.get("normalized_value") != stable_unique(values):
            fail(f"matrix anomaly {key} normalized_value is inconsistent")
        warnings.append(f"documented matrix transcription anomaly {key}: {values} -> {stable_unique(values)}")

    for key in anomalies:
        if key not in cells:
            fail(f"matrix anomaly references missing cell: {key}")
    for key, expected in ANCHORS.items():
        if cells.get(key) != expected:
            fail(f"matrix anchor mismatch {key}: expected {expected}, got {cells.get(key)}")

    # 76 SIS exact count and class distribution.
    sis_path = RES / "76_standard_solutions.md"
    if sis_path.is_file():
        ids = SIS_ID.findall(sis_path.read_text(encoding="utf-8"))
        if len(ids) != 76:
            fail(f"expected 76 numbered SIS entries, found {len(ids)}")
        if len(set(ids)) != len(ids):
            fail("duplicate SIS identifiers found")
        counts = {i: 0 for i in range(1, 6)}
        for sis_id in ids:
            counts[int(sis_id.split(".")[0])] += 1
        if counts != EXPECTED_SIS_BY_CLASS:
            fail(f"SIS class distribution mismatch: expected {EXPECTED_SIS_BY_CLASS}, got {counts}")

    # ARIZ must contain all 9 parts.
    ariz_path = RES / "ariz_85c.md"
    if ariz_path.is_file():
        text = ariz_path.read_text(encoding="utf-8")
        for part in range(1, 10):
            if f"# Part {part}" not in text:
                fail(f"ARIZ missing Part {part}")

    # Psychological-inertia tools should include all classical operators we claim.
    psych_path = RES / "psychological_inertia_tools.md"
    if psych_path.is_file():
        text = psych_path.read_text(encoding="utf-8")
        for marker in ("Nine Windows", "Size–Time–Cost", "Smart Little People", "Intensification of contradiction"):
            if marker not in text:
                fail(f"psychological-inertia resource missing marker: {marker!r}")

    # Module map should reference all owned resources and canonical router.
    module_readme = ROOT / "README.md"
    if module_readme.is_file():
        text = module_readme.read_text(encoding="utf-8")
        for name in RESOURCE_NAMES:
            if name not in text:
                fail(f"triz/README.md does not list resource: {name}")
        for marker in ("ROUTER.md", "module.json", "lookup_standard_solution.py"):
            if marker not in text:
                fail(f"triz/README.md missing structural entry: {marker}")

    # Python syntax.
    for script in (ROOT / "scripts").glob("*.py"):
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except SyntaxError as exc:
            fail(f"{script.name} syntax error: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(json.dumps({"ok": False, "module": "triz", "errors": len(errors), "warnings": len(warnings)}))
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    print(json.dumps({
        "ok": True,
        "module": "triz",
        "errors": 0,
        "warnings": len(warnings),
        "resources": len(RESOURCE_NAMES),
        "matrix_cells": 1190,
        "documented_matrix_anomalies": len(anomalies),
        "sis": 76,
        "ariz_parts": 9,
        "t_stages": 10,
        "examples": 4,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
