from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
CODE_PATHS = ("tsao_computation", "scripts", "tests", "_bootstrap.py")
CLAIM_BOUNDARY = (
    "This validates local orchestration, contracts, deterministic evidence and packaging. "
    "It does not claim external solver execution or production HPC performance."
)
_TIMING_RECORDS: list[dict[str, object]] = []


@dataclass(frozen=True, slots=True)
class CommandResult:
    index: int
    label: str
    command: tuple[str, ...]
    returncode: int
    output: str
    elapsed_seconds: float


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def source_artifacts() -> tuple[str, str]:
    release_version = version()
    return (
        f"TsaoSciComputation-{release_version}.zip",
        f"TsaoSciComputation-{release_version}.tar.gz",
    )


def verification_workers(task_count: int) -> int:
    if task_count < 1:
        raise ValueError("task_count must be positive")
    configured = os.environ.get("TSAO_VERIFY_WORKERS")
    if configured is not None:
        try:
            workers = int(configured)
        except ValueError as error:
            raise ValueError("TSAO_VERIFY_WORKERS must be an integer") from error
        if workers < 1:
            raise ValueError("TSAO_VERIFY_WORKERS must be positive")
        return min(workers, task_count)
    return min(task_count, max(1, min(3, os.cpu_count() or 1)))


def _record_timing(
    label: str, command: Sequence[str], elapsed: float, mode: str, returncode: int
) -> None:
    _TIMING_RECORDS.append(
        {
            "label": label,
            "command": list(command),
            "elapsed_seconds": round(elapsed, 6),
            "mode": mode,
            "returncode": returncode,
            "status": "PASS" if returncode == 0 else "FAIL",
        }
    )


def run(label: str, command: Sequence[str], *, env: dict[str, str] | None = None) -> int:
    print(f"\n==> {label}", flush=True)
    print("    " + " ".join(command), flush=True)
    started = time.perf_counter()
    try:
        returncode = subprocess.run(  # nosec B603
            list(command), cwd=ROOT, env=env, check=False
        ).returncode
    except OSError:
        returncode = 127
    _record_timing(
        label,
        command,
        time.perf_counter() - started,
        "sequential",
        returncode,
    )
    return returncode


