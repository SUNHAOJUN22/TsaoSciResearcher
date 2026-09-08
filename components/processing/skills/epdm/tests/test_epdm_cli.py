from __future__ import annotations

import json
import subprocess
import sys

import pytest


def test_epdm_cli_reference_audit_and_model_suite():
    commands = (
        ("epdm", "status"),
        ("epdm", "reference-demo"),
        ("epdm", "audit"),
        ("epdm", "model-suite", "--temperature-k", "323.15", "--residence-s", "300"),
    )
    for args in commands:
        completed = subprocess.run(
            [sys.executable, "-m", "tsao.cli", *args],
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload
        if args[1] == "model-suite":
            assert payload["status"] == "CALCULATED_REFERENCE_ONLY"
            assert payload["semibatch_reference_step"]["molar_closure_residual"] == pytest.approx(
                0.0, abs=1e-12
            )
