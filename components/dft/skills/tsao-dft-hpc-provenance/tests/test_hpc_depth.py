import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HpcDepthTests(unittest.TestCase):
    def test_site_profile(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_site_profile.py"), str(ROOT / "templates/site-profile.yaml")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_estimate(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/estimate_resources.py"),
                str(ROOT / "examples/slurm/hpc-manifest.yaml"),
                "--jobs",
                "2",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["allocated_cpu_hours_total"], 192.0)

    def test_restart_lineage(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_restart_lineage.py"),
                str(ROOT / "templates/restart-lineage.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_engine_command(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "job.sh"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/generate_job_script.py"),
                    str(ROOT / "examples/slurm/hpc-manifest.yaml"),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            t = out.read_text()
            self.assertIn("g16 < demo.gjf > demo.log", t)
            self.assertIn("method_fingerprint_id", t)


if __name__ == "__main__":
    unittest.main()
