from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tsao_researcher", "quality", str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_quality_cli_accepts_documented_example() -> None:
    result = _run(ROOT / "examples/scientific-quality-check.json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["details"]["verdict"] == "causal-supported"


def test_quality_cli_returns_nonzero_for_blocked_claim(tmp_path: Path) -> None:
    request = tmp_path / "blocked.json"
    request.write_text(
        json.dumps(
            {
                "kind": "causality-guard",
                "spec": {
                    "claim": "The morphology causes the improvement.",
                    "design": "observational comparison",
                    "temporal_order": True,
                    "confounders_addressed": False,
                    "intervention_or_natural_experiment": False,
                    "comparison_or_control": True,
                    "replication": True,
                    "mechanism_tested": False,
                    "uncertainty_reported": True,
                },
            }
        ),
        encoding="utf-8",
    )
    result = _run(request)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "BLOCK"
    assert any(finding["code"] == "CG-OVERCLAIM" for finding in payload["findings"])
