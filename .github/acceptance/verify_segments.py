"""Verify fourteen independent v2 regression receipts against their raw witnesses."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path

from pytest_witness import collector_digest, load_events, verify_invocation
from regression_segment import (
    REPOSITORIES,
    SCHEMA,
    SCOPE,
    SEGMENT_SECONDS,
    canonical_digest,
    digest,
    junit_counts,
    normalize_argv,
    normalized_commands,
    validate_clocks,
    validate_previous,
    write_json,
)
from strict_json import loads as strict_json_loads


def identity(value: object, pattern: str, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError(f"invalid {label}")
    return value


def unique_id(value: object, identities: set[str]) -> None:
    label = identity(value, r"[0-9a-f]{32}", "globally unique segment/iteration ID")
    if label in identities:
        raise ValueError("duplicate segment/iteration identity")
    identities.add(label)


def witness_file(directory: Path, row: dict, key: str, name: str) -> Path:
    if row.get(key) != name:
        raise ValueError(f"noncanonical {key} filename")
    path = directory / name
    if path.is_symlink() or not path.is_file() or digest(path) != row.get(key + "_sha256"):
        raise ValueError(f"missing or altered {key} witness")
    return path


def verified_elapsed(path: Path, receipt: dict, identities: set[str] | None = None) -> float:
    ids = identities if identities is not None else set()
    if receipt.get("schema") != SCHEMA or receipt.get("status") != "SEGMENT_COMPLETE":
        raise ValueError("only completed v2 segments qualify")
    repo = receipt.get("repository")
    if repo not in REPOSITORIES:
        raise ValueError("unsupported repository identity")
    unique_id(receipt.get("segment_id"), ids)
    for key, width in (("sha", 40), ("tree", 40), ("environment", 64), ("orchestration_sha", 40)):
        identity(receipt.get(key), rf"[0-9a-f]{{{width}}}", key)
    for key in ("run_id", "run_attempt"):
        identity(receipt.get(key), r"[1-9][0-9]*", key)
    for key in ("source_directory", "output_directory", "python_executable", "target_python_executable"):
        if not isinstance(receipt.get(key), str) or not Path(receipt[key]).is_absolute():
            raise ValueError(f"require absolute {key}")
    if receipt.get("pytest_collector_sha256") != (
        None if repo == "ResinDB-Pro-by-SunHJ" else collector_digest()
    ):
        raise ValueError("observer source does not match the control revision")
    expected_commands = normalized_commands(repo)
    if receipt.get("expected_commands") != expected_commands:
        raise ValueError("missing or changed canonical command inventory")
    cycles = receipt.get("cycles")
    if type(cycles) is not int or cycles < 1:
        raise ValueError("invalid cycle count")
    phase_seconds, utc_start, utc_finish = validate_clocks(receipt)
    ledger = path.parent / "iterations.jsonl"
    if (
        ledger.is_symlink()
        or not ledger.is_file()
        or ledger.stat().st_size > 500_000_000
        or digest(ledger) != receipt.get("iterations_sha256")
    ):
        raise ValueError("missing or altered iteration ledger")
    elapsed = 0.0
    previous_ns = receipt["monotonic_start_ns"]
    previous_utc = utc_start
    rows = 0
    with ledger.open(encoding="utf-8") as handle:
        for rows, line in enumerate(handle, 1):
            row = strict_json_loads(line)
            if (
                not isinstance(row, dict)
                or row.get("schema") != SCHEMA
                or row.get("segment_id") != receipt["segment_id"]
            ):
                raise ValueError("iteration schema/segment binding mismatch")
            unique_id(row.get("iteration_id"), ids)
            expected_cycle, expected_index = divmod(rows - 1, len(expected_commands))
            expected_cycle += 1
            if (
                type(row.get("cycle")) is not int
                or type(row.get("command_index")) is not int
                or row["cycle"] != expected_cycle
                or row["command_index"] != expected_index
                or expected_cycle > cycles
            ):
                raise ValueError("iteration order or complete cycle coverage mismatch")
            if row.get("sha") != receipt["sha"] or row.get("environment") != receipt["environment"]:
                raise ValueError("iteration source/environment mismatch")
            seconds, begin, end = validate_clocks(row)
            if (
                seconds > 1801
                or row["monotonic_start_ns"] < previous_ns
                or row["monotonic_end_ns"] > receipt["monotonic_end_ns"]
                or begin < previous_utc
                or end > utc_finish
            ):
                raise ValueError("overlapping, out-of-phase or over-timeout test process")
            previous_ns, previous_utc = row["monotonic_end_ns"], end
            if (
                type(row.get("seconds")) not in (int, float)
                or not math.isfinite(row["seconds"])
                or not math.isclose(row["seconds"], seconds, rel_tol=0, abs_tol=1e-9)
            ):
                raise ValueError("test elapsed seconds disagree with monotonic clock")
            if type(row.get("exit_code")) is not int or row["exit_code"] != 0:
                raise ValueError("unsuccessful test process")
            stem = f"{expected_cycle}-{expected_index}"
            witness_file(path.parent, row, "log", f"test-{stem}.log")
            xml = witness_file(path.parent, row, "junit", f"junit-{stem}.xml")
            original_xml = Path(receipt["output_directory"]) / xml.name
            command = row.get("command")
            normalized = normalize_argv(repo, command, original_xml)
            if (
                normalized != expected_commands[expected_index]
                or row.get("normalized_argv") != normalized
                or row.get("normalized_argv_sha256") != canonical_digest(normalized)
                or row.get("argv_sha256") != canonical_digest(command)
            ):
                raise ValueError("command argv/inventory/hash mismatch")
            if (
                repo not in {"AspenOps-Agent", "ResinDB-Pro-by-SunHJ"}
                and command[0] != receipt["python_executable"]
            ):
                raise ValueError("command interpreter differs from receipt")
            events = None
            if repo != "ResinDB-Pro-by-SunHJ":
                event_path = witness_file(path.parent, row, "pytest_events", f"junit-{stem}.xml.events.json")
                events = load_events(event_path)
                verify_invocation(
                    events, command, receipt["source_directory"], receipt["target_python_executable"]
                )
            if row.get("counts") != junit_counts(xml, events):
                raise ValueError("reported counts disagree with real test witnesses")
            elapsed += seconds
    if rows != cycles * len(expected_commands):
        raise ValueError("missing command or incomplete cycle")
    reported = receipt.get("successful_test_process_seconds")
    if (
        type(reported) not in (int, float)
        or not math.isfinite(reported)
        or not math.isclose(reported, elapsed, rel_tol=0, abs_tol=1e-6)
        or elapsed < SEGMENT_SECONDS
        or elapsed > phase_seconds
    ):
        raise ValueError("unverified or insufficient accumulated test-process time")
    return elapsed


def verify(root: Path, plan: dict, run: str, attempt: str, orchestration: str) -> list[dict]:
    identity(run, r"[1-9][0-9]*", "Actions run ID")
    identity(attempt, r"[1-9][0-9]*", "Actions attempt")
    identity(orchestration, r"[0-9a-f]{40}", "orchestration SHA")
    if not isinstance(plan, dict) or set(plan) != set(REPOSITORIES):
        raise ValueError("plan must contain all and only seven repositories")
    for repo, sha in plan.items():
        if repo == "TsaoSciResearcher" and sha == "SELF":
            continue
        identity(sha, r"[0-9a-f]{40}", "fixed target SHA")
    paths = list(root.rglob("receipt.json"))
    if len(paths) != 14 or any(path.is_symlink() for path in paths):
        raise ValueError("exactly fourteen independent receipt files are required")
    receipts = {}
    elapsed = {}
    identities = set()
    for path in paths:
        receipt = strict_json_loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("invalid receipt document")
        repo, phase = receipt.get("repository"), receipt.get("phase")
        if repo not in plan or type(phase) is not int or phase not in (1, 2) or (repo, phase) in receipts:
            raise ValueError("duplicate or unexpected repository/phase")
        expected_sha = orchestration if plan[repo] == "SELF" else plan[repo]
        if (
            receipt.get("sha") != expected_sha
            or receipt.get("run_id") != run
            or receipt.get("run_attempt") != attempt
            or receipt.get("orchestration_sha") != orchestration
        ):
            raise ValueError("receipt Actions/source identity mismatch")
        if not isinstance(receipt.get("job_id"), str) or not receipt["job_id"].startswith(f"{repo}:{phase}:"):
            raise ValueError("invalid job identity")
        elapsed[(repo, phase)] = verified_elapsed(path, receipt, identities)
        receipts[(repo, phase)] = path, receipt
    result = []
    for repo in REPOSITORIES:
        first_path, first = receipts[(repo, 1)]
        _, second = receipts[(repo, 2)]
        validate_previous(first, second)
        if second.get("predecessor_sha256") != digest(first_path):
            raise ValueError("phase two does not bind the verified predecessor receipt")
        refs = (
            subprocess.check_output(
                ["git", "ls-remote", "--heads", f"https://github.com/SUNHAOJUN22/{repo}.git"],
                text=True,
                timeout=60,
            )
            .strip()
            .splitlines()
        )
        if len(refs) != 1 or refs[0].split() != [first["sha"], "refs/heads/main"]:
            raise ValueError(f"STALE_OR_NONSOLE_MAIN: {repo}")
        result.append(
            {
                "repository": repo,
                "sha": first["sha"],
                "tree": first["tree"],
                "status": "SEGMENTED_REGRESSION_COMPLETE",
                "successful_test_process_seconds": elapsed[(repo, 1)] + elapsed[(repo, 2)],
                "segment_ids": [first["segment_id"], second["segment_id"]],
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--orchestration-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = {"schema": "tsao.seven-repository-acceptance/v2", "status": "INCOMPLETE", "scope": SCOPE}
    try:
        summary["repositories"] = verify(
            args.root,
            strict_json_loads(args.plan.read_text(encoding="utf-8")),
            args.run_id,
            args.run_attempt,
            args.orchestration_sha,
        )
        summary["status"] = "SEGMENTED_REGRESSION_COMPLETE"
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
    write_json(args.output, summary)
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["status"] == "SEGMENTED_REGRESSION_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