def _run_captured(
    index: int,
    label: str,
    command: Sequence[str],
    env: dict[str, str] | None,
) -> CommandResult:
    started = time.perf_counter()
    try:
        completed = subprocess.run(  # nosec B603
            list(command),
            cwd=ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        returncode = completed.returncode
        output = completed.stdout
    except OSError as error:
        returncode = 127
        output = f"ERROR: {error}\n"
    return CommandResult(
        index=index,
        label=label,
        command=tuple(command),
        returncode=returncode,
        output=output,
        elapsed_seconds=time.perf_counter() - started,
    )


def run_commands(commands: Sequence[tuple[str, Sequence[str]]]) -> int:
    for label, command in commands:
        returncode = run(label, command)
        if returncode:
            print(f"\nFAILED: {label} (exit {returncode})", file=sys.stderr)
            return returncode
    return 0


def run_commands_parallel(
    commands: Sequence[tuple[str, Sequence[str]]],
    *,
    env: dict[str, str] | None = None,
    max_workers: int | None = None,
) -> int:
    if not commands:
        return 0
    workers = max_workers or verification_workers(len(commands))
    workers = max(1, min(workers, len(commands)))
    if workers == 1:
        for label, command in commands:
            returncode = run(label, command, env=env)
            if returncode:
                print(f"\nFAILED: {label} (exit {returncode})", file=sys.stderr)
                return returncode
        return 0

    print(f"\n==> bounded parallel verification ({workers} workers)", flush=True)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tsao-verify") as pool:
        futures = [
            pool.submit(_run_captured, index, label, command, env)
            for index, (label, command) in enumerate(commands)
        ]
        results = sorted((future.result() for future in futures), key=lambda item: item.index)

    first_failure = 0
    for result in results:
        print(f"\n==> {result.label} [parallel]", flush=True)
        print("    " + " ".join(result.command), flush=True)
        if result.output:
            print(result.output, end="" if result.output.endswith("\n") else "\n")
        print(f"    elapsed={result.elapsed_seconds:.3f}s", flush=True)
        _record_timing(
            result.label,
            result.command,
            result.elapsed_seconds,
            "parallel",
            result.returncode,
        )
        if result.returncode and not first_failure:
            first_failure = result.returncode
            print(
                f"\nFAILED: {result.label} (exit {result.returncode})",
                file=sys.stderr,
            )
    return first_failure


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_core() -> int:
    coverage_env = dict(os.environ)
    coverage_env.setdefault(
        "TSAO_COVERAGE_JSON", str(Path(tempfile.gettempdir()) / "tsao-current-coverage.json")
    )
    returncode = run(
        "tests and coverage",
        (PYTHON, "scripts/run_tests.py", "--coverage"),
        env=coverage_env,
    )
    if returncode:
        return returncode

    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("scientific reference benchmarks", (PYTHON, "scripts/run_scientific_benchmarks.py")),
        ("critical coverage policy", (PYTHON, "scripts/check_critical_coverage.py")),
        ("version metadata", (PYTHON, "scripts/sync_version_metadata.py", "--check")),
        ("repository audit", (PYTHON, "scripts/validate_repository.py")),
        ("schema validation", (PYTHON, "scripts/validate_schemas.py")),
        ("packaged registry assets", (PYTHON, "scripts/sync_package_assets.py", "--check")),
        ("adapter metadata", (PYTHON, "scripts/validate_adapter_metadata.py")),
        (
            "acceleration audit reports",
            (PYTHON, "scripts/build_acceleration_audits.py", "--check"),
        ),
        (
            "resource broker GPU binding evidence",
            (PYTHON, "scripts/build_resource_broker_evidence.py", "--check"),
        ),
        ("capability index", (PYTHON, "scripts/build_capability_index.py", "--check")),
        ("adapter documentation", (PYTHON, "scripts/build_adapter_docs.py", "--check")),
        ("workflow documentation", (PYTHON, "scripts/build_workflow_docs.py", "--check")),
        ("scenario examples", (PYTHON, "scripts/build_examples.py", "--check")),
    )
    returncode = run_commands_parallel(checks)
    if returncode:
        return returncode
    return run("repository manifest", (PYTHON, "scripts/build_manifest.py", "--check"))


def verify_quality() -> int:
    returncode = run_commands(
        (
            ("repository quality rules", (PYTHON, "scripts/quality_check.py")),
            ("Ruff lint", (PYTHON, "-m", "ruff", "check", *CODE_PATHS)),
            ("Ruff formatting", (PYTHON, "-m", "ruff", "format", "--check", *CODE_PATHS)),
        )
    )
    if returncode:
        return returncode
    returncode = run_commands_parallel(
        (
            (
                "Mypy",
                (PYTHON, "-m", "mypy", "--python-version", "3.13", "tsao_computation", "scripts"),
            ),
            (
                "Bandit",
                (PYTHON, "-m", "bandit", "-q", "-r", "tsao_computation", "scripts", "-x", "tests"),
            ),
            ("repository security scan", (PYTHON, "scripts/security_scan.py")),
            ("controlled mutation gate", (PYTHON, "scripts/run_mutation_gate.py")),
        ),
        max_workers=2,
    )
    if returncode:
        return returncode
    return run("refresh repository manifest", (PYTHON, "scripts/build_manifest.py"))


