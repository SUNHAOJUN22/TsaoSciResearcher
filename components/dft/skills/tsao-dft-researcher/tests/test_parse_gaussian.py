import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from parse_gaussian import parse_log  # noqa: E402 -- script-local import follows an explicit sys.path setup


class ParseGaussianTests(unittest.TestCase):
    def test_minimum_candidate(self):
        text = (ROOT / "tests/fixtures/minimum.log").read_text()
        result = parse_log(text)
        self.assertEqual(result["status"], "MINIMUM_CANDIDATE")
        self.assertEqual(result["charge"], 0)
        self.assertAlmostEqual(result["last_scf_energy_hartree"], -100.123456789)

    def test_ts_candidate(self):
        text = (ROOT / "tests/fixtures/ts.log").read_text()
        result = parse_log(text)
        self.assertEqual(result["status"], "TS_CANDIDATE")
        self.assertEqual(result["imaginary_frequencies_cm-1"], [-500.0])


if __name__ == "__main__":
    unittest.main()
