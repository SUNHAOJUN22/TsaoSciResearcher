from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/strict_numeric.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_strict_numeric", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


numeric = load_module()


class StrictNumericTests(unittest.TestCase):
    def test_exact_int_rejects_coercion_and_bounds(self) -> None:
        errors: list[str] = []
        self.assertEqual(numeric.exact_int(4, "value", errors, minimum=1), 4)
        self.assertEqual(errors, [])

        for coercion_value in (True, 4.0, "4", None):
            coercion_errors: list[str] = []
            self.assertEqual(numeric.exact_int(coercion_value, "value", coercion_errors, minimum=1, default=7), 7)
            self.assertEqual(coercion_errors, ["value must be an exact integer"])

        errors = []
        self.assertEqual(numeric.exact_int(0, "value", errors, minimum=1), 1)
        self.assertEqual(errors, ["value must be >= 1"])

    def test_finite_float_rejects_bool_string_nonfinite_and_bounds(self) -> None:
        errors: list[str] = []
        self.assertEqual(numeric.finite_float(4, "value", errors, minimum=0.1), 4.0)
        self.assertEqual(numeric.finite_float(4.5, "value", errors, minimum=0.1), 4.5)
        self.assertEqual(errors, [])

        for coercion_value in (True, "4", None):
            coercion_errors: list[str] = []
            self.assertEqual(numeric.finite_float(coercion_value, "value", coercion_errors, default=2.5), 2.5)
            self.assertEqual(coercion_errors, ["value must be a finite number"])

        for nonfinite_value in (math.nan, math.inf, -math.inf):
            nonfinite_errors: list[str] = []
            self.assertEqual(numeric.finite_float(nonfinite_value, "value", nonfinite_errors, default=2.5), 2.5)
            self.assertEqual(nonfinite_errors, ["value must be finite"])

        errors = []
        self.assertEqual(numeric.finite_float(0.05, "value", errors, minimum=0.1), 0.1)
        self.assertEqual(errors, ["value must be >= 0.1"])

    def test_exact_bool_rejects_truthy_standins(self) -> None:
        errors: list[str] = []
        self.assertTrue(numeric.exact_bool(True, "flag", errors))
        self.assertFalse(numeric.exact_bool(False, "flag", errors))
        self.assertEqual(errors, [])

        for standin in (1, 0, "true", None):
            standin_errors: list[str] = []
            self.assertTrue(numeric.exact_bool(standin, "flag", standin_errors, default=True))
            self.assertEqual(standin_errors, ["flag must be a boolean"])

    def test_exact_int_list_is_sorted_unique_and_fail_closed(self) -> None:
        errors: list[str] = []
        self.assertEqual(numeric.exact_int_list(None, "items", errors, [2, 1]), [2, 1])
        self.assertEqual(errors, [])

        errors = []
        self.assertEqual(numeric.exact_int_list([4, 2, 4], "items", errors, [1]), [2, 4])
        self.assertEqual(errors, [])

        invalid_lists: tuple[object, ...] = ([], "1,2", {1, 2})
        for invalid_list in invalid_lists:
            invalid_list_errors: list[str] = []
            self.assertEqual(numeric.exact_int_list(invalid_list, "items", invalid_list_errors, [1]), [1])
            self.assertEqual(invalid_list_errors, ["items must be a non-empty list"])

        errors = []
        self.assertEqual(numeric.exact_int_list([1, True, 2.0, "3", 4], "items", errors, [9]), [1, 4])
        self.assertEqual(
            errors,
            [
                "items[1] must be an exact integer",
                "items[2] must be an exact integer",
                "items[3] must be an exact integer",
            ],
        )

        errors = []
        self.assertEqual(numeric.exact_int_list([0, -1], "items", errors, [9], minimum=1), [9])
        self.assertEqual(errors, ["items[0] must be >= 1", "items[1] must be >= 1"])


if __name__ == "__main__":
    unittest.main()
