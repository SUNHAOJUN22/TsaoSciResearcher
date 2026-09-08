#!/usr/bin/env python3
"""Run the complete TsaoDFT quality gate in a deterministic fail-fast sequence."""

from __future__ import annotations

import argparse
import hashlib
import uuid
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    name: str
    command: tuple[str, ...]
    timeout_seconds: float = 240.0


def stages(include_tests: bool = True) -> list[Stage]:
    items = [
        Stage("demo assets", (sys.executable, "scripts/generate_readme_demos.py")),
        Stage("dependency contract", (sys.executable, "scripts/validate_dependencies.py")),
        Stage("CI constraints", (sys.executable, "scripts/validate_constraints.py")),
        Stage(
            "acceleration contracts",
            (sys.executable, "scripts/validate_acceleration_contracts.py"),
        ),
        Stage(
            "benchmark contract",
            (sys.executable, "scripts/validate_benchmark_contract.py"),
        ),
        Stage(
            "acceleration registry",
            (sys.executable, "scripts/validate_acceleration_registry.py"),
        ),
        Stage(
            "engine capabilities",
            (sys.executable, "scripts/validate_engine_capabilities.py"),
        ),
        Stage(
            "compute qualification",
            (sys.executable, "scripts/validate_compute_qualification.py"),
        ),
        Stage(
            "compute contract evidence",
            (
                sys.executable,
                "scripts/capture_compute_contract_evidence.py",
                "--out",
                "compute-contract-evidence.json",
            ),
        ),
        Stage(
            "compute architecture audit",
            (sys.executable, "scripts/audit_compute_architecture.py"),
        ),
        Stage(
            "release acceptance",
            (
                sys.executable,
                "scripts/build_release_acceptance.py",
                "--out",
                "release-acceptance.json",
            ),
        ),
        Stage("packaging model", (sys.executable, "scripts/validate_packaging_model.py")),
        Stage("catalog", (sys.executable, "scripts/validate_catalog.py")),
        Stage("Agent eval contracts", (sys.executable, "scripts/validate_agent_evals.py")),
        Stage("governance", (sys.executable, "scripts/validate_governance.py")),
        Stage("capability claims", (sys.executable, "scripts/validate_capability_claims.py")),
        Stage("secret patterns", (sys.executable, "scripts/validate_secrets.py")),
        Stage("ignore markers", (sys.executable, "scripts/validate_ignore_markers.py")),
        Stage("AI assets", (sys.executable, "scripts/validate_ai_assets.py")),
        Stage("README visuals", (sys.executable, "scripts/validate_readme_visuals.py", "--strict")),
        Stage("README links", (sys.executable, "scripts/validate_readme_links.py")),
        Stage("Ruff lint", (sys.executable, "-m", "ruff", "check", ".")),
        Stage("Ruff format", (sys.executable, "-m", "ruff", "format", "--diff", ".")),
        Stage("mypy", (sys.executable, "scripts/run_type_checks.py"), timeout_seconds=900.0),
        Stage(
            "trust-boundary strict mypy",
            (sys.executable, "scripts/run_strict_type_checks.py"),
            timeout_seconds=900.0,
        ),
        Stage(
            "coverage",
            (
                sys.executable,
                "scripts/run_coverage.py",
                "--contract-evidence",
                "compute-contract-evidence.json",
            ),
            timeout_seconds=1200.0,
        ),
        Stage("Bandit", (sys.executable, "scripts/run_bandit.py"), timeout_seconds=600.0),
        Stage("repository", (sys.executable, "scripts/validate_repo.py", "--strict")),
    ]
    if include_tests:
        items.append(Stage("unit tests", (sys.executable, "scripts/run_all_tests.py"), timeout_seconds=900.0))
    return items


def run_stage(
    stage: Stage,
    env: dict[str, str],
    *,
    timeout_override: float | None = None,
    capture_output: bool = False,
) -> dict[str, object]:
    started = time.monotonic()
    timeout = timeout_override if timeout_override is not None else stage.timeout_seconds
    try:
        process = subprocess.run(
            stage.command,
            cwd=ROOT,
            text=True,
            env=env,
            timeout=timeout,
            capture_output=capture_output,
            check=False,
        )
        result: dict[str, object] = {
            "stage": stage.name,
            "returncode": process.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "timed_out": False,
        }
        if capture_output and process.returncode != 0:
            result["output"] = ((process.stdout or "") + (process.stderr or "")).rstrip()
        return result
    except subprocess.TimeoutExpired as exc:
        result = {
            "stage": stage.name,
            "returncode": 124,
            "seconds": round(time.monotonic() - started, 3),
            "timed_out": True,
            "timeout_seconds": timeout,
        }
        if capture_output:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            result["output"] = (stdout + stderr).rstrip()
        return result


def _source_identity() -> str:
    """Bind executable Python source, not regenerated historical reports."""
    digest = hashlib.sha256()
    for folder in (ROOT / "scripts", ROOT / "skills"):
        for path in sorted(folder.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="Run static gates only")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Override the timeout for every stage in seconds; must be positive",
    )
    args = parser.parse_args()
    if args.timeout is not None and args.timeout <= 0:
        parser.error("--timeout must be positive")

    run_id = uuid.uuid4().hex
    final_receipt = ROOT / "quality-run-acceptance.json"
    final_receipt.unlink(missing_ok=True)
    # A checked-in historical report must never impersonate this run.
    (ROOT / "coverage-report.json").unlink(missing_ok=True)
    source_before = _source_identity()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    results: list[dict[str, object]] = []
    started = time.monotonic()
    expected = stages(include_tests=not args.skip_tests)

    for index, stage in enumerate(expected, start=1):
        result = run_stage(stage, env, timeout_override=args.timeout, capture_output=args.json_output)
        results.append(result)
        if not args.json_output:
            status = "PASS" if result["returncode"] == 0 else "TIMEOUT" if result["timed_out"] else "FAIL"
            print(f"[{index}] {stage.name}: {status} ({result['seconds']:.3f}s)")
        if result["returncode"] != 0:
            break

    ok = len(results) == len(expected) and all(item["returncode"] == 0 for item in results)
    source_after = _source_identity()
    ok = ok and source_before == source_after
    qualification = {
        "schema_version": "tsao.quality-run/1",
        "state": "SOFTWARE_ACCEPTANCE_READY" if ok and not args.skip_tests else "UNQUALIFIED",
        "run_id": run_id,
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "source_before": source_before, "source_after": source_after,
        "required": [stage.name for stage in stages()],
        "executed": results,
        "external_execution": "NOT_EVALUATED",
    }
    final_receipt.write_text(json.dumps(qualification, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    payload = {
        "ok": ok,
        "python": sys.version.split()[0],
        "seconds": round(time.monotonic() - started, 3),
        "stages": results,
    }
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"QUALITY GATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
