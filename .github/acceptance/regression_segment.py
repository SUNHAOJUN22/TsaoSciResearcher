"""Run a source-pinned regression segment; elapsed test-process time is not CPU time."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from pytest_witness import collector_digest, load_events, pytest_counts, verify_invocation
from strict_json import loads as strict_json_loads

REPOSITORIES = (
    "AspenOps-Agent",
    "TsaoSciComputation",
    "TSAO-PROCESSING-SKILL",
    "ResinDB-Pro-by-SunHJ",
    "TsaoDFT_skill",
    "TsaoSciResearcher",
    "OpenDeepMind_skill",
)
DFT_SUITES = (
    "tests",
    "skills/tsao-dft-catalysis-profile/tests",
    "skills/tsao-dft-hpc-provenance/tests",
    "skills/tsao-dft-kinetics-multiscale/tests",
    "skills/tsao-dft-ml-active-learning/tests",
    "skills/tsao-dft-researcher/tests",
    "skills/tsao-dft-suite/tests",
    "skills/tsao-periodic-dft-materials/tests",
    "skills/tsao-structure-prep/tests",
)
SCHEMA = "tsao.regression-segment/v2"
SEGMENT_SECONDS = 10800
SCOPE = "segmented Linux software regression; not CPU time, uninterrupted service soak, solver execution or scientific certification"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def utc_seconds(value: object) -> float:
    if not isinstance(value, str):
        raise ValueError("missing UTC timestamp")
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.utcoffset() is None or date.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must explicitly identify UTC")
    return date.timestamp()


def validate_clocks(record: dict) -> tuple[float, float, float]:
    start, finish = (record.get(key) for key in ("monotonic_start_ns", "monotonic_end_ns"))
    if type(start) is not int or type(finish) is not int or start < 0 or finish <= start:
        raise ValueError("invalid monotonic interval")
    seconds = (finish - start) / 1_000_000_000
    utc_start, utc_finish = utc_seconds(record.get("started_at")), utc_seconds(record.get("finished_at"))
    if utc_finish < utc_start or abs(utc_finish - utc_start - seconds) > 1:
        raise ValueError("UTC and monotonic clocks disagree")
    return seconds, utc_start, utc_finish


def git(root: Path, *args: str) -> str:
    # Acceptance must observe the worktree without trusting a local fsmonitor
    # cache or changing the caller's repository configuration.
    return subprocess.check_output(
        ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args], text=True, timeout=60
    ).strip()


def source_check(root: Path, sha: str, *, remote: bool) -> str:
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("source directory must be the repository worktree root")
    if git(root, "rev-parse", "HEAD") != sha:
        raise ValueError("checkout SHA changed")
    # Git status intentionally omits paths carrying these index flags. Reject
    # them without clearing user flags or silently changing the tested checkout.
    flags = git(root, "ls-files", "-v", "-z").split("\0")
    if any(item and (item[0].islower() or item[0] == "S") for item in flags):
        raise ValueError("source index contains assume-unchanged or skip-worktree paths")
    if git(root, "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"):
        raise ValueError("source worktree is not clean")
    if remote:
        refs = git(root, "ls-remote", "--heads", "origin").splitlines()
        if len(refs) != 1 or refs[0].split() != [sha, "refs/heads/main"]:
            raise ValueError("STALE_OR_NONSOLE_MAIN: remote source identity changed")
    return git(root, "rev-parse", "HEAD^{tree}")


def junit_counts(path: Path, events: dict | None = None) -> dict[str, int]:
    if path.is_symlink() or path.stat().st_size > 50_000_000:
        raise ValueError("unsafe or oversized JUnit witness")
    data = path.read_bytes()
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("unsafe XML declaration")
    root = ET.fromstring(data)
    if root.tag not in {"testsuite", "testsuites"} or list(root.iter("failure")) or list(root.iter("error")):
        raise ValueError("invalid or unsuccessful JUnit witness")
    if events is not None:
        return pytest_counts(root, events)
    cases = list(root.iter("testcase"))
    counts = {"passed": 0, "skipped": 0, "failed": 0}
    for case in cases:
        statuses = list(case.iter("skipped"))
        if (
            len(list(case.iter("testcase"))) != 1
            or len(statuses) > 1
            or any(status not in list(case) for status in statuses)
        ):
            raise ValueError("nested testcase or inconsistent status elements")
        counts["skipped" if statuses else "passed"] += 1
    for suite in root.iter():
        if suite.tag not in {"testsuite", "testsuites"}:
            continue
        leaves = list(suite.iter("testcase"))
        expected = {
            "tests": len(leaves),
            "skipped": sum(case.find("skipped") is not None for case in leaves),
            "failures": 0,
            "errors": 0,
        }
        for key, wanted in expected.items():
            declared = suite.get(key)
            if declared is not None and (not re.fullmatch(r"[0-9]+", declared) or int(declared) != wanted):
                raise ValueError(f"JUnit {key} summary disagrees with real leaf cases")
    if not counts["passed"]:
        raise ValueError("empty or entirely skipped JUnit witness")
    return counts


def commands(repo: str, root: Path, output: Path, cycle: int) -> list[tuple[list[str], Path]]:
    if repo not in REPOSITORIES:
        raise ValueError("unsupported repository")
    prefix = ["uv", "run", "--no-sync", "python"] if repo == "AspenOps-Agent" else [sys.executable]
    if repo == "ResinDB-Pro-by-SunHJ":
        report = output / f"junit-{cycle}-0.xml"
        return [
            (
                [
                    "node",
                    "node_modules/vitest/vitest.mjs",
                    "run",
                    "--pool=forks",
                    "--maxWorkers=1",
                    "--reporter=junit",
                    "--outputFile",
                    str(report),
                ],
                report,
            )
        ]
    suites = (
        DFT_SUITES
        if repo == "TsaoDFT_skill"
        else (("open-deep-mind/tests",) if repo == "OpenDeepMind_skill" else (None,))
    )
    result = []
    for index, suite in enumerate(suites):
        report = output / f"junit-{cycle}-{index}.xml"
        command = [
            *prefix,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "tsao_acceptance_pytest_events",
            f"--tsao-event-report={report}.events.json",
            f"--junitxml={report}",
        ]
        if repo == "AspenOps-Agent":
            command.extend(["-W", "error::ResourceWarning"])
        if repo == "TsaoSciResearcher":
            command.extend(["-p", "hypothesis.extra.pytestplugin"])
        if repo == "TsaoDFT_skill":
            command.append("--import-mode=importlib")
        if suite:
            command.append(suite)
        result.append((command, report))
    return result


def normalize_argv(repo: str, command: list[str], report: Path) -> list[str]:
    if not isinstance(command, list) or not command or any(not isinstance(value, str) for value in command):
        raise ValueError("invalid command argv")
    result = [value.replace(str(report), "$JUNIT") for value in command]
    if repo not in {"AspenOps-Agent", "ResinDB-Pro-by-SunHJ"}:
        if not Path(command[0]).is_absolute() or not re.fullmatch(
            r"python(?:[0-9]+(?:\.[0-9]+)*)?", Path(command[0]).name
        ):
            raise ValueError("invalid Python executable")
        result[0] = "$PYTHON"
    return result


def normalized_commands(repo: str) -> list[list[str]]:
    return [
        normalize_argv(repo, command, report)
        for command, report in commands(repo, Path("$SOURCE"), Path("$OUTPUT"), 1)
    ]


def run_command(command: list[str], root: Path, log: Path, env: dict[str, str]) -> dict:
    timing = {"started_at": utc_now(), "monotonic_start_ns": time.monotonic_ns()}
    with log.open("x", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command, cwd=root, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            code = process.wait(timeout=1800)
        except BaseException:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
    timing.update(monotonic_end_ns=time.monotonic_ns(), finished_at=utc_now(), exit_code=code)
    if code != 0:
        raise ValueError(f"test command failed with exit {code}; see {log.name}")
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        timing["seconds"] = validate_clocks(timing)[0]
        return timing
    os.killpg(process.pid, signal.SIGKILL)
    raise ValueError(f"test command left a live process group; see {log.name}")


def environment(root: Path, repo: str) -> str:
    prefix = ["uv", "run", "--no-sync", "python"] if repo == "AspenOps-Agent" else [sys.executable]
    code = "import importlib.metadata as m,json,platform;print(json.dumps([platform.python_version(),sorted((d.metadata['Name'].lower(),d.version) for d in m.distributions())],sort_keys=True))"
    payload = subprocess.check_output([*prefix, "-c", code], cwd=root, timeout=60)
    if repo == "ResinDB-Pro-by-SunHJ":
        payload += subprocess.check_output(["node", "--version"], timeout=30)
        payload += (root / "package-lock.json").read_bytes()
    return hashlib.sha256(payload).hexdigest()


def target_python(root: Path, repo: str) -> str:
    if repo == "AspenOps-Agent":
        return subprocess.check_output(
            ["uv", "run", "--no-sync", "python", "-c", "import sys; print(sys.executable)"],
            cwd=root,
            text=True,
            timeout=60,
        ).strip()
    return sys.executable


def validate_previous(previous: dict, expected: dict) -> None:
    for key in (
        "repository",
        "sha",
        "tree",
        "environment",
        "run_id",
        "run_attempt",
        "orchestration_sha",
        "python_executable",
        "target_python_executable",
        "pytest_collector_sha256",
    ):
        if previous.get(key) != expected.get(key):
            raise ValueError(f"predecessor identity mismatch: {key}")
    seconds = previous.get("successful_test_process_seconds")
    if (
        previous.get("schema") != SCHEMA
        or previous.get("phase") != 1
        or previous.get("status") != "SEGMENT_COMPLETE"
        or type(seconds) not in (int, float)
        or not math.isfinite(seconds)
        or seconds < SEGMENT_SECONDS
    ):
        raise ValueError("predecessor is not a completed v2 three-hour segment")
    if previous.get("segment_id") == expected.get("segment_id") or utc_seconds(
        previous.get("finished_at")
    ) > utc_seconds(expected.get("started_at")):
        raise ValueError("predecessor overlaps or duplicates the next segment")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", choices=REPOSITORIES, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", type=int, choices=(1, 2), required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--seconds", type=int, default=SEGMENT_SECONDS)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.sha) or not 1 <= args.seconds <= SEGMENT_SECONDS:
        parser.error("require a full commit SHA and 1..10800 seconds")
    if not args.root.is_absolute() or not args.output.is_absolute():
        parser.error("source and output directories must be absolute")
    root, output = args.root.resolve(), args.output.resolve()
    if (
        output == root
        or root in output.parents
        or (output / "receipt.json").exists()
        or (output / "iterations.jsonl").exists()
    ):
        parser.error("output must be fresh and outside the target worktree")
    output.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": SCHEMA,
        "segment_id": uuid.uuid4().hex,
        "repository": args.repo,
        "sha": args.sha,
        "phase": args.phase,
        "started_at": utc_now(),
        "monotonic_start_ns": time.monotonic_ns(),
        "status": "NOT_STARTED",
        "job_id": f"{args.repo}:{args.phase}:{os.environ.get('GITHUB_JOB', 'local')}",
        "python_executable": sys.executable,
        "target_python_executable": target_python(root, args.repo),
        "output_directory": str(output),
        "source_directory": str(root),
        "pytest_collector_sha256": None if args.repo == "ResinDB-Pro-by-SunHJ" else collector_digest(),
        "expected_commands": normalized_commands(args.repo),
        "successful_test_process_seconds": 0.0,
        "cycles": 0,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "orchestration_sha": os.environ.get("GITHUB_SHA"),
        "scope": SCOPE,
    }
    try:
        for key in ("run_id", "run_attempt"):
            if not re.fullmatch(r"[1-9][0-9]*", str(receipt[key] or "")):
                raise ValueError(f"require positive Actions identity: {key}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(receipt["orchestration_sha"] or "")):
            raise ValueError("require exact orchestration SHA")
        receipt["tree"] = source_check(root, args.sha, remote=True)
        receipt["environment"] = environment(root, args.repo)
        if args.phase == 2:
            if args.previous is None:
                raise ValueError("phase two requires the phase-one receipt")
            from verify_segments import verified_elapsed

            previous = strict_json_loads(args.previous.read_text(encoding="utf-8"))
            validate_previous(previous, receipt)
            verified_elapsed(args.previous, previous)
            receipt["predecessor_sha256"] = digest(args.previous)
        elif args.previous is not None:
            raise ValueError("phase one must not import predecessor time")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent) + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
        )
        if args.repo == "TsaoSciResearcher":
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        receipt["status"] = "RUNNING"
        write_json(output / "receipt.json", receipt)
        checked = time.monotonic()
        while receipt["successful_test_process_seconds"] < args.seconds:
            cycle = receipt["cycles"] + 1
            for index, (command, report) in enumerate(commands(args.repo, root, output, cycle)):
                log = output / f"test-{cycle}-{index}.log"
                timing = run_command(command, root, log, env)
                events = None
                witness = Path(str(report) + ".events.json")
                if args.repo != "ResinDB-Pro-by-SunHJ":
                    events = load_events(witness)
                    verify_invocation(events, command, str(root), receipt["target_python_executable"])
                counts = junit_counts(report, events)
                source_check(root, args.sha, remote=False)
                normalized = normalize_argv(args.repo, command, report)
                record = dict(
                    schema=SCHEMA,
                    iteration_id=uuid.uuid4().hex,
                    segment_id=receipt["segment_id"],
                    cycle=cycle,
                    command_index=index,
                    command=command,
                    argv_sha256=canonical_digest(command),
                    normalized_argv=normalized,
                    normalized_argv_sha256=canonical_digest(normalized),
                    environment=receipt["environment"],
                    sha=args.sha,
                    counts=counts,
                    **timing,
                    log=log.name,
                    log_sha256=digest(log),
                    junit=report.name,
                    junit_sha256=digest(report),
                )
                if events is not None:
                    record.update(pytest_events=witness.name, pytest_events_sha256=digest(witness))
                with (output / "iterations.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
                receipt["successful_test_process_seconds"] += timing["seconds"]
                if time.monotonic() - checked >= 300:
                    source_check(root, args.sha, remote=True)
                    checked = time.monotonic()
            receipt["cycles"] = cycle
            write_json(output / "receipt.json", receipt)
            print(json.dumps(receipt, sort_keys=True), flush=True)
        source_check(root, args.sha, remote=True)
        if environment(root, args.repo) != receipt["environment"]:
            raise ValueError("dependency environment changed during testing")
        receipt["iterations_sha256"] = digest(output / "iterations.jsonl")
        receipt["status"] = "SEGMENT_COMPLETE" if args.seconds == SEGMENT_SECONDS else "SMOKE_ONLY"
    except Exception as exc:
        receipt["status"] = "FAILED"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    receipt.update(monotonic_end_ns=time.monotonic_ns(), finished_at=utc_now())
    write_json(output / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2), flush=True)
    return 0 if receipt["status"] in {"SEGMENT_COMPLETE", "SMOKE_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
