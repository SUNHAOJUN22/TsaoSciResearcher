from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StreamingParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vasp = load_module("parse_vasp")
        cls.qe = load_module("parse_qe")
        cls.cp2k = load_module("parse_cp2k")

    def test_vasp_streams_last_values_and_force_block(self):
        text = """vasp.6.4.3\nNIONS = 2\nfree energy TOTEN = -10.0 eV\nE-fermi : 1.2\nTOTAL-FORCE (eV/Angst)\n---\n0 0 0 0.3 0.4 0.0\n0 0 0 0.0 0.0 0.2\ntotal drift\nfree energy TOTEN = -11.5 eV\nE-fermi : 1.8\naborting loop because EDIFF is reached\nreached required accuracy - stopping structural energy minimisation\nElapsed time (sec): 44.5\nGeneral timing and accounting informations for this job\n"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "OUTCAR"
            path.write_text(text, encoding="utf-8")
            result = self.vasp.parse(path)
        self.assertEqual(result["energy_count"], 2)
        self.assertEqual(result["last_toten_eV"], -11.5)
        self.assertEqual(result["fermi_energy_eV"], 1.8)
        self.assertAlmostEqual(result["max_force_eV_per_angstrom"], 0.5)
        self.assertEqual(result["status"], "RELAX_VALIDATED_CANDIDATE")

    def test_qe_streams_last_values(self):
        text = """Program PWSCF v.7.3\n! total energy = -20.0 Ry\nconvergence has been achieved\nTotal force = 0.2\nP= 3.0\n! total energy = -21.0 Ry\nthe Fermi energy is 5.5 ev\nEnd of BFGS Geometry Optimization\nJOB DONE.\n"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pw.out"
            path.write_text(text, encoding="utf-8")
            result = self.qe.parse(path)
        self.assertEqual(result["energy_count"], 2)
        self.assertEqual(result["last_total_energy_Ry"], -21.0)
        self.assertEqual(result["last_total_force_Ry_per_bohr"], 0.2)
        self.assertEqual(result["status"], "RELAX_VALIDATED_CANDIDATE")

    def test_cp2k_streams_last_values(self):
        text = """CP2K| version string: CP2K version 2026.1\nENERGY| Total FORCE_EVAL ( QS ) energy (a.u.): -3.0\nSCF run converged\nMax. gradient = 0.05\nENERGY| Total FORCE_EVAL ( QS ) energy (a.u.): -3.5\nGEOMETRY OPTIMIZATION COMPLETED\nPROGRAM ENDED AT 2026-07-27\n"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cp2k.out"
            path.write_text(text, encoding="utf-8")
            result = self.cp2k.parse(path)
        self.assertEqual(result["energy_count"], 2)
        self.assertEqual(result["last_total_energy_hartree"], -3.5)
        self.assertEqual(result["last_max_gradient"], 0.05)
        self.assertEqual(result["status"], "RELAX_VALIDATED_CANDIDATE")

    def test_parsers_do_not_use_read_text(self):
        samples = {
            self.vasp: "General timing and accounting informations for this job\nEDIFF is reached\n",
            self.qe: "JOB DONE.\nconvergence has been achieved\n",
            self.cp2k: "PROGRAM ENDED AT now\nSCF run converged\n",
        }
        with tempfile.TemporaryDirectory() as temporary:
            for index, (module, text) in enumerate(samples.items()):
                path = Path(temporary) / f"output-{index}.txt"
                path.write_text(text, encoding="utf-8")
                with patch.object(Path, "read_text", side_effect=AssertionError("read_text forbidden")):
                    module.parse(path)


if __name__ == "__main__":
    unittest.main()
