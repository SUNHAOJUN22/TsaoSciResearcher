#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, load_data


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("contract")
    a = p.parse_args()
    try:
        data = load_data(a.contract)
        schema = load_data(ROOT / "schemas/figure-contract.schema.json")
        jsonschema.Draft202012Validator(schema).validate(data)
        formats = set(data["export"]["formats"])
        if formats & {"png", "tiff"} and data["export"]["raster_dpi"] < 300:
            raise ValueError("publication raster export must be at least 300 DPI")
        if data["audience"].lower().find("journal") >= 0 and not formats & {"svg", "pdf"}:
            raise ValueError("journal figure should include SVG or PDF vector export when applicable")
        for panel in data["panels"]:
            if panel["kind"] == "quantitative":
                if panel.get("x_axis") is None or panel.get("y_axis") is None:
                    raise ValueError(f"panel {panel['id']}: quantitative panel requires axes")
                for axis in ["x_axis", "y_axis"]:
                    if not panel[axis]["label"].strip():
                        raise ValueError(f"panel {panel['id']}: {axis} label required")
                    if not panel[axis]["unit"].strip():
                        raise ValueError(
                            f"panel {panel['id']}: {axis} unit or explicit dimensionless marker required"
                        )
        print(
            json.dumps(
                {
                    "valid": True,
                    "figure_id": data["figure_id"],
                    "panels": len(data["panels"]),
                    "formats": sorted(formats),
                },
                ensure_ascii=False,
            )
        )
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
