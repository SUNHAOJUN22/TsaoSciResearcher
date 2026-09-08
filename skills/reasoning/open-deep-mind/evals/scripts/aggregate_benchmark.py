#!/usr/bin/env python3
"""Aggregate completed OpenDeepMind benchmark run/grading artifacts."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "benchmark-config.json").read_text(encoding="utf-8"))
EVALS = json.loads((ROOT / "evals.json").read_text(encoding="utf-8"))
CASE_MAP = {c["id"]: c for c in EVALS["evals"]}


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def rate(values: list[bool]) -> float | None:
    return statistics.fmean(1.0 if x else 0.0 for x in values) if values else None


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def numeric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def get_assertion_pass_rate(grade: dict[str, Any]) -> float | None:
    return numeric(grade.get("summary", {}).get("pass_rate"))


def build_metrics(rows: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    pass_rates: list[float] = []
    blocker_flags: list[bool] = []
    route_flags: list[bool] = []
    false_triz_flags: list[bool] = []
    leakage_flags: list[bool] = []
    judge_scores: list[float] = []
    rival_flags: list[bool] = []
    falsifier_flags: list[bool] = []
    tokens: list[float] = []
    durations: list[float] = []
    case_pass_flags: list[bool] = []

    for _case, run, grade in rows:
        value = get_assertion_pass_rate(grade)
        if value is not None:
            pass_rates.append(value)
        blocker_flags.append(bool(grade.get("red_blockers", [])))
        rc = grade.get("route_correct")
        if isinstance(rc, bool):
            route_flags.append(rc)
        ft = grade.get("triz_false_activation")
        if isinstance(ft, bool):
            false_triz_flags.append(ft)
        ml = grade.get("module_leakage")
        if isinstance(ml, bool):
            leakage_flags.append(ml)
        js = numeric(grade.get("judge_score"))
        if js is not None:
            judge_scores.append(js)
        rp = grade.get("rival_model_present")
        if isinstance(rp, bool):
            rival_flags.append(rp)
        fp = grade.get("falsifier_present")
        if isinstance(fp, bool):
            falsifier_flags.append(fp)
        t = numeric(run.get("total_tokens"))
        if t is not None:
            tokens.append(t)
        d = numeric(run.get("duration_ms"))
        if d is not None:
            durations.append(d)
        cp = grade.get("summary", {}).get("case_passed")
        if isinstance(cp, bool):
            case_pass_flags.append(cp)

    return {
        "runs": len(rows),
        "case_pass_rate": rate(case_pass_flags),
        "assertion_pass_rate": mean(pass_rates),
        "red_blocker_rate": rate(blocker_flags),
        "routing_accuracy": rate(route_flags),
        "triz_false_activation_rate": rate(false_triz_flags),
        "module_leakage_rate": rate(leakage_flags),
        "judge_score_mean": mean(judge_scores),
        "rival_model_coverage": rate(rival_flags),
        "falsifier_coverage": rate(falsifier_flags),
        "mean_tokens": mean(tokens),
        "mean_duration_ms": mean(durations),
    }


def paired_comparison(
    left_rows: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]],
    right_rows: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    common = sorted(set(left_rows) & set(right_rows))
    assertion_deltas: list[float] = []
    judge_deltas: list[float] = []
    token_deltas: list[float] = []
    duration_deltas: list[float] = []
    left_case_wins = 0
    right_case_wins = 0
    ties = 0

    for key in common:
        _lc, lrun, lgrade = left_rows[key]
        _rc, rrun, rgrade = right_rows[key]
        la, ra = get_assertion_pass_rate(lgrade), get_assertion_pass_rate(rgrade)
        if la is not None and ra is not None:
            assertion_deltas.append(la - ra)
        lj, rj = numeric(lgrade.get("judge_score")), numeric(rgrade.get("judge_score"))
        if lj is not None and rj is not None:
            judge_deltas.append(lj - rj)
        lt, rt = numeric(lrun.get("total_tokens")), numeric(rrun.get("total_tokens"))
        if lt is not None and rt is not None:
            token_deltas.append(lt - rt)
        ld, rd = numeric(lrun.get("duration_ms")), numeric(rrun.get("duration_ms"))
        if ld is not None and rd is not None:
            duration_deltas.append(ld - rd)

        lp = lgrade.get("summary", {}).get("case_passed")
        rp = rgrade.get("summary", {}).get("case_passed")
        if isinstance(lp, bool) and isinstance(rp, bool):
            if lp and not rp:
                left_case_wins += 1
            elif rp and not lp:
                right_case_wins += 1
            else:
                ties += 1

    return {
        "paired_runs": len(common),
        "left_case_pass_wins": left_case_wins,
        "right_case_pass_wins": right_case_wins,
        "case_pass_ties": ties,
        "mean_assertion_pass_rate_delta_left_minus_right": mean(assertion_deltas),
        "mean_judge_score_delta_left_minus_right": mean(judge_deltas),
        "mean_tokens_delta_left_minus_right": mean(token_deltas),
        "mean_duration_ms_delta_left_minus_right": mean(duration_deltas),
        "blind_pairwise_result": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", help="iteration-N directory")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        parser.error(f"workspace does not exist: {workspace}")

    manifest = read_json(workspace / "manifest.json")
    if not manifest:
        parser.error("workspace manifest.json is missing or invalid; create the workspace with create_workspace.py")
    if manifest.get("benchmark_version") != CONFIG.get("benchmark_version"):
        parser.error("workspace benchmark_version does not match the current benchmark definition")

    expected_slots = manifest.get("expected_run_slots")
    if not isinstance(expected_slots, list) or not expected_slots:
        parser.error("workspace manifest has no expected_run_slots; recreate it with the current create_workspace.py")

    by_cfg: dict[str, list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    indexed: dict[str, dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = defaultdict(dict)
    incomplete: list[str] = []
    metadata_errors: list[str] = []

    for slot in expected_slots:
        if not isinstance(slot, dict):
            metadata_errors.append(f"invalid expected slot: {slot!r}")
            continue
        case_id = slot.get("case_id")
        cfg = slot.get("configuration")
        rep = slot.get("repetition")
        if not isinstance(case_id, str) or not isinstance(cfg, str) or not isinstance(rep, int):
            metadata_errors.append(f"invalid expected slot fields: {slot!r}")
            continue
        run_dir = workspace / f"eval-{case_id}" / cfg / f"run-{rep}"
        run = read_json(run_dir / "run_record.json")
        grade = read_json(run_dir / "grading.json")
        if not run or not grade:
            incomplete.append(str(run_dir))
            continue
        case = CASE_MAP.get(case_id)
        if not case:
            metadata_errors.append(f"unknown case in manifest: {case_id}")
            continue
        if run.get("case_id") != case_id or run.get("configuration") != cfg or run.get("repetition") != rep:
            metadata_errors.append(f"run metadata mismatch: {run_dir}")
            continue
        if grade.get("case_id") != case_id or grade.get("configuration") != cfg:
            metadata_errors.append(f"grading metadata mismatch: {run_dir}")
            continue
        row = (case, run, grade)
        by_cfg[cfg].append(row)
        indexed[cfg][(case_id, rep)] = row

    configurations = {cfg: build_metrics(rows) for cfg, rows in sorted(by_cfg.items())}

    comparison_results: dict[str, Any] = {}
    for comparison in CONFIG.get("comparisons", []):
        if not isinstance(comparison, dict):
            continue
        cid = comparison.get("id")
        left = comparison.get("left")
        right = comparison.get("right")
        if not all(isinstance(x, str) for x in (cid, left, right)):
            continue
        comparison_results[cid] = {
            "left": left,
            "right": right,
            "scope": comparison.get("scope"),
            **paired_comparison(indexed.get(left, {}), indexed.get(right, {})),
        }

    complete_run_count = sum(len(rows) for rows in by_cfg.values())
    expected_run_count = len(expected_slots)
    expected_cfg_ids = {slot.get("configuration") for slot in expected_slots if isinstance(slot, dict)}
    observed_cfg_ids = set(configurations)
    all_expected_configs_present = observed_cfg_ids == expected_cfg_ids

    artifact_set_complete = (
        expected_run_count > 0
        and complete_run_count == expected_run_count
        and not incomplete
        and not metadata_errors
        and all_expected_configs_present
    )
    publication_blockers: list[str] = []
    if not artifact_set_complete:
        publication_blockers.append("ARTIFACT_SET_INCOMPLETE_OR_INCONSISTENT")
    # This dependency-free aggregator validates artifact completeness only. It cannot
    # independently verify provider identity, grader independence, holdout sealing,
    # or an authorized release signature, so it must never self-authorize publication.
    publication_blockers.append("INDEPENDENT_PUBLICATION_ATTESTATION_NOT_VERIFIED")

    result = {
        "benchmark_version": CONFIG["benchmark_version"],
        "generated_from": str(workspace),
        "manifest_split": manifest.get("split"),
        "expected_runs": expected_run_count,
        "complete_runs": complete_run_count,
        "configurations": configurations,
        "comparisons": comparison_results,
        "incomplete_run_directories": sorted(set(incomplete)),
        "metadata_errors": metadata_errors,
        "artifact_set_complete": artifact_set_complete,
        "publication_status": (
            "EVIDENCE_COMPLETE_AWAITING_INDEPENDENT_ATTESTATION"
            if artifact_set_complete
            else "INCOMPLETE_ARTIFACT_SET"
        ),
        "publication_blockers": publication_blockers,
        "publication_ready": False,
    }

    output = Path(args.output).resolve() if args.output else workspace / "benchmark.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "expected_runs": expected_run_count,
        "complete_runs": complete_run_count,
        "incomplete": len(set(incomplete)),
        "metadata_errors": len(metadata_errors),
        "configurations": sorted(configurations),
        "artifact_set_complete": result["artifact_set_complete"],
        "publication_status": result["publication_status"],
        "publication_ready": result["publication_ready"],
    }, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
