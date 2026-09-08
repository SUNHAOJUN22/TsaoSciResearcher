import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from parse_gaussian import parse_log  # noqa: E402 -- path injection is intentional for script testing


class RichGaussianTests(unittest.TestCase):
    def test_rich_fields(self):
        r = parse_log((ROOT / "tests/fixtures/rich.log").read_text())
        self.assertEqual(r["route_metadata"]["method"], "UB3LYP")
        self.assertEqual(r["route_metadata"]["basis"], "6-31G(d)")
        self.assertEqual(r["route_metadata"]["solvent"], "Water")
        self.assertEqual(r["final_coordinates"][1]["element"], "O")
        self.assertAlmostEqual(r["orbital_energies"]["alpha_homo_hartree"], -0.25)
        self.assertAlmostEqual(r["dipole_moment"]["total_debye"], 0.3742)
        self.assertEqual(len(r["nmr_shieldings"]), 2)
        self.assertEqual(r["excited_states"][0]["contributions"][0]["from_orbital"], 3)
        self.assertAlmostEqual(r["spin_s2"]["ideal"], 0.75)


if __name__ == "__main__":
    unittest.main()