def verify_package() -> int:
    artifacts = source_artifacts()
    environment = dict(os.environ)
    environment["SOURCE_DATE_EPOCH"] = environment.get("SOURCE_DATE_EPOCH", "1700000000")
    shutil.rmtree(ROOT / "dist", ignore_errors=True)

    with tempfile.TemporaryDirectory(prefix="tsao-source-build-") as temporary:
        temporary_root = Path(temporary)
        first = temporary_root / "first"
        second = temporary_root / "second"
        returncode = run_commands_parallel(
            (
                (
                    "source build A",
                    (PYTHON, "scripts/package_release.py", "--output-dir", str(first)),
                ),
                (
                    "source build B",
                    (PYTHON, "scripts/package_release.py", "--output-dir", str(second)),
                ),
            ),
            env=environment,
            max_workers=2,
        )
        if returncode:
            return returncode

        for artifact in artifacts:
            first_hash = sha256(first / artifact)
            second_hash = sha256(second / artifact)
            if first_hash != second_hash:
                print(f"FAILED: non-reproducible source artifact: {artifact}", file=sys.stderr)
                return 1

        destination = ROOT / "dist"
        destination.mkdir(exist_ok=True)
        for path in first.iterdir():
            if path.is_file():
                shutil.copy2(path, destination / path.name)

    returncode = run("wheel rebuild and isolated install", (PYTHON, "scripts/verify_wheel.py"))
    if returncode:
        return returncode
    returncode = run("deterministic SPDX and CycloneDX SBOMs", (PYTHON, "scripts/build_sbom.py"))
    if returncode:
        return returncode
    returncode = run(
        "release manifest and checksums", (PYTHON, "scripts/build_release_manifest.py")
    )
    if returncode:
        return returncode
    return run("repository manifest", (PYTHON, "scripts/build_manifest.py", "--check"))


def verify_benchmark() -> int:
    returncode = run(
        "scientific reference benchmarks", (PYTHON, "scripts/run_scientific_benchmarks.py")
    )
    if returncode:
        return returncode
    with tempfile.TemporaryDirectory(prefix="tsao-benchmark-") as temporary:
        output = Path(temporary) / "benchmark.json"
        return run(
            "orchestration microbenchmark",
            (PYTHON, "scripts/benchmark.py", "--output", str(output)),
        )


PROFILE_FUNCTIONS: dict[str, Callable[[], int]] = {
    "core": verify_core,
    "quality": verify_quality,
    "package": verify_package,
    "benchmark": verify_benchmark,
}
RELEASE_PROFILE_NAMES = ("quality", "core", "package")


def selected_verifications(profile: str) -> tuple[Callable[[], int], ...]:
    if profile == "all":
        return tuple(PROFILE_FUNCTIONS[name] for name in RELEASE_PROFILE_NAMES)
    try:
        return (PROFILE_FUNCTIONS[profile],)
    except KeyError as error:
        raise ValueError(f"unknown verification profile: {profile}") from error


def _recorded_seconds() -> float:
    total = 0.0
    for record in _TIMING_RECORDS:
        value = record.get("elapsed_seconds")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total += float(value)
    return total


def _write_timing_report(path: Path, profile: str, elapsed: float, returncode: int) -> None:
    payload = {
        "schema_version": "1.1",
        "profile": profile,
        "status": "PASS" if returncode == 0 else "FAIL",
        "total_seconds": round(elapsed, 6),
        "total_recorded_seconds": round(_recorded_seconds(), 6),
        "default_parallel_workers": verification_workers(999),
        "steps": _TIMING_RECORDS,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical TsaoSciComputation verification profiles."
    )
    parser.add_argument(
        "--profile",
        choices=(*PROFILE_FUNCTIONS, "all"),
        default="all",
        help=(
            "all runs the deterministic release gates (quality, core, package); "
            "benchmark remains separate because it is environment-specific"
        ),
    )
    parser.add_argument(
        "--timing-json",
        type=Path,
        help="write deterministic step timing telemetry to this path",
    )
    args = parser.parse_args()

    _TIMING_RECORDS.clear()
    started = time.perf_counter()
    returncode = 0
    for verification in selected_verifications(args.profile):
        returncode = verification()
        if returncode:
            break
    elapsed = time.perf_counter() - started
    if args.timing_json is not None:
        _write_timing_report(args.timing_json, args.profile, elapsed, returncode)
    if returncode:
        print(f"\nValidation failed (exit {returncode}).", file=sys.stderr)
        return returncode
    print(f"\nPASS: verification profile '{args.profile}' completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
