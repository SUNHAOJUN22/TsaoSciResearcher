import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.registries import adapters

p = argparse.ArgumentParser()
p.add_argument("--workflow", required=True)
p.add_argument("--environment", type=Path, required=True)
a = p.parse_args()
env = {x["slug"]: x for x in json.loads(a.environment.read_text())}
candidates = []
for r in adapters():
    if r["workflow"] == a.workflow:
        p = env.get(r["slug"], {})
        candidates.append(
            {"slug": r["slug"], "available": bool(p.get("available")), "maturity": r["maturity"]}
        )
candidates.sort(key=lambda x: (not x["available"], x["slug"]))
print(
    json.dumps(
        {
            "selected": candidates[0]["slug"]
            if candidates and candidates[0]["available"]
            else None,
            "candidates": candidates,
            "claim_boundary": "No unavailable solver is selected as runnable.",
        },
        indent=2,
    )
)
