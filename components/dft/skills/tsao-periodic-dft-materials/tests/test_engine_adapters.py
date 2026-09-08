import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples/engine-adapters"


class EngineAdapterTests(unittest.TestCase):
    def run_json(self, script, *args, expected=0):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *map(str, args)], capture_output=True, text=True
        )
        self.assertEqual(r.returncode, expected, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_vasp_preflight_and_parse(self):
        d = self.run_json("preflight_vasp.py", EX / "vasp")
        self.assertEqual(d["poscar"]["atom_count"], 2)
        d = self.run_json("parse_vasp.py", EX / "vasp/OUTCAR")
        self.assertTrue(d["electronic_converged"])
        self.assertAlmostEqual(d["last_toten_eV"], -10.123456)

    def test_qe_preflight_and_parse(self):
        d = self.run_json("preflight_qe.py", EX / "qe/si.in")
        self.assertEqual(len(d["parsed"]["species"]), 1)
        d = self.run_json("parse_qe.py", EX / "qe/si.out")
        self.assertTrue(d["scf_converged"])
        self.assertIsNotNone(d["last_total_energy_eV"])

    def test_cp2k_preflight_and_parse(self):
        d = self.run_json("preflight_cp2k.py", EX / "cp2k/si.inp")
        self.assertEqual(d["parsed"]["run_type"], "ENERGY")
        d = self.run_json("parse_cp2k.py", EX / "cp2k/si.out")
        self.assertTrue(d["scf_converged"])
        self.assertAlmostEqual(d["last_total_energy_hartree"], -7.5)

    def test_convergence(self):
        d = self.run_json(
            "analyze_convergence.py", EX / "convergence-results.csv", "--absolute-threshold", "0.002", "--tail", "2"
        )
        self.assertTrue(d["converged_candidate"])


if __name__ == "__main__":
    unittest.main()
