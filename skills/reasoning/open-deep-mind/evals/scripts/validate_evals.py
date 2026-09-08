#!/usr/bin/env python3
"""Validate OpenDeepMind behavioral benchmark definitions without third-party packages."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals.json"
CONFIG = ROOT / "benchmark-config.json"

EXPECTED_CATEGORIES = {
    "routing": 12,
    "first-philosophy": 10,
    "first-principles": 12,
    "dual-engine": 8,
    "triz-positive": 10,
    "triz-negative": 8,
}
EXPECTED_SPLITS = {"train": 36, "validation": 12, "holdout": 12}
EXPECTED_PREFIX = {
    "routing": "R",
    "first-philosophy": "F",
    "first-principles": "P",
    "dual-engine": "D",
    "triz-positive": "T",
    "triz-negative": "N",
}
VALID_ROUTES = {"phi", "p", "phi-p", "triz"}
ID_RE = re.compile(r"^[RFPDTN][0-9]{2}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = json.loads(EVALS.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"cannot parse evals.json: {exc}"}))
        return 1

    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"cannot parse benchmark-config.json: {exc}"}))
        return 1

    if data.get("skill_name") != "open-deep-mind":
        errors.append("skill_name must be open-deep-mind")
    if data.get("benchmark_version") != config.get("benchmark_version"):
        errors.append("evals benchmark_version != benchmark-config benchmark_version")

    evals = data.get("evals")
    if not isinstance(evals, list):
        errors.append("evals must be a list")
        evals = []
    if len(evals) != 60:
        errors.append(f"expected exactly 60 evals, found {len(evals)}")

    ids: set[str] = set()
    categories: Counter[str] = Counter()
    splits: Counter[str] = Counter()

    for index, case in enumerate(evals):
        prefix = f"evals[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in (
            "id", "category", "split", "prompt", "expected_output",
            "expected_route", "triz_allowed", "assertions", "red_blockers"
        ):
            if key not in case:
                errors.append(f"{prefix} missing {key}")
        cid = case.get("id")
        category = case.get("category")
        split = case.get("split")
        route = case.get("expected_route")
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid):
            errors.append(f"{prefix}.id invalid: {cid!r}")
        elif cid in ids:
            errors.append(f"duplicate eval id: {cid}")
        else:
            ids.add(cid)
        if category not in EXPECTED_CATEGORIES:
            errors.append(f"{prefix}.category invalid: {category!r}")
        else:
            categories[category] += 1
            if isinstance(cid, str) and not cid.startswith(EXPECTED_PREFIX[category]):
                errors.append(f"{cid}: ID prefix does not match category {category}")
        if split not in EXPECTED_SPLITS:
            errors.append(f"{prefix}.split invalid: {split!r}")
        else:
            splits[split] += 1
        if route not in VALID_ROUTES:
            errors.append(f"{prefix}.expected_route invalid: {route!r}")
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or len(prompt.strip()) < 20:
            errors.append(f"{prefix}.prompt too short")
        expected = case.get("expected_output")
        if not isinstance(expected, str) or len(expected.strip()) < 20:
            errors.append(f"{prefix}.expected_output too short")
        assertions = case.get("assertions")
        if not isinstance(assertions, list) or len(assertions) < 2 or not all(isinstance(x, str) and len(x) >= 8 for x in assertions):
            errors.append(f"{prefix}.assertions must contain at least two substantive strings")
        blockers = case.get("red_blockers")
        if not isinstance(blockers, list) or len(blockers) < 1 or not all(isinstance(x, str) and len(x) >= 8 for x in blockers):
            errors.append(f"{prefix}.red_blockers must be a non-empty list")
        triz_allowed = case.get("triz_allowed")
        if not isinstance(triz_allowed, bool):
            errors.append(f"{prefix}.triz_allowed must be boolean")
        triz_expected = route == "triz"
        if triz_expected:
            if triz_allowed is not True:
                errors.append(f"{cid}: TRIZ-routed case must explicitly allow TRIZ")
            p = prompt.lower() if isinstance(prompt, str) else ""
            if not any(token in p for token in ("triz", "ariz", "su-field", "ifr")) and "物场" not in p:
                errors.append(f"{cid}: TRIZ-routed case lacks an explicit trigger token")
        elif triz_allowed is not False:
            errors.append(f"{cid}: non-TRIZ route must not pre-authorize TRIZ")
        if category == "triz-positive" and not triz_expected:
            errors.append(f"{cid}: triz-positive must route triz")

    if dict(categories) != EXPECTED_CATEGORIES:
        errors.append(f"category distribution mismatch: expected {EXPECTED_CATEGORIES}, got {dict(categories)}")
    if dict(splits) != EXPECTED_SPLITS:
        errors.append(f"split distribution mismatch: expected {EXPECTED_SPLITS}, got {dict(splits)}")

    cfgs = config.get("configurations")
    if not isinstance(cfgs, list) or len(cfgs) != 4:
        errors.append("benchmark-config must define exactly four configurations for benchmark v1.0.0")
        cfgs = []
    cfg_ids = [c.get("id") for c in cfgs if isinstance(c, dict)]
    required_cfgs = {
        "no_skill",
        "first_principles_baseline",
        "opendeepmind_full",
        "opendeepmind_no_triz_ablation",
    }
    if set(cfg_ids) != required_cfgs:
        errors.append(f"configuration set mismatch: expected {sorted(required_cfgs)}, got {sorted(cfg_ids)}")

    cfg_by_id = {c.get("id"): c for c in cfgs if isinstance(c, dict)}
    baseline = cfg_by_id.get("first_principles_baseline", {})
    sha = baseline.get("commit", "")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        errors.append("external first-principles baseline must be pinned to a 40-hex commit")

    full = cfg_by_id.get("opendeepmind_full", {})
    if full.get("triz_policy") != "explicit-only":
        errors.append("opendeepmind_full must preserve explicit-only TRIZ policy")

    ablation = cfg_by_id.get("opendeepmind_no_triz_ablation", {})
    if ablation.get("case_categories") != ["triz-positive"]:
        errors.append("no-TRIZ ablation must be limited to triz-positive cases")
    if "triz" not in ablation.get("disabled_modules", []):
        errors.append("no-TRIZ ablation must explicitly disable the TRIZ module")
    if ablation.get("forced_route") != "p":
        errors.append("no-TRIZ ablation must force the P route")
    if ablation.get("score_routing_accuracy") is not False:
        errors.append("routing accuracy must be disabled for the intentional no-TRIZ ablation")

    comparisons = config.get("comparisons", [])
    comparison_ids = {c.get("id") for c in comparisons if isinstance(c, dict)}
    if comparison_ids != {"full_vs_no_skill", "full_vs_first_principles_baseline", "triz_module_ablation"}:
        errors.append("benchmark comparisons must include the two baselines and TRIZ ablation")

    if config.get("repetitions", 0) < 3:
        errors.append("benchmark repetitions must be at least 3")
    if config.get("publication", {}).get("publish_scores_before_real_runs") is not False:
        errors.append("publication policy must forbid publishing scores before real runs")

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(json.dumps({"ok": False, "errors": len(errors), "warnings": len(warnings)}))
        return 1

    print(json.dumps({
        "ok": True,
        "errors": 0,
        "warnings": len(warnings),
        "cases": len(evals),
        "categories": dict(categories),
        "splits": dict(splits),
        "configurations": len(cfgs),
        "repetitions": config.get("repetitions"),
        "triz_ablation": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
