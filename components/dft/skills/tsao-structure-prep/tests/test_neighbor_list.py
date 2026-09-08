from __future__ import annotations

import importlib.util
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"neighbor_contract_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NeighborListTests(unittest.TestCase):
    neighbors: Any
    geometry: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.neighbors = load_script("neighbor_list.py")
        cls.geometry = load_script("inspect_xyz.py")

    def assert_equivalent(
        self,
        coordinates: np.ndarray,
        cutoff: float,
        *,
        box: Any = None,
        periodic: Any = None,
    ) -> None:
        reference = self.neighbors.pairs_within_cutoff(
            coordinates,
            cutoff,
            box=box,
            periodic=periodic,
            backend="reference",
        )
        numpy_result = self.neighbors.pairs_within_cutoff(
            coordinates,
            cutoff,
            box=box,
            periodic=periodic,
            backend="numpy",
        )
        cell_list = self.neighbors.pairs_within_cutoff(
            coordinates,
            cutoff,
            box=box,
            periodic=periodic,
            backend="cell-list",
        )
        expected = [(pair.i, pair.j, pair.distance_angstrom) for pair in reference.pairs]
        for result in (numpy_result, cell_list):
            actual = [(pair.i, pair.j, pair.distance_angstrom) for pair in result.pairs]
            self.assertEqual([(i, j) for i, j, _ in actual], [(i, j) for i, j, _ in expected])
            for (_, _, left), (_, _, right) in zip(expected, actual, strict=True):
                self.assertAlmostEqual(left, right, places=12)

    def test_nonperiodic_backends_are_exactly_equivalent(self) -> None:
        rng = np.random.default_rng(17)
        coordinates = rng.normal(size=(80, 3)) * 5.0
        self.assert_equivalent(coordinates, 1.75)
        nearest = self.neighbors.nearest_pair_distance(coordinates)
        brute = self.neighbors.reference_pairs(coordinates, 1e6)
        self.assertAlmostEqual(nearest, min(pair.distance_angstrom for pair in brute.pairs), places=12)

    def test_orthogonal_periodic_minimum_image(self) -> None:
        coordinates = np.asarray([[0.1, 0.0, 0.0], [9.9, 0.0, 0.0], [5.0, 5.0, 5.0]])
        box = np.diag([10.0, 10.0, 10.0])
        self.assert_equivalent(coordinates, 0.5, box=box, periodic=True)
        result = self.neighbors.cell_list_pairs(coordinates, 0.5, box=box, periodic=True)
        self.assertEqual([(pair.i, pair.j) for pair in result.pairs], [(0, 1)])
        self.assertAlmostEqual(result.pairs[0].distance_angstrom, 0.2, places=12)

    def test_triclinic_and_partial_periodic_equivalence(self) -> None:
        rng = np.random.default_rng(23)
        box = np.asarray([[8.0, 0.0, 0.0], [1.8, 7.0, 0.0], [0.6, 1.1, 6.0]])
        coordinates = rng.random((90, 3)) @ box
        for periodic in (True, (True, False, True)):
            with self.subTest(periodic=periodic):
                self.assert_equivalent(coordinates, 1.4, box=box, periodic=periodic)

    def test_skewed_triclinic_uses_true_closest_lattice_image(self) -> None:
        box = np.asarray(
            [
                [5.0, 0.0, 0.0],
                [1.13077409, 5.0, 0.0],
                [-1.13995997, 4.87265737, 5.0],
            ]
        )
        fractional = np.asarray([0.96167068, 0.37108397, 0.30091855])
        coordinates = np.vstack([np.zeros(3), fractional @ box])
        delta = coordinates[1] - coordinates[0]
        cases = (
            (True, (0, 1, 2)),
            ((True, True, False), (0, 1)),
        )
        for periodic, axes in cases:
            with self.subTest(periodic=periodic):
                distances: list[float] = []
                for values in itertools.product(range(-2, 3), repeat=len(axes)):
                    shift = np.zeros(3)
                    for axis, value in zip(axes, values, strict=True):
                        shift[axis] = value
                    distances.append(float(np.linalg.norm(delta - shift @ box)))
                brute = min(distances)

                rounded = fractional.copy()
                for axis in axes:
                    rounded[axis] -= np.rint(rounded[axis])
                rounded_distance = float(np.linalg.norm(rounded @ box))
                self.assertGreater(rounded_distance, 3.0)
                self.assertLess(brute, 3.0)

                for backend in ("reference", "numpy", "cell-list"):
                    result = self.neighbors.pairs_within_cutoff(
                        coordinates,
                        3.0,
                        box=box,
                        periodic=periodic,
                        backend=backend,
                    )
                    self.assertEqual([(pair.i, pair.j) for pair in result.pairs], [(0, 1)])
                    self.assertAlmostEqual(result.pairs[0].distance_angstrom, brute, places=12)
                nearest = self.neighbors.nearest_pair_distance(
                    coordinates,
                    box=box,
                    periodic=periodic,
                )
                self.assertAlmostEqual(nearest, brute, places=12)

        near_half_box = np.asarray(
            [
                [1.0, 0.0, 0.0],
                [0.1, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        near_half_coordinates = np.asarray(
            [
                [0.0, 0.0, 0.0],
                [0.500000000000001, 0.0, 0.0],
            ]
        )
        for backend in ("reference", "numpy", "cell-list"):
            with self.subTest(near_half_backend=backend):
                result = self.neighbors.pairs_within_cutoff(
                    near_half_coordinates,
                    0.5,
                    box=near_half_box,
                    periodic=(True, False, False),
                    backend=backend,
                )
                self.assertEqual([(pair.i, pair.j) for pair in result.pairs], [(0, 1)])
                self.assertLess(result.pairs[0].distance_angstrom, 0.5)

    def test_cell_list_reduces_sparse_candidate_evaluations(self) -> None:
        axis = np.arange(0.0, 200.0, 2.0)
        coordinates = np.column_stack((axis, np.zeros_like(axis), np.zeros_like(axis)))
        result = self.neighbors.cell_list_pairs(coordinates, 1.1)
        self.assertEqual(result.pairs, ())
        self.assertLess(result.evaluated_pairs, result.total_pairs // 10)

    def test_duplicate_coordinates_and_deterministic_order(self) -> None:
        coordinates = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        first = self.neighbors.cell_list_pairs(coordinates, 1.1)
        second = self.neighbors.cell_list_pairs(coordinates, 1.1)
        self.assertEqual(first, second)
        self.assertEqual([(pair.i, pair.j) for pair in first.pairs], [(0, 1), (0, 2), (1, 2)])
        self.assertEqual(self.neighbors.nearest_pair_distance(coordinates), 0.0)

    def test_invalid_contracts_fail_closed(self) -> None:
        invalid = [
            ([], 1.0, None, None, "shape"),
            ([[0.0, 0.0, float("nan")]], 1.0, None, None, "finite"),
            ([[0.0, 0.0, 0.0]], True, None, None, "cutoff"),
            ([[0.0, 0.0, 0.0]], 0.0, None, None, "cutoff"),
            ([[0.0, 0.0, 0.0]], 1.0, None, True, "box"),
            ([[0.0, 0.0, 0.0]], 1.0, np.zeros((3, 3)), True, "nonsingular"),
            ([[0.0, 0.0, 0.0]], 1.0, np.eye(3), (True, False), "periodic"),
        ]
        for coordinates, cutoff, box, periodic, message in invalid:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.neighbors.pairs_within_cutoff(
                    coordinates,
                    cutoff,
                    box=box,
                    periodic=periodic,
                    backend="cell-list",
                )
        with self.assertRaisesRegex(ValueError, "backend"):
            self.neighbors.pairs_within_cutoff([[0.0, 0.0, 0.0]], 1.0, backend="cuda")

    def test_inspect_xyz_cell_list_matches_reference(self) -> None:
        rng = np.random.default_rng(41)
        coordinates = rng.normal(size=(180, 3)) * 4.0
        atoms = [
            {
                "index": index + 1,
                "element": ("C", "H", "O", "N")[index % 4],
                "x": float(point[0]),
                "y": float(point[1]),
                "z": float(point[2]),
            }
            for index, point in enumerate(coordinates)
        ]
        reference = self.geometry.inspect(atoms, backend="python")
        accelerated = self.geometry.inspect(atoms, backend="cell-list")
        for key in ("ok", "errors", "warnings", "heuristic_bonds", "minimum_pair_distance_angstrom"):
            if key == "minimum_pair_distance_angstrom":
                self.assertAlmostEqual(reference[key], accelerated[key], places=12)
            else:
                self.assertEqual(reference[key], accelerated[key])
        self.assertLess(accelerated["evaluated_pair_count"], accelerated["pair_count"])
        self.assertEqual(accelerated["pair_backend"], "cell-list")

    def test_periodic_inspection_and_cli_are_structured(self) -> None:
        atoms = [
            {"index": 1, "element": "H", "x": 0.1, "y": 0.0, "z": 0.0},
            {"index": 2, "element": "H", "x": 9.9, "y": 0.0, "z": 0.0},
        ]
        report = self.geometry.inspect(
            atoms,
            backend="cell-list",
            box=np.diag([10.0, 10.0, 10.0]).tolist(),
            periodic=True,
        )
        self.assertFalse(report["ok"])
        self.assertAlmostEqual(report["minimum_pair_distance_angstrom"], 0.2, places=12)
        self.assertEqual(report["periodic_axes"], {"x": True, "y": True, "z": True})

        with tempfile.TemporaryDirectory() as temporary:
            xyz = Path(temporary) / "periodic.xyz"
            xyz.write_text("2\nperiodic\nH 0.1 0 0\nH 9.9 0 0\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "inspect_xyz.py"),
                    str(xyz),
                    "--backend",
                    "cell-list",
                    "--periodic",
                    "xyz",
                    "--box",
                    "10",
                    "0",
                    "0",
                    "0",
                    "10",
                    "0",
                    "0",
                    "0",
                    "10",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertAlmostEqual(payload["minimum_pair_distance_angstrom"], 0.2, places=12)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
