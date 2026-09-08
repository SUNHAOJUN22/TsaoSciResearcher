import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreflightTests(unittest.TestCase):
    def initialize(self, project: Path) -> tuple[Path, Path]:
        init = ROOT / "scripts/init_project.py"
        preflight = ROOT / "scripts/preflight_project.py"
        subprocess.run([sys.executable, str(init), str(project)], check=True, capture_output=True, text=True)
        return init, preflight

    def test_initialized_project_preflights_with_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _, preflight = self.initialize(project)
            result = subprocess.run(
                [sys.executable, str(preflight), str(project), "--json"], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"ok": true', result.stdout.lower())
            self.assertTrue((project / ".research/manifests/research-manifest.json").exists())
            self.assertTrue((project / ".research/manifests/figure-manifest.json").exists())

    def test_malformed_project_yaml_is_structured_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _, preflight = self.initialize(project)
            (project / ".research/project.yaml").write_text("[\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(preflight), str(project), "--json"], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertTrue(any("project.yaml parse failed" in item for item in report["failures"]))
            self.assertNotIn("Traceback", result.stderr)

    def test_malformed_task_and_dependency_are_structured_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            _, preflight = self.initialize(project)
            task_files = sorted((project / ".research/tasks").glob("*.yaml"))
            self.assertTrue(task_files)
            task_files[0].write_text("[\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(preflight), str(project), "--json"], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertTrue(any("task" in item and "parse failed" in item for item in report["failures"]))
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
