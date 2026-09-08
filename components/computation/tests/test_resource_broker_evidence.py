from __future__ import annotations

import json
import subprocess  # nosec B404
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def test_resource_broker_gpu_binding_evidence_is_current_and_schema_valid() -> None:
    report_path = ROOT / "reports" / "RESOURCE_BROKER_GPU_BINDING_V6_HARDENING.json"
    schema_path = ROOT / "schemas" / "resource-broker-gpu-binding-evidence.schema.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(report)
    assert report["status"] == "PASS"
    assert all(case["passed"] is True for case in report["cases"])

    completed = subprocess.run(  # nosec B603
        [
            sys.executable,
            "scripts/build_resource_broker_evidence.py",
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
