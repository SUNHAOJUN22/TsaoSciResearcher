#!/usr/bin/env python3
"""Run deterministic repository preflight and bounded regression tests."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_ENV = os.environ.copy()
BASE_ENV["PYTHONDONTWRITEBYTECODE"] = "1"
BASE_ENV["PYTHONNOUSERSITE"] = "1"
BASE_ENV["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass(frozen=True, slots=True)
class TestResult:
    path: str
    returncode: int
    seconds: float
    stdout: str
    stderr: str


def run(
    command: Sequence[str], *, env: Mapping[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> None:
    printable = [str(part) for part in command]
    print("+", " ".join(printable), flush=True)
    subprocess.run(
        printable,
        cwd=ROOT,
        check=True,
        env=dict(env or BASE_ENV),
        timeout=timeout,
        shell=False,
    )


def _test_modules(include: str | None, order: str, seed: int) -> list[Path]:
    modules = sorted((ROOT / "tests").glob("test_*.py"), key=lambda path: path.name)
    if include:
        pattern = re.compile(include)
        modules = [path for path in modules if pattern.search(path.name)]
    if not modules:
        raise SystemExit("no test modules matched the requested selection")
    if order == "reverse":
        modules.reverse()
    elif order == "random":
        random.Random(seed).shuffle(modules)
    return modules


def _run_module(path: Path, timeout: int, environment: dict[str, str]) -> TestResult:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-p",
                "hypothesis.extra.pytestplugin",
                str(path.relative_to(ROOT)),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=timeout,
            check=False,
            shell=False,
        )
        return TestResult(
            path=path.relative_to(ROOT).as_posix(),
            returncode=result.returncode,
            seconds=time.perf_counter() - started,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else exc.stdout or ""
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else exc.stderr or ""
        )
        return TestResult(
            path=path.relative_to(ROOT).as_posix(),
            returncode=124,
            seconds=time.perf_counter() - started,
            stdout=stdout,
            stderr=stderr + f"\nmodule exceeded {timeout}s timeout",
        )


def _preflight() -> None:
    run([sys.executable, "scripts/audit_repository.py"])
    with tempfile.TemporaryDirectory(prefix="tsr-pycache-") as directory:
        environment = BASE_ENV.copy()
        environment["PYTHONPYCACHEPREFIX"] = directory
        run(
            [sys.executable, "-m", "compileall", "-q", "scripts", "tsao_researcher", "tests"],
            env=environment,
        )
    run([sys.executable, "scripts/validate_structure.py"])
    run([sys.executable, "scripts/generate_checksums.py", "--check"])
    run([sys.executable, "scripts/build_capability_index.py", "--check"])
    run([sys.executable, "scripts/route_task.py", "--self-test"])
    run([sys.executable, "scripts/validate_figure.py", "examples/figure-contract.json"])


def _write_report(path: str | None, payload: dict[str, object]) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--order", choices=("normal", "reverse", "random"), default="normal")
    parser.add_argument("--seed", type=int, default=20260721)
    parser.add_argument("--module-timeout", type=int, default=120)
    parser.add_argument("--include", help="Regular expression matched against test module filenames.")
    parser.add_argument("--json-out")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--skip-release-validation", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.jobs <= 32:
        raise SystemExit("--jobs must be between 1 and 32")
    if not 5 <= args.module_timeout <= 1800:
        raise SystemExit("--module-timeout must be between 5 and 1800 seconds")

    started = time.perf_counter()
    if not args.skip_preflight:
        _preflight()

    modules = _test_modules(args.include, args.order, args.seed)
    environment = BASE_ENV.copy()
    environment["TSR_TEST_ORDER_SEED"] = str(args.seed)
    workers = min(args.jobs, len(modules))
    print(
        f"running {len(modules)} isolated test modules with {workers} workers "
        f"in {args.order} submission order",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tsr-test") as pool:
        results = list(pool.map(lambda path: _run_module(path, args.module_timeout, environment), modules))

    failures = [result for result in results if result.returncode != 0]
    for result in sorted(results, key=lambda item: item.path):
        status = "PASS" if result.returncode == 0 else f"FAIL({result.returncode})"
        print(f"{status:10s} {result.seconds:8.3f}s {result.path}")
        if result.returncode != 0:
            if result.stdout:
                print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")

    payload: dict[str, object] = {
        "status": "FAIL" if failures else "PASS",
        "order": args.order,
        "seed": args.seed,
        "jobs": workers,
        "module_timeout_seconds": args.module_timeout,
        "seconds": round(time.perf_counter() - started, 6),
        "modules": [
            {
                "path": result.path,
                "returncode": result.returncode,
                "seconds": round(result.seconds, 6),
            }
            for result in results
        ],
    }
    _write_report(args.json_out, payload)
    if failures:
        raise SystemExit(f"{len(failures)} test module(s) failed")

    if not args.skip_release_validation:
        run([sys.executable, "scripts/validate_release.py"], timeout=600)
    print(f"ALL TESTS PASS modules={len(results)} seconds={payload['seconds']}")


if __name__ == "__main__":
    main()
