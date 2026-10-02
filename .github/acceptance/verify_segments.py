"""Independently validate twelve receipts and their original test witnesses."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
from pathlib import Path

from regression_segment import REPOSITORIES, SEGMENT_SECONDS, digest, junit_counts, validate_previous, write_json


def verified_elapsed(path: Path, receipt: dict) -> float:
    ledger = path.parent / "iterations.jsonl"
    if digest(ledger) != receipt.get("iterations_sha256"):
        raise ValueError("iteration ledger digest mismatch")
    elapsed = 0.0
    cycles = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        seconds = record.get("seconds")
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("invalid elapsed test time")
        for field in ("log", "junit"):
            name = record[field]
            if not isinstance(name, str) or Path(name).name != name or name in {".", ".."}:
                raise ValueError("witness path must be a local filename")
            witness = path.parent / name
            if witness.is_symlink() or digest(witness) != record[field + "_sha256"]:
                raise ValueError("witness digest mismatch")
        if junit_counts(path.parent / record["junit"]) != record.get("counts"):
            raise ValueError("JUnit counts mismatch")
        cycle = record.get("cycle")
        if type(cycle) is not int or cycle < 1:
            raise ValueError("invalid cycle number")
        cycles.add(cycle)
        elapsed += seconds
    reported = receipt.get("successful_test_process_seconds")
    count = receipt.get("cycles")
    if (type(count) is not int or count < 1 or cycles != set(range(1, count + 1))
            or type(reported) not in (int, float) or not math.isfinite(reported)
            or not math.isclose(elapsed, reported, rel_tol=0.0, abs_tol=1e-6)
            or elapsed < SEGMENT_SECONDS):
        raise ValueError("elapsed time or cycle inventory is incomplete")
    return elapsed


def verify(root: Path, plan: dict, run_id: str, attempt: str, orchestration_sha: str) -> list[dict]:
    if set(plan) != set(REPOSITORIES) or not run_id.isdigit() or not attempt.isdigit():
        raise ValueError("exactly six repositories and an Actions run identity are required")
    paths = sorted(root.rglob("receipt.json"))
    if len(paths) != 12:
        raise ValueError("exactly twelve independent segment receipts are required")
    grouped = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError("symlink receipt")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        repo, phase = receipt.get("repository"), receipt.get("phase")
        if repo not in REPOSITORIES or type(phase) is not int or phase not in (1, 2) or (repo, phase) in grouped:
            raise ValueError("unexpected or duplicate segment identity")
        expected = orchestration_sha if plan[repo] == "SELF" else plan[repo]
        if not re.fullmatch(r"[0-9a-f]{40}", expected) or receipt.get("sha") != expected:
            raise ValueError("receipt does not match the pinned plan")
        if (receipt.get("run_id") != run_id or receipt.get("run_attempt") != attempt
                or receipt.get("orchestration_sha") != orchestration_sha
                or receipt.get("status") != "SEGMENT_COMPLETE"):
            raise ValueError("receipt is not complete for this Actions attempt")
        grouped[repo, phase] = (path, receipt, verified_elapsed(path, receipt))
    rows = []
    for repo in REPOSITORIES:
        path1, first, seconds1 = grouped[repo, 1]
        _, second, seconds2 = grouped[repo, 2]
        validate_previous(first, second)
        if second.get("predecessor_sha256") != digest(path1):
            raise ValueError("predecessor receipt hash mismatch")
        refs = subprocess.check_output(
            ["git", "ls-remote", "--heads", f"https://github.com/SUNHAOJUN22/{repo}.git"],
            text=True, timeout=60,
        ).strip().splitlines()
        if len(refs) != 1 or refs[0].split() != [first["sha"], "refs/heads/main"]:
            raise ValueError(f"STALE_OR_NONSOLE_MAIN: {repo}")
        rows.append(dict(repository=repo, sha=first["sha"], tree=first["tree"],
                         successful_test_process_seconds=seconds1 + seconds2,
                         cycles=first["cycles"] + second["cycles"], status="SEGMENTED_REGRESSION_COMPLETE"))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    summary = dict(status="INCOMPLETE", scope="two sequential three-hour Linux regression segments per repository")
    try:
        summary["repositories"] = verify(
            args.input, json.loads(args.plan.read_text(encoding="utf-8")), os.environ.get("GITHUB_RUN_ID", ""),
            os.environ.get("GITHUB_RUN_ATTEMPT", ""), os.environ.get("GITHUB_SHA", ""),
        )
        summary["status"] = "SEGMENTED_REGRESSION_COMPLETE"
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
    write_json(args.output / "six-hour-summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["status"] == "SEGMENTED_REGRESSION_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
