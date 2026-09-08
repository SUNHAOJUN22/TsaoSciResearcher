from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_quality_gate():
    path = ROOT / "scripts" / "quality_gate.py"
    spec = importlib.util.spec_from_file_location("tsao_quality_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


quality_gate = load_quality_gate()


class QualityGateTests(unittest.TestCase):
    def test_dependency_contract_precedes_static_analysis(self):
        stages = quality_gate.stages()
        names = [stage.name for stage in stages]
        self.assertEqual(len(names), 29)
        self.assertEqual(names[1], "dependency contract")
        self.assertLess(names.index("dependency contract"), names.index("Ruff lint"))
        self.assertLess(names.index("CI constraints"), names.index("acceleration contracts"))
        self.assertLess(names.index("acceleration contracts"), names.index("benchmark contract"))
        self.assertLess(names.index("benchmark contract"), names.index("acceleration registry"))
        self.assertLess(names.index("acceleration registry"), names.index("engine capabilities"))
        self.assertLess(names.index("engine capabilities"), names.index("compute qualification"))
        self.assertLess(names.index("compute qualification"), names.index("compute contract evidence"))
        self.assertLess(names.index("compute contract evidence"), names.index("compute architecture audit"))
        self.assertLess(names.index("compute architecture audit"), names.index("release acceptance"))
        self.assertLess(names.index("release acceptance"), names.index("coverage"))
        self.assertEqual(names.count("benchmark contract"), 1)
        self.assertEqual(names.count("compute architecture audit"), 1)
        self.assertEqual(names.count("release acceptance"), 1)
        self.assertEqual(names.count("engine capabilities"), 1)
        self.assertEqual(names.count("compute qualification"), 1)
        self.assertEqual(names.count("compute contract evidence"), 1)
        self.assertLess(names.index("compute architecture audit"), names.index("capability claims"))
        acceptance = next(stage for stage in stages if stage.name == "release acceptance")
        self.assertIn("scripts/build_release_acceptance.py", acceptance.command)
        self.assertIn("release-acceptance.json", acceptance.command)
        coverage = next(stage for stage in stages if stage.name == "coverage")
        self.assertIn("--contract-evidence", coverage.command)
        self.assertIn("compute-contract-evidence.json", coverage.command)
        self.assertEqual(names[-1], "unit tests")

    def test_skip_tests_removes_only_unit_test_stage(self):
        full = [stage.name for stage in quality_gate.stages()]
        static = [stage.name for stage in quality_gate.stages(include_tests=False)]
        self.assertEqual(static, full[:-1])
        self.assertNotIn("unit tests", static)

    def test_stage_timeout_is_reported_deterministically(self):
        stage = quality_gate.Stage(
            "timeout fixture",
            (sys.executable, "-c", "import time; time.sleep(0.2)"),
            timeout_seconds=0.01,
        )
        result = quality_gate.run_stage(stage, os.environ.copy(), capture_output=True)
        self.assertEqual(result["returncode"], 124)
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["timeout_seconds"], 0.01)

    def test_non_positive_timeout_is_rejected_by_cli(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "quality_gate.py"), "--timeout", "0"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--timeout must be positive", result.stderr)


if __name__ == "__main__":
    unittest.main()
