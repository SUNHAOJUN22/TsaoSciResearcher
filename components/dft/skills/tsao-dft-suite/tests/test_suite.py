import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SuiteTests(unittest.TestCase):
    def run_handoff_text(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "handoff.yaml"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_handoff.py"), str(path), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_handoff(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_handoff.py"), str(ROOT / "examples/handoff.yaml")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_handoff_malformed_yaml_is_structured_failure(self):
        result = self.run_handoff_text("[\n")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(any("parse failed" in item for item in report["errors"]))
        self.assertNotIn("Traceback", result.stderr)

    def test_handoff_rejects_wrong_root_collections_and_nonfinite_resources(self):
        wrong_root = self.run_handoff_text("- not\n- a\n- mapping\n")
        self.assertEqual(wrong_root.returncode, 1)
        self.assertIn("root must be a mapping", wrong_root.stdout)

        data = yaml.safe_load((ROOT / "examples/handoff.yaml").read_text(encoding="utf-8"))
        data["structure_artifacts"] = {"not": "a-list"}
        data["resource_estimate"]["jobs"] = True
        data["resource_estimate"]["cpu_hours"] = float("nan")
        result = self.run_handoff_text(yaml.safe_dump(data))
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIn("structure_artifacts must be a list", report["errors"])
        self.assertIn("resource_estimate.jobs must be finite numeric", report["errors"])
        self.assertIn("resource_estimate.cpu_hours must be finite numeric", report["errors"])

    def test_method_draft_reports_errors_but_parser_runs(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_method_fingerprint.py"),
                str(ROOT / "templates/method-fingerprint.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("charge", result.stdout)

    def test_router(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/route_dft_task.py"), "VASP", "surface", "adsorption"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("tsao-periodic-dft-materials", result.stdout)

    def test_manifest_paths(self):
        manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
        for path in manifest["always_load"]:
            self.assertTrue((ROOT / path).exists())


if __name__ == "__main__":
    unittest.main()
