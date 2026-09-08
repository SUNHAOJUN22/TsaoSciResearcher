#!/usr/bin/env python3
"""Generate a reviewable VMD/Tachyon Tcl script from a legacy figure spec or a figure manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import load_yaml  # noqa: E402 -- script-local import follows an explicit sys.path setup


def load_document(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8")) if path.suffix.lower() == ".json" else load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("spec root must be a mapping/object")
    return data


def replace(template: str, mapping: dict[str, object]) -> str:
    for key, value in mapping.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def resolve_input(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).absolute()


def camera_commands(panel: dict[str, Any]) -> str:
    camera = panel.get("camera")
    if not isinstance(camera, dict):
        return "# no explicit camera transform; inspect and record before publication"
    commands: list[str] = []
    for axis, angle in camera.get("rotations", []) if isinstance(camera.get("rotations"), list) else []:
        if axis in {"x", "y", "z"} and isinstance(angle, (int, float)):
            commands.append(f"rotate {axis} by {angle}")
    scale = camera.get("scale_by")
    if isinstance(scale, (int, float)):
        commands.append(f"scale by {scale}")
    translate = camera.get("translate_by")
    if isinstance(translate, list) and len(translate) == 3 and all(isinstance(v, (int, float)) for v in translate):
        commands.append(f"translate by {translate[0]} {translate[1]} {translate[2]}")
    return "\n".join(commands) if commands else "# camera registry contains no transform commands"


def select_panel(
    data: dict[str, Any], figure_id: str | None, panel_id: str | None, panel_index: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    if "figures" in data:
        figures = data.get("figures")
        if not isinstance(figures, list) or not figures:
            raise ValueError("figure manifest contains no figures")
        figure = (
            next((f for f in figures if isinstance(f, dict) and f.get("id") == figure_id), None)
            if figure_id
            else figures[0]
        )
        if not isinstance(figure, dict):
            raise ValueError(f"figure_id not found: {figure_id}")
        panels = figure.get("panels")
        if not isinstance(panels, list) or not panels:
            raise ValueError("selected figure has no panels")
        panel = (
            next((p for p in panels if isinstance(p, dict) and p.get("id") == panel_id), None)
            if panel_id
            else panels[panel_index]
        )
        if not isinstance(panel, dict):
            raise ValueError(f"panel_id not found: {panel_id}")
        return figure, panel
    panels = data.get("panels", []) or []
    panel = panels[panel_index] if panels else data
    if not isinstance(panel, dict):
        raise ValueError("selected panel must be a mapping")
    return data, panel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--figure-id")
    parser.add_argument("--panel-id")
    parser.add_argument("--panel", type=int, default=0, help="Panel index when no panel id is supplied")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    spec_path = args.spec.resolve()
    data = load_document(spec_path)
    figure, panel = select_panel(data, args.figure_id, args.panel_id, args.panel)
    base = spec_path.parent
    panel_type = str(panel.get("type") or figure.get("figure_type") or "").lower()
    shared = figure.get("shared_parameters", {}) if isinstance(figure.get("shared_parameters"), dict) else {}
    params = panel.get("parameters", {}) if isinstance(panel.get("parameters"), dict) else {}
    merged = {**shared, **params}
    width = int(panel.get("width_px", figure.get("width_px", 2400)))
    height = int(panel.get("height_px", figure.get("height_px", 1800)))
    camera_id = panel.get("camera_id", shared.get("camera", "unregistered"))

    if panel_type == "esp" or "esp" in str(figure.get("figure_type", "")).lower():
        density = panel.get("density_cube")
        esp = panel.get("esp_cube")
        if not density or not esp:
            raise SystemExit("ESP panel requires density_cube and esp_cube")
        density_path = resolve_input(base, str(density))
        esp_path = resolve_input(base, str(esp))
        for path in [density_path, esp_path]:
            if not path.exists() and not args.allow_missing:
                raise SystemExit(f"Missing input: {path}")
        template = (SKILL_DIR / "templates/vmd-esp.tcl").read_text(encoding="utf-8")
        mapping = {
            "DENSITY_CUBE": density_path,
            "ESP_CUBE": esp_path,
            "DENSITY_ISOVALUE": merged.get("density_isovalue_au", merged.get("density_isovalue_e_bohr3", 0.001)),
            "ESP_MIN": merged.get("esp_min", -0.05),
            "ESP_MAX": merged.get("esp_max", 0.05),
            "COLOR_MAP": merged.get("color_map", merged.get("palette", "BGR")),
            "OUTPUT_TGA": panel.get("render_output", f"{figure.get('id', figure.get('figure_id', 'figure'))}.tga"),
            "CAMERA_ID": camera_id,
            "CAMERA_COMMANDS": camera_commands(panel),
            "WIDTH": width,
            "HEIGHT": height,
        }
    else:
        cube = panel.get("cube_file")
        if not cube:
            raise SystemExit("Orbital/field panel requires cube_file")
        cube_path = resolve_input(base, str(cube))
        if not cube_path.exists() and not args.allow_missing:
            raise SystemExit(f"Missing input: {cube_path}")
        template = (SKILL_DIR / "templates/vmd-orbital.tcl").read_text(encoding="utf-8")
        mapping = {
            "CUBE_FILE": cube_path,
            "ISOVALUE": merged.get("isovalue_au", merged.get("orbital_isovalue_au", panel.get("isovalue", 0.020))),
            "POSITIVE_COLOR_ID": panel.get("positive_color_id", 0),
            "NEGATIVE_COLOR_ID": panel.get("negative_color_id", 1),
            "OUTPUT_TGA": panel.get("render_output", f"{figure.get('id', figure.get('figure_id', 'figure'))}.tga"),
            "CAMERA_ID": camera_id,
            "CAMERA_COMMANDS": camera_commands(panel),
            "WIDTH": width,
            "HEIGHT": height,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(replace(template, mapping), encoding="utf-8")
    print(f"Generated reviewable VMD script: {args.out}")
    print("Review volume indices, camera/orientation, colors, transparency, and output at final size before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
