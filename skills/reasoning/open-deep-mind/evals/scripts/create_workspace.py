#!/usr/bin/env python3
"""Create an empty, reproducible OpenDeepMind benchmark iteration workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals.json"
CONFIG = ROOT / "benchmark-config.json"


def applies_to_case(cfg: dict, case: dict) -> bool:
    categories = cfg.get("case_categories", ["all"])
    return "all" in categories or case.get("category") in categories


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--split", choices=["train", "validation", "holdout", "all"], default="validation")
    parser.add_argument("--workspace", default="../OpenDeepMind_skill-workspace")
    args = parser.parse_args()

    if args.iteration < 1:
        parser.error("--iteration must be >= 1")

    data = json.loads(EVALS.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cases = [c for c in data["evals"] if args.split == "all" or c["split"] == args.split]
    configs = config["configurations"]
    repetitions = int(config["repetitions"])

    workspace_root = (ROOT.parent.parent / args.workspace).resolve()
    iteration = workspace_root / f"iteration-{args.iteration}"
    iteration.mkdir(parents=True, exist_ok=True)

    expected_slots: list[dict] = []
    for case in cases:
        for cfg in configs:
            if not applies_to_case(cfg, case):
                continue
            for rep in range(1, repetitions + 1):
                expected_slots.append({
                    "case_id": case["id"],
                    "configuration": cfg["id"],
                    "repetition": rep,
                })

    manifest = {
        "benchmark_version": config["benchmark_version"],
        "iteration": args.iteration,
        "split": args.split,
        "cases": [c["id"] for c in cases],
        "configurations": [c["id"] for c in configs],
        "repetitions": repetitions,
        "expected_run_slots": expected_slots,
        "status": "workspace-created-no-model-runs-yet"
    }
    (iteration / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    created = 0
    for case in cases:
        case_dir = iteration / f"eval-{case['id']}"
        case_dir.mkdir(exist_ok=True)
        (case_dir / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
        for cfg in configs:
            if not applies_to_case(cfg, case):
                continue
            for rep in range(1, repetitions + 1):
                run_dir = case_dir / cfg["id"] / f"run-{rep}"
                (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
                instructions = {
                    "case_id": case["id"],
                    "category": case["category"],
                    "split": case["split"],
                    "configuration": cfg["id"],
                    "configuration_kind": cfg.get("kind"),
                    "repetition": rep,
                    "prompt": case["prompt"],
                    "expected_route_for_production": case["expected_route"],
                    "score_routing_accuracy": cfg.get("score_routing_accuracy", True),
                    "skill": cfg.get("skill_path"),
                    "external_repository": cfg.get("repository"),
                    "external_commit": cfg.get("commit"),
                    "disabled_modules": cfg.get("disabled_modules", []),
                    "forced_route": cfg.get("forced_route"),
                    "required_artifacts": ["run_record.json", "grading.json"]
                }
                (run_dir / "run_instructions.json").write_text(
                    json.dumps(instructions, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                created += 1

    print(json.dumps({
        "ok": True,
        "workspace": str(iteration),
        "cases": len(cases),
        "run_slots": created,
        "note": "No model/API calls were executed; this command creates the evaluation workspace only."
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
