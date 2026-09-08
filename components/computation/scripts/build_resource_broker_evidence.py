from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from tsao_computation.errors import SecurityError
from tsao_computation.execution import ExecutionResourceClaim, validate_resource_binding

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "RESOURCE_BROKER_GPU_BINDING_V6_HARDENING.json"
CLAIM_BOUNDARY = (
    "This deterministic evidence validates resource-claim and visible-device environment "
    "consistency only. It does not claim that a GPU, solver, license, MPI runtime or production "
    "workload was executed or scientifically qualified."
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evaluate_case(
    case_id: str,
    environment: dict[str, str],
    claim: ExecutionResourceClaim,
    expected: str,
) -> dict[str, object]:
    detail = "binding accepted"
    try:
        validate_resource_binding(environment, claim)
        observed = "accepted"
    except SecurityError as error:
        observed = "rejected"
        detail = str(error)
    return {
        "case_id": case_id,
        "environment": dict(sorted(environment.items())),
        "claim": claim.to_dict(),
        "expected": expected,
        "observed": observed,
        "passed": observed == expected,
        "detail": detail,
    }


def build_report() -> dict[str, Any]:
    cases = [
        _evaluate_case(
            "cpu-only-no-gpu-binding",
            {},
            ExecutionResourceClaim(),
            "accepted",
        ),
        _evaluate_case(
            "matching-cuda-claim",
            {"CUDA_VISIBLE_DEVICES": "0"},
            ExecutionResourceClaim(gpu_devices=(0,)),
            "accepted",
        ),
        _evaluate_case(
            "matching-hip-rocr-aliases",
            {"HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "0"},
            ExecutionResourceClaim(gpu_devices=(0,)),
            "accepted",
        ),
        _evaluate_case(
            "unclaimed-cuda-exposure",
            {"CUDA_VISIBLE_DEVICES": "0"},
            ExecutionResourceClaim(),
            "rejected",
        ),
        _evaluate_case(
            "conflicting-hip-rocr-aliases",
            {"HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "1"},
            ExecutionResourceClaim(gpu_devices=(0,)),
            "rejected",
        ),
        _evaluate_case(
            "malformed-secondary-alias",
            {"HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "gpu1"},
            ExecutionResourceClaim(gpu_devices=(0,)),
            "rejected",
        ),
    ]
    passed = all(bool(case["passed"]) for case in cases)
    source_paths = (
        ROOT / "tsao_computation" / "execution" / "resources.py",
        ROOT / "tests" / "test_acceleration_batch.py",
        ROOT / "tests" / "test_resource_broker_evidence.py",
    )
    return {
        "schema_version": "1.0",
        "evidence_id": "resource-broker-gpu-binding-v6-hardening",
        "status": "PASS" if passed else "FAIL",
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in source_paths
        },
        "cases": cases,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def render() -> str:
    return json.dumps(build_report(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic GPU resource-binding hardening evidence."
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render()
    if args.check:
        if not REPORT_PATH.is_file() or REPORT_PATH.read_text(encoding="utf-8") != text:
            print(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "passed": False,
                        "problem": f"stale evidence: {REPORT_PATH.relative_to(ROOT).as_posix()}",
                    },
                    sort_keys=True,
                )
            )
            return 1
    else:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(text, encoding="utf-8", newline="\n")
    payload = build_report()
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "passed": payload["status"] == "PASS",
                "cases": len(payload["cases"]),
                "report": REPORT_PATH.relative_to(ROOT).as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
