from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "contracts_v17.py"
)
SPEC = importlib.util.spec_from_file_location("tsao_dft_contracts_v17", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DftContractsV17Tests(unittest.TestCase):
    def test_fatal_after_success_is_still_failed(self) -> None:
        decision = MODULE.parse_termination(
            [
                "reached required accuracy",
                "writing final structure",
                "BRMIX: very serious problems",
            ]
        )
        self.assertEqual(decision.status, "FAILED")
        self.assertIn("brmix: very serious problems", decision.fatal_markers)
        self.assertTrue(decision.success_markers)

    def test_success_without_fatal_is_converged(self) -> None:
        decision = MODULE.parse_termination(["iteration 12", "Normal termination"])
        self.assertEqual(decision.status, "CONVERGED")

    def test_truncated_output_is_incomplete(self) -> None:
        decision = MODULE.parse_termination(["iteration 1", "iteration 2"])
        self.assertEqual(decision.status, "INCOMPLETE")

    def test_tst_rate_uses_declared_standard_state_factor(self) -> None:
        base = MODULE.tst_rate_constant(50_000.0, 298.15)
        doubled = MODULE.tst_rate_constant(50_000.0, 298.15, standard_state_factor=2.0)
        self.assertGreater(base, 0.0)
        self.assertAlmostEqual(doubled, 2.0 * base)

    def test_tst_rejects_nonphysical_temperature_and_nonfinite_energy(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.tst_rate_constant(50_000.0, 0.0)
        with self.assertRaises(ValueError):
            MODULE.tst_rate_constant(math.inf, 298.15)

    def test_quantity_kind_controls_shape(self) -> None:
        MODULE.validate_quantity_shape("forces", (4, 3), atom_count=4)
        MODULE.validate_quantity_shape("stress_voigt", (6,))
        with self.assertRaises(ValueError):
            MODULE.validate_quantity_shape("forces", (3, 4), atom_count=4)

    def test_parser_convergence_does_not_prove_external_execution(self) -> None:
        status = MODULE.external_execution_status(
            parser_converged=True,
            signed_external_receipt=False,
        )
        self.assertEqual(status, "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
