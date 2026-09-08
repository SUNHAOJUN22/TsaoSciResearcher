import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tsao_researcher.state import initialize, load_project

ROOT = Path(__file__).resolve().parents[1]


class TestCLIContracts(unittest.TestCase):
    def run_ok(self, *args):
        return subprocess.run([sys.executable, *args], cwd=ROOT, check=True, text=True, capture_output=True)

    def test_installer_dry_run_and_uninstall(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "skill"
            dry = self.run_ok("scripts/install.py", "--target", str(target), "--dry-run", "--validate")
            self.assertIn("Would install", dry.stdout)
            self.assertFalse(target.exists())
            self.run_ok("scripts/install.py", "--target", str(target), "--validate")
            self.assertTrue((target / "SKILL.md").exists())
            self.run_ok("scripts/install.py", "--target", str(target), "--uninstall")
            self.assertFalse(target.exists())

    def test_capability_search(self):
        result = self.run_ok("scripts/capability_search.py", "科研绘图")
        self.assertTrue(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()


def test_handoff_cli_uses_canonical_v2_state(tmp_path: Path) -> None:
    project = initialize("handoff study", "what property should be computed?", tmp_path)
    source = project / "data/input.dat"
    source.write_bytes(b"input")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/handoff_to_computation.py"),
            "--project",
            str(project),
            "--out",
            "computation/job.json",
            "--question",
            "what property should be computed?",
            "--property",
            "free energy",
            "--profile",
            "MD",
            "--scale",
            "atomistic",
            "--boundary-condition",
            "periodic box",
            "--metric",
            "free-energy convergence",
            "--expected-output",
            "PMF profile",
            "--method",
            "enhanced sampling",
            "--input-file",
            "data/input.dat",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    handoff = json.loads((project / "computation/job.json").read_text(encoding="utf-8"))
    assert handoff["schema_version"] == "2.0"
    assert handoff["scale"] == "atomistic"
    assert handoff["boundary_conditions"] == ["periodic box"]
    assert handoff["evaluation_metrics"] == ["free-energy convergence"]
    assert handoff["expected_outputs"] == ["PMF profile"]
    assert handoff["evidence_level"] == "prepared"
    assert load_project(project)["computation_handoffs"] == ["computation/job.json"]
