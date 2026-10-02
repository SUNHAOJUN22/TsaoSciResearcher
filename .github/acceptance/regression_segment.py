"""Run a source-pinned regression segment; elapsed test time is not CPU time."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPOSITORIES = (
    "AspenOps-Agent", "TsaoSciComputation", "TSAO-PROCESSING-SKILL",
    "ResinDB-Pro-by-SunHJ", "TsaoDFT_skill", "TsaoSciResearcher",
)
SEGMENT_SECONDS = 10800


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=60).strip()


def source_check(root: Path, sha: str, *, remote: bool) -> str:
    if git(root, "rev-parse", "HEAD") != sha:
        raise ValueError("checkout SHA changed")
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("source worktree is not clean")
    if remote:
        refs = git(root, "ls-remote", "--heads", "origin").splitlines()
        if len(refs) != 1 or refs[0].split() != [sha, "refs/heads/main"]:
            raise ValueError("STALE_OR_NONSOLE_MAIN: remote source identity changed")
    return git(root, "rev-parse", "HEAD^{tree}")


def junit_counts(path: Path) -> dict[str, int]:
    data = path.read_bytes()
    if len(data) > 50_000_000 or b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("unsafe or oversized JUnit witness")
    root = ET.fromstring(data)
    for suite in root.iter():
        if suite.tag in {"testsuite", "testsuites"}:
            if int(suite.get("failures", "0")) or int(suite.get("errors", "0")):
                raise ValueError("JUnit suite reports failures or errors")
    cases = root.findall(".//testcase")
    counts = {"passed": 0, "skipped": 0, "failed": 0}
    for case in cases:
        key = "failed" if case.find("failure") is not None or case.find("error") is not None else (
            "skipped" if case.find("skipped") is not None else "passed"
        )
        counts[key] += 1
    if counts["failed"] or not counts["passed"]:
        raise ValueError(f"failing or empty JUnit witness: {counts}")
    return counts


def commands(repo: str, root: Path, output: Path, cycle: int) -> list[tuple[list[str], Path]]:
    prefix = ["uv", "run", "--no-sync", "python"] if repo == "AspenOps-Agent" else [sys.executable]
    if repo == "ResinDB-Pro-by-SunHJ":
        report = output / f"junit-{cycle}-0.xml"
        return [(["node", "node_modules/vitest/vitest.mjs", "run", "--pool=forks", "--maxWorkers=1",
                  "--reporter=junit", "--outputFile", str(report)], report)]
    suites = ["tests", *[str(p.relative_to(root)) for p in sorted((root / "skills").glob("*/tests")) if p.is_dir()]] if repo == "TsaoDFT_skill" else [None]
    result = []
    for index, suite in enumerate(suites):
        report = output / f"junit-{cycle}-{index}.xml"
        command = [*prefix, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}"]
        if repo == "AspenOps-Agent":
            command.extend(["-W", "error::ResourceWarning"])
        if repo == "TsaoSciResearcher":
            command.extend(["-p", "hypothesis.extra.pytestplugin"])
        if suite:
            command.extend(["--import-mode=importlib", suite])
        result.append((command, report))
    return result


def run_command(command: list[str], root: Path, log: Path, env: dict[str, str]) -> float:
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(command, cwd=root, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=1800)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
    seconds = time.monotonic() - started
    if code:
        raise ValueError(f"test command failed with exit {code}; see {log.name}")
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return seconds
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


def validate_previous(previous: dict, expected: dict) -> None:
    for key in ("repository", "sha", "tree", "environment", "run_id", "run_attempt", "orchestration_sha"):
        if previous.get(key) != expected[key]:
            raise ValueError(f"predecessor identity mismatch: {key}")
    seconds = previous.get("successful_test_process_seconds")
    if (previous.get("phase") != 1 or previous.get("status") != "SEGMENT_COMPLETE"
            or isinstance(seconds, bool) or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds) or seconds < SEGMENT_SECONDS):
        raise ValueError("predecessor is not a completed three-hour segment")


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
    root, output = args.root.resolve(), args.output.resolve()
    if output == root or root in output.parents or (output / "receipt.json").exists():
        parser.error("output must be fresh and outside the target worktree")
    output.mkdir(parents=True, exist_ok=True)
    receipt = dict(repository=args.repo, sha=args.sha, phase=args.phase, status="NOT_STARTED",
                   successful_test_process_seconds=0.0, cycles=0, run_id=os.environ.get("GITHUB_RUN_ID"),
                   run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), orchestration_sha=os.environ.get("GITHUB_SHA"),
                   scope="segmented Linux regression; not uninterrupted service soak or solver certification")
    try:
        receipt["tree"] = source_check(root, args.sha, remote=True)
        receipt["environment"] = environment(root, args.repo)
        if args.phase == 2:
            if args.previous is None:
                raise ValueError("phase two requires the phase-one receipt")
            previous = json.loads(args.previous.read_text(encoding="utf-8"))
            validate_previous(previous, receipt)
            receipt["predecessor_sha256"] = digest(args.previous)
        elif args.previous is not None:
            raise ValueError("phase one must not import predecessor time")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        if args.repo == "TsaoSciResearcher":
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        receipt["status"] = "RUNNING"
        write_json(output / "receipt.json", receipt)
        checked = time.monotonic()
        while receipt["successful_test_process_seconds"] < args.seconds:
            cycle = receipt["cycles"] + 1
            for index, (command, report) in enumerate(commands(args.repo, root, output, cycle)):
                log = output / f"test-{cycle}-{index}.log"
                seconds = run_command(command, root, log, env)
                counts = junit_counts(report)
                source_check(root, args.sha, remote=False)
                record = dict(cycle=cycle, command=command, seconds=seconds, counts=counts,
                              log=log.name, log_sha256=digest(log), junit=report.name, junit_sha256=digest(report))
                with (output / "iterations.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
                receipt["successful_test_process_seconds"] += seconds
            receipt["cycles"] = cycle
            if time.monotonic() - checked >= 300:
                source_check(root, args.sha, remote=True)
                checked = time.monotonic()
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
    write_json(output / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2), flush=True)
    return 0 if receipt["status"] in {"SEGMENT_COMPLETE", "SMOKE_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
