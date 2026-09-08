from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_uncertainty_budget.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("researcher_uncertainty_numerics", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def budget(values: list[float], rule: str = "root_sum_square") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "project_id": "P",
        "observable": "barrier",
        "unit": "kcal/mol",
        "components": [
            {"type": "numerical", "magnitude": value, "basis": f"component-{index}"}
            for index, value in enumerate(values)
        ],
        "combination_rule": rule,
        "status": "draft",
    }


class UncertaintyNumericsTests(unittest.TestCase):
    module: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()

    def test_root_sum_square_matches_hypotenuse(self) -> None:
        errors, warnings, summary = self.module.validate(budget([3.0, 4.0]))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(summary["combined_magnitude"], 5.0)

    def test_root_sum_square_avoids_intermediate_overflow(self) -> None:
        errors, warnings, summary = self.module.validate(budget([1e308, 1e308]))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        observed = summary["combined_magnitude"]
        self.assertTrue(math.isfinite(observed))
        self.assertTrue(math.isclose(observed, math.hypot(1e308, 1e308), rel_tol=0.0, abs_tol=0.0))

    def test_sum_bounds_uses_accurate_floating_sum(self) -> None:
        errors, warnings, summary = self.module.validate(budget([1e16, 1.0, 1.0], "sum_bounds"))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(summary["combined_magnitude"], math.fsum([1e16, 1.0, 1.0]))

    def test_report_separately_has_no_combined_scalar(self) -> None:
        errors, warnings, summary = self.module.validate(budget([1.0], "report_separately"))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIsNone(summary["combined_magnitude"])


if __name__ == "__main__":
    unittest.main()
