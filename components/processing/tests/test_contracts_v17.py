from __future__ import annotations

import math
import unittest

from tsao.contracts_v17 import (
    Quantity,
    aggregate_status,
    component_balance,
    mean_absolute_percentage_error,
    stable_first_order_conversion,
)


class ProcessingContractsV17Tests(unittest.TestCase):
    @staticmethod
    def mass_flow(value: float, unit: str = "kg/h", scale: float = 1.0 / 3600.0) -> Quantity:
        return Quantity(value=value, unit=unit, dimension="mass_flow", scale_to_si=scale)

    def test_equal_total_flow_cannot_hide_species_substitution(self) -> None:
        decision = component_balance(
            {"A": self.mass_flow(100.0)},
            {"B": self.mass_flow(100.0)},
            absolute_tolerance=1e-12,
            relative_tolerance=1e-12,
        )
        self.assertEqual(decision.status, "FAIL")
        self.assertEqual(
            set(decision.reason_codes),
            {"COMPONENT_RESIDUAL:A", "COMPONENT_RESIDUAL:B"},
        )

    def test_unit_conversion_precedes_balance(self) -> None:
        decision = component_balance(
            {"A": self.mass_flow(3.6)},
            {"A": Quantity(0.001, "kg/s", "mass_flow", 1.0)},
            absolute_tolerance=1e-12,
            relative_tolerance=1e-12,
        )
        self.assertEqual(decision.status, "PASS")

    def test_boolean_and_nonfinite_values_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            Quantity(True, "kg/s", "mass_flow", 1.0).canonical()
        with self.assertRaises(ValueError):
            Quantity(math.inf, "kg/s", "mass_flow", 1.0).canonical()

    def test_status_lattice_is_monotone(self) -> None:
        self.assertEqual(aggregate_status(["PASS", "HOLD"]), "HOLD")
        self.assertEqual(aggregate_status(["PASS", "FAIL", "HOLD"]), "FAIL")
        self.assertEqual(aggregate_status([]), "NOT_EVALUATED")

    def test_stable_conversion_handles_small_exposure(self) -> None:
        value = stable_first_order_conversion(1e-14)
        self.assertGreater(value, 0.0)
        self.assertAlmostEqual(value, 1e-14, places=27)

    def test_mape_is_undefined_when_all_observations_are_zero(self) -> None:
        self.assertIsNone(mean_absolute_percentage_error([0.0, 0.0], [0.0, 1.0]))
        self.assertAlmostEqual(
            mean_absolute_percentage_error([2.0, 4.0], [1.0, 6.0]) or 0.0,
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
