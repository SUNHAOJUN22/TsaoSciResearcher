import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_manifest(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_hpc_manifest.py"),
                str(ROOT / "examples/slurm/hpc-manifest.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_script(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "j.sh"
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
            self.assertEqual(r.returncode, 0)
            self.assertIn("#SBATCH", out.read_text())

    def test_failure(self):
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/classify_failure.py"),
                str(ROOT / "examples/failures/gaussian-memory.log"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn("memory", r.stdout)


if __name__ == "__main__":
    unittest.main()
