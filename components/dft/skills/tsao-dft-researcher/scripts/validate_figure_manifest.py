#!/usr/bin/env python3
"""Validate scientific-figure provenance, comparison consistency, and AI-schematic labeling."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

FORBIDDEN_PALETTES = {"jet", "rainbow", "gist_rainbow", "nipy_spectral"}
ROLES = {"main", "extended", "si", "qa", "exploratory"}
QUANTITATIVE_TYPES = {
    "energy_profile",
    "bar",
    "scatter",
    "histogram",
    "heatmap",
    "box",
    "violin",
    "spectrum",
    "parity",
    "residual",
}
SURFACE_TYPES = {
    "mo",
    "esp",
    "spin_density",
    "difference_density",
    "nci",
    "iri",
    "igmh",
    "elf",
    "lol",
    "nto",
    "hole_electron",
    "icss",
}


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required for YAML manifests; use JSON or install pyyaml") from exc
    return yaml.safe_load(text)


def _require_string(item: dict[str, Any], field: str, where: str, errors: list[str]) -> None:
    if not isinstance(item.get(field), str) or not item[field].strip():
        errors.append(f"{where}: missing non-empty string field {field}")


def _path_exists(base: Path, value: str) -> bool:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.exists() and path.stat().st_size > 0


def validate_manifest(
    data: Any, base: Path, research: dict[str, Any] | None = None, check_files: bool = False
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"], warnings
    _require_string(data, "project_id", "root", errors)
    figures = data.get("figures")
    if not isinstance(figures, list):
        return [*errors, "root: figures must be an array"], warnings

    research_artifacts: dict[str, dict[str, Any]] = {}
    if isinstance(research, dict):
        for artifact in research.get("artifacts", []) if isinstance(research.get("artifacts"), list) else []:
            if isinstance(artifact, dict) and isinstance(artifact.get("id"), str):
                research_artifacts[artifact["id"]] = artifact

    figure_ids: set[str] = set()
    panel_ids: set[str] = set()
    groups: dict[str, list[tuple[str, dict[str, Any], str]]] = {}

    for fi, figure in enumerate(figures):
        fwhere = f"figures[{fi}]"
        if not isinstance(figure, dict):
            errors.append(f"{fwhere}: must be an object")
            continue
        for field in ("id", "title", "role", "conclusion", "evidence_grade"):
            _require_string(figure, field, fwhere, errors)
        figure_id = figure.get("id")
        if isinstance(figure_id, str):
            if figure_id in figure_ids:
                errors.append(f"{fwhere}: duplicate figure id {figure_id}")
            figure_ids.add(figure_id)
        role = figure.get("role")
        if role not in ROLES:
            errors.append(f"{fwhere}: role must be one of {sorted(ROLES)}")
        grade = figure.get("evidence_grade")
        if grade not in {"A", "B", "C", "D"}:
            errors.append(f"{fwhere}: evidence_grade must be A/B/C/D")
        if role in {"main", "extended"} and grade == "D":
            errors.append(f"{fwhere}: grade D evidence cannot be placed in main/extended figures")
        outputs = figure.get("outputs", [])
        if not isinstance(outputs, list) or not outputs:
            errors.append(f"{fwhere}: outputs must be a non-empty list")
            outputs = []
        if check_files:
            for output in outputs:
                if not isinstance(output, str) or not _path_exists(base, output):
                    errors.append(f"{fwhere}: missing or empty output {output!r}")
        panels = figure.get("panels")
        if not isinstance(panels, list) or not panels:
            errors.append(f"{fwhere}: panels must be a non-empty array")
            continue

        for pi, panel in enumerate(panels):
            pwhere = f"{fwhere}.panels[{pi}]"
            if not isinstance(panel, dict):
                errors.append(f"{pwhere}: must be an object")
                continue
            for field in ("id", "type"):
                _require_string(panel, field, pwhere, errors)
            panel_id = panel.get("id")
            if isinstance(panel_id, str):
                if panel_id in panel_ids:
                    errors.append(f"{pwhere}: duplicate panel id {panel_id}")
                panel_ids.add(panel_id)
            panel_type = panel.get("type")
            source_ids = panel.get("source_artifact_ids")
            if not isinstance(source_ids, list) or not source_ids:
                errors.append(f"{pwhere}: source_artifact_ids must be a non-empty list")
                source_ids = []
            for source_id in source_ids:
                if research is not None and source_id not in research_artifacts:
                    errors.append(f"{pwhere}: source artifact {source_id} is absent from research manifest")
            if panel_type in SURFACE_TYPES:
                for field in ("method", "basis", "phase_or_solvent", "renderer", "camera_id"):
                    _require_string(panel, field, pwhere, errors)
                params = panel.get("parameters")
                if not isinstance(params, dict):
                    errors.append(f"{pwhere}: surface panel requires parameters object")
                    params = {}
                palette = str(params.get("palette", "")).lower()
                if palette in FORBIDDEN_PALETTES:
                    errors.append(f"{pwhere}: forbidden palette {palette}")
                if panel_type in {"mo", "nto"}:
                    if not isinstance(params.get("isovalue_au"), (int, float)) or params.get("isovalue_au", 0) <= 0:
                        errors.append(f"{pwhere}: MO/NTO panel requires positive isovalue_au")
                    _require_string(params, "orbital_or_state_label", pwhere + ".parameters", errors)
                    _require_string(params, "positive_phase_color", pwhere + ".parameters", errors)
                    _require_string(params, "negative_phase_color", pwhere + ".parameters", errors)
                    multiplicity = panel.get("multiplicity")
                    if isinstance(multiplicity, int) and multiplicity > 1:
                        label = str(params.get("orbital_or_state_label", "")).lower()
                        if not any(
                            token in label
                            for token in (
                                "somo",
                                "alpha",
                                "beta",
                                "\N{GREEK SMALL LETTER ALPHA}",
                                "\N{GREEK SMALL LETTER BETA}",
                            )
                        ):
                            errors.append(f"{pwhere}: open-shell orbital panel must label SOMO or alpha/beta channel")
                        if not params.get("spin_channel"):
                            errors.append(f"{pwhere}: open-shell orbital panel requires spin_channel")
                if panel_type == "esp":
                    for field in (
                        "density_isovalue_au",
                        "esp_min",
                        "esp_max",
                        "unit",
                        "negative_color",
                        "positive_color",
                    ):
                        if field not in params:
                            errors.append(f"{pwhere}: ESP panel missing {field}")
                    vmin, vmax = params.get("esp_min"), params.get("esp_max")
                    if isinstance(vmin, (int, float)) and isinstance(vmax, (int, float)):
                        if not vmin < 0 < vmax:
                            errors.append(f"{pwhere}: ESP scale must cross zero")
                        if not math.isclose(abs(vmin), abs(vmax), rel_tol=1e-6, abs_tol=1e-12):
                            errors.append(f"{pwhere}: ESP comparison scale must be symmetric")
                if panel_type in {"spin_density", "difference_density"} and (
                    not isinstance(params.get("positive_isovalue"), (int, float))
                    or not isinstance(params.get("negative_isovalue"), (int, float))
                ):
                    errors.append(f"{pwhere}: signed density panel requires positive_isovalue and negative_isovalue")
                group = panel.get("comparison_group")
                if isinstance(group, str) and group:
                    groups.setdefault(group, []).append((pwhere, panel, str(role)))
            elif panel_type in QUANTITATIVE_TYPES:
                if panel.get("quantitative") is not True:
                    errors.append(f"{pwhere}: quantitative panel requires quantitative=true")
                source_data = panel.get("source_data")
                if not isinstance(source_data, str) or not source_data:
                    errors.append(f"{pwhere}: quantitative panel requires source_data")
                elif check_files and not _path_exists(base, source_data):
                    errors.append(f"{pwhere}: source_data is missing or empty: {source_data}")
                panel_outputs = panel.get("outputs", [])
                if not isinstance(panel_outputs, list) or not any(
                    str(x).lower().endswith((".svg", ".pdf")) for x in panel_outputs
                ):
                    warnings.append(f"{pwhere}: quantitative panel should provide SVG or PDF output")
            elif panel_type == "schematic":
                if panel.get("ai_generated") is True:
                    if panel.get("illustrative_only") is not True or panel.get("quantitative") is True:
                        errors.append(
                            f"{pwhere}: AI-generated schematic must be illustrative_only and non-quantitative"
                        )
                    if panel.get("computed_surface") is True:
                        errors.append(f"{pwhere}: AI-generated schematic cannot be marked as a computed surface")
                else:
                    warnings.append(f"{pwhere}: schematic does not state whether AI generation was used")
            else:
                warnings.append(f"{pwhere}: unrecognized panel type {panel_type!r}")

    for group, entries in groups.items():
        if len(entries) < 2:
            continue
        baseline_where, baseline, baseline_role = entries[0]
        base_params = baseline.get("parameters", {}) if isinstance(baseline.get("parameters"), dict) else {}
        fields = ["method", "basis", "phase_or_solvent", "renderer", "camera_id"]
        param_fields = [
            "isovalue_au",
            "density_isovalue_au",
            "esp_min",
            "esp_max",
            "unit",
            "palette",
            "positive_phase_color",
            "negative_phase_color",
        ]
        for where, panel, role in entries[1:]:
            strict = role in {"main", "extended"} or baseline_role in {"main", "extended"}
            for field in fields:
                if panel.get(field) != baseline.get(field):
                    message = f"comparison_group {group}: {field} differs between {baseline_where} and {where}"
                    (errors if strict else warnings).append(message)
            params = panel.get("parameters", {}) if isinstance(panel.get("parameters"), dict) else {}
            for field in param_fields:
                if (field in base_params or field in params) and params.get(field) != base_params.get(field):
                    message = (
                        f"comparison_group {group}: parameter {field} differs between {baseline_where} and {where}"
                    )
                    (errors if strict else warnings).append(message)

    return errors, warnings


def _self_test() -> int:
    valid = {
        "schema_version": "1.0",
        "project_id": "demo",
        "figures": [
            {
                "id": "F1",
                "title": "ESP comparison",
                "role": "main",
                "conclusion": "The accepted structures have different surface potentials.",
                "evidence_grade": "A",
                "outputs": ["F1.svg"],
                "panels": [
                    {
                        "id": "a",
                        "type": "esp",
                        "source_artifact_ids": ["art-a"],
                        "method": "wB97X-D",
                        "basis": "def2-SVP",
                        "phase_or_solvent": "SMD",
                        "renderer": "VMD/Tachyon",
                        "camera_id": "cam-1",
                        "comparison_group": "g1",
                        "parameters": {
                            "density_isovalue_au": 0.001,
                            "esp_min": -0.05,
                            "esp_max": 0.05,
                            "unit": "a.u.",
                            "negative_color": "red",
                            "positive_color": "blue",
                            "palette": "diverging",
                        },
                    },
                    {
                        "id": "b",
                        "type": "esp",
                        "source_artifact_ids": ["art-b"],
                        "method": "wB97X-D",
                        "basis": "def2-SVP",
                        "phase_or_solvent": "SMD",
                        "renderer": "VMD/Tachyon",
                        "camera_id": "cam-1",
                        "comparison_group": "g1",
                        "parameters": {
                            "density_isovalue_au": 0.001,
                            "esp_min": -0.05,
                            "esp_max": 0.05,
                            "unit": "a.u.",
                            "negative_color": "red",
                            "positive_color": "blue",
                            "palette": "diverging",
                        },
                    },
                ],
            }
        ],
    }
    errors, _ = validate_manifest(valid, Path.cwd())
    broken = json.loads(json.dumps(valid))
    broken["figures"][0]["panels"][1]["parameters"]["esp_max"] = 0.06
    broken_errors, _ = validate_manifest(broken, Path.cwd())
    if errors or not broken_errors:
        print("SELF-TEST FAIL")
        if errors:
            print("Unexpected:", errors)
        return 1
    print("SELF-TEST PASS")
    return 0


def main() -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--research-manifest", type=Path)
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if args.manifest is None:
        parser.error("manifest is required unless --self-test is used")
    try:
        data = _load(args.manifest)
        research = _load(args.research_manifest) if args.research_manifest else None
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read manifest: {exc}")
        return 2
    errors, warnings = validate_manifest(data, args.manifest.resolve().parent, research, args.check_files)
    result = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"FAIL: {error}")
        print(f"RESULT: {'PASS' if not errors else 'FAIL'} ({len(errors)} errors, {len(warnings)} warnings)")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
