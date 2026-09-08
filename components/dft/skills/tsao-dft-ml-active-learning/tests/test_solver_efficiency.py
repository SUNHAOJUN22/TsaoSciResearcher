from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "train_ridge_baseline.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tsao_ridge", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RidgeSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_primal_and_dual_predictions_match(self):
        rng = np.random.default_rng(17)
        matrix = rng.normal(size=(24, 40))
        target = rng.normal(size=24)
        primal = self.module.fit_ridge(matrix, target, 0.75, "primal")
        dual = self.module.fit_ridge(matrix, target, 0.75, "dual")
        primal_prediction = primal[0] + matrix @ primal[1]
        dual_prediction = dual[0] + matrix @ dual[1]
        np.testing.assert_allclose(primal_prediction, dual_prediction, rtol=1e-10, atol=1e-10)

    def test_unpenalized_intercept_is_feature_translation_invariant(self):
        rng = np.random.default_rng(23)
        matrix = rng.normal(size=(40, 6))
        target = 7.5 + matrix @ np.array([1.2, -0.7, 0.3, 2.0, -1.1, 0.5])
        shift = np.array([100.0, -40.0, 8.0, 13.0, -2.0, 77.0])
        shifted = matrix + shift
        original_fit = self.module.fit_ridge(matrix, target, 0.4, "primal")
        shifted_fit = self.module.fit_ridge(shifted, target, 0.4, "primal")
        original_prediction = original_fit[0] + matrix @ original_fit[1]
        shifted_prediction = shifted_fit[0] + shifted @ shifted_fit[1]
        np.testing.assert_allclose(original_prediction, shifted_prediction, rtol=1e-11, atol=1e-11)
        np.testing.assert_allclose(original_fit[1], shifted_fit[1], rtol=1e-11, atol=1e-11)

    def test_regularization_updates_diagonal_without_identity_allocation(self):
        matrix = np.arange(60.0).reshape(10, 6)
        target = np.arange(10.0)
        with patch.object(self.module.np, "eye", side_effect=AssertionError("identity allocation")):
            _, coefficients, solver, dimension = self.module.fit_ridge(matrix, target, 1.0, "primal")
        self.assertEqual(solver, "primal")
        self.assertEqual(dimension, 6)
        self.assertEqual(coefficients.shape, (6,))

    def test_auto_uses_dual_for_wide_matrix(self):
        matrix = np.arange(60.0).reshape(6, 10)
        target = np.arange(6.0)
        _, _, solver, dimension = self.module.fit_ridge(matrix, target, 1.0, "auto")
        self.assertEqual(solver, "dual")
        self.assertEqual(dimension, 6)

    def test_auto_uses_primal_for_tall_matrix(self):
        matrix = np.arange(60.0).reshape(10, 6)
        target = np.arange(10.0)
        _, _, solver, dimension = self.module.fit_ridge(matrix, target, 1.0, "auto")
        self.assertEqual(solver, "primal")
        self.assertEqual(dimension, 6)

    def test_zero_alpha_uses_stable_least_squares(self):
        matrix = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]])
        target = np.array([1.0, 2.0, 3.0, 4.0])
        intercept, coefficients, solver, dimension = self.module.fit_ridge(matrix, target, 0.0, "auto")
        prediction = intercept + matrix @ coefficients
        np.testing.assert_allclose(prediction, target, rtol=1e-12, atol=1e-12)
        self.assertEqual(solver, "lstsq")
        self.assertEqual(dimension, 3)

    def test_metrics_match_direct_definitions(self):
        observed = self.module.metrics([1.0, 2.0, 4.0], [1.5, 1.0, 5.0])
        self.assertAlmostEqual(observed["mae"], 2.5 / 3.0)
        self.assertAlmostEqual(observed["rmse"], np.sqrt(2.25 / 3.0))
        self.assertAlmostEqual(observed["r2"], 1.0 - 2.25 / (14.0 / 3.0))
        with self.assertRaisesRegex(ValueError, "aligned non-empty"):
            self.module.metrics([], [])

    def test_negative_and_nonfinite_alpha_are_rejected(self):
        matrix = np.eye(3)
        target = np.arange(3.0)
        for alpha in (-0.1, float("nan"), float("inf")):
            with self.subTest(alpha=alpha), self.assertRaisesRegex(ValueError, "finite and non-negative"):
                self.module.fit_ridge(matrix, target, alpha, "auto")

    def test_non_finite_values_and_empty_dimensions_are_rejected(self):
        matrix = np.array([[1.0, np.nan], [2.0, 3.0]])
        target = np.array([1.0, 2.0])
        with self.assertRaisesRegex(ValueError, "finite values"):
            self.module.fit_ridge(matrix, target, 1.0, "auto")
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.module.fit_ridge(np.empty((2, 0)), target, 1.0, "auto")


if __name__ == "__main__":
    unittest.main()
