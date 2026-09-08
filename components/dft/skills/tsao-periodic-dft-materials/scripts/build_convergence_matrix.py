#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

import yaml

ap = argparse.ArgumentParser()
ap.add_argument("spec", type=Path)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
d = yaml.safe_load(a.spec.read_text())
vals = d.get("values") or []
if len(vals) < 3:
    raise SystemExit("at least three convergence values required")
a.out.parent.mkdir(parents=True, exist_ok=True)
with a.out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "parameter", "value", "observable", "method_fingerprint", "status"])
    for i, v in enumerate(vals, 1):
        w.writerow(
            [
                f"{d.get('study_id', 'CONV')}-{i:03d}",
                d["parameter"],
                v,
                d["observable"],
                d["fixed_method_fingerprint"],
                "planned",
            ]
        )
print(f"wrote {len(vals)} rows")
