import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class VmdTclTests(unittest.TestCase):
    def test_orbital_script_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cube = tmp / "orb.cube"
            cube.write_text("mock cube", encoding="utf-8")
            spec = tmp / "spec.yaml"
            spec.write_text(
                yaml.safe_dump(
                    {
                        "figure_id": "F1",
                        "figure_type": "orbital_gallery",
                        "shared_parameters": {"orbital_isovalue_au": 0.020},
                        "panels": [{"cube_file": str(cube), "camera_id": "cam-1", "render_output": "orb.tga"}],
                    }
                ),
                encoding="utf-8",
            )
            out = tmp / "render.tcl"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/make_vmd_tcl.py"), str(spec), "--out", str(out)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            text = out.read_text(encoding="utf-8")
            self.assertIn("Isosurface 0.02", text)
            self.assertIn("camera_id: cam-1", text)


if __name__ == "__main__":
    unittest.main()
