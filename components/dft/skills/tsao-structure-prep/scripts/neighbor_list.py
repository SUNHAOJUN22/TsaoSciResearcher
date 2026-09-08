#!/usr/bin/env python3
"""Deterministic reference, NumPy and cell-list neighbor search backends.

The module is a geometry acceleration layer, not electronic-structure evidence.
It supports non-periodic coordinates and full or partial periodicity in
orthogonal or triclinic cells. All backends use the same exact minimum-image
definition and return lexicographically ordered zero-based pairs.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

BACKENDS = ("auto", "reference", "numpy", "cell-list")
AUTO_CELL_LIST_ATOMS = 2048
BOX_DETERMINANT_EPSILON = 1e-12
MAX_MINIMUM_IMAGE_CANDIDATES = 100_000
MIC_BOUND_EPSILON = 1e-12
# Angstrom magnitudes beyond this reference-kernel domain are rejected explicitly.
NUMERIC_GEOMETRY_LIMIT = 1e100


@dataclass(frozen=True)
class NeighborPair:
    """One pair within the requested cutoff."""

    i: int
    j: int
    distance_angstrom: float


@dataclass(frozen=True)
class NeighborSearchResult:
    """Immutable deterministic neighbor-search result."""

    backend: str
    pairs: tuple[NeighborPair, ...]
    evaluated_pairs: int
    total_pairs: int


def _coordinates(value: Any) -> np.ndarray:
    coordinates = np.asarray(value, dtype=np.float64)
    if coordinates.ndim != 2 or coordinates.shape[1:] != (3,):
        raise ValueError("coordinates must have shape (N, 3)")
    if not np.isfinite(coordinates).all():
        raise ValueError("coordinates must be finite")
    if np.any(np.abs(coordinates) > NUMERIC_GEOMETRY_LIMIT):
        raise ValueError("coordinates exceed the numerical geometry domain")
    return np.ascontiguousarray(coordinates)


def _periodic(value: Any) -> tuple[bool, bool, bool]:
    if value is None:
        return (False, False, False)
    if isinstance(value, bool):
        return (value, value, value)
    if not isinstance(value, (tuple, list)) or len(value) != 3 or not all(isinstance(item, bool) for item in value):
        raise ValueError("periodic must be a bool or exactly three booleans")
    return cast(tuple[bool, bool, bool], tuple(value))


def _box(value: Any, periodic: tuple[bool, bool, bool]) -> tuple[np.ndarray | None, np.ndarray | None]:
    if value is None:
        if any(periodic):
            raise ValueError("periodic axes require a 3x3 box")
        return None, None
    box = np.asarray(value, dtype=np.float64)
    if box.shape != (3, 3) or not np.isfinite(box).all():
        raise ValueError("box must be a finite 3x3 matrix")
    determinant = float(np.linalg.det(box))
    if not math.isfinite(determinant) or abs(determinant) <= BOX_DETERMINANT_EPSILON:
        raise ValueError("box must be nonsingular")
    return np.ascontiguousarray(box), np.linalg.inv(box)


def _cutoff(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("cutoff must be a finite positive number")
    cutoff = float(value)
    if not math.isfinite(cutoff) or cutoff <= 0:
        raise ValueError("cutoff must be a finite positive number")
    if cutoff > NUMERIC_GEOMETRY_LIMIT:
        raise ValueError("cutoff exceeds the numerical geometry domain")
    return cutoff


def _orthogonal_box(box: np.ndarray) -> bool:
    gram = box @ box.T
    diagonal = np.diag(np.diag(gram))
    scale = max(1.0, float(np.max(np.abs(np.diag(gram)))))
    return bool(np.allclose(gram, diagonal, rtol=0.0, atol=1e-12 * scale))


def _exact_minimum_image_single(
    delta: np.ndarray,
    box: np.ndarray,
    periodic: tuple[bool, bool, bool],
) -> np.ndarray:
    periodic_axes = tuple(axis for axis, enabled in enumerate(periodic) if enabled)
    basis = box[list(periodic_axes), :]
    singular_values = np.linalg.svd(basis, compute_uv=False)
    sigma_max = float(singular_values[0])
    sigma_min = float(singular_values[-1])
    singular_limit = np.finfo(np.float64).eps * max(1.0, sigma_max) * 64.0
    if not math.isfinite(sigma_min) or sigma_min <= singular_limit:
        raise ValueError("periodic box basis is numerically singular")

    continuous_shift = np.linalg.lstsq(basis.T, delta, rcond=None)[0]
    if not np.isfinite(continuous_shift).all():
        raise ValueError("periodic minimum-image projection must be finite")
    initial_shift = tuple(round(float(value)) for value in continuous_shift)
    initial_vector = np.asarray(initial_shift, dtype=np.float64)
    perpendicular = delta - continuous_shift @ basis
    best = delta - initial_vector @ basis
    best_squared = float(np.dot(best, best))
    perpendicular_squared = float(np.dot(perpendicular, perpendicular))

    movable_squared = max(0.0, best_squared - perpendicular_squared)
    radius = math.nextafter(math.sqrt(movable_squared) / sigma_min, math.inf) + MIC_BOUND_EPSILON
    lower = tuple(math.floor(float(value) - radius) for value in continuous_shift)
    upper = tuple(math.ceil(float(value) + radius) for value in continuous_shift)
    candidate_count = math.prod(high - low + 1 for low, high in zip(lower, upper, strict=True))
    if candidate_count > MAX_MINIMUM_IMAGE_CANDIDATES:
        raise ValueError("exact minimum-image search exceeds the bounded candidate limit")

    best_shift = initial_shift
    ranges = (range(low, high + 1) for low, high in zip(lower, upper, strict=True))
    for values in itertools.product(*ranges):
        shift = np.asarray(values, dtype=np.float64)
        residual = delta - shift @ basis
        squared = float(np.dot(residual, residual))
        if squared < best_squared or (squared == best_squared and values < best_shift):
            best = residual
            best_squared = squared
            best_shift = values
    return best


def _minimum_image(
    delta: np.ndarray,
    box: np.ndarray | None,
    inverse_box: np.ndarray | None,
    periodic: tuple[bool, bool, bool],
) -> np.ndarray:
    if box is None or inverse_box is None or not any(periodic):
        return delta

    if _orthogonal_box(box):
        fractional = delta @ inverse_box
        for axis, enabled in enumerate(periodic):
            if enabled:
                fractional[..., axis] -= np.rint(fractional[..., axis])
        return fractional @ box

    array = np.asarray(delta, dtype=np.float64)
    if array.shape == (3,):
        return _exact_minimum_image_single(array, box, periodic)
    flat = array.reshape((-1, 3))
    if len(flat) == 0:
        return array.copy()
    reduced = np.vstack([_exact_minimum_image_single(vector, box, periodic) for vector in flat])
    return reduced.reshape(array.shape)


def _distance(
    left: np.ndarray,
    right: np.ndarray,
    box: np.ndarray | None,
    inverse_box: np.ndarray | None,
    periodic: tuple[bool, bool, bool],
) -> float:
    delta = _minimum_image(right - left, box, inverse_box, periodic)
    return float(np.linalg.norm(delta))


def _sort_pairs(pairs: Iterable[NeighborPair]) -> tuple[NeighborPair, ...]:
    return tuple(sorted(pairs, key=lambda pair: (pair.i, pair.j)))


def reference_pairs(
    coordinates: Any,
    cutoff: Any,
    *,
    box: Any = None,
    periodic: Any = None,
) -> NeighborSearchResult:
    """Enumerate all pairs with a scalar deterministic reference implementation."""

    points = _coordinates(coordinates)
    periodic_axes = _periodic(periodic)
    box_matrix, inverse_box = _box(box, periodic_axes)
    cutoff_value = _cutoff(cutoff)
    cutoff_squared = cutoff_value * cutoff_value
    pairs: list[NeighborPair] = []
    evaluated = 0
    for i in range(max(0, len(points) - 1)):
        for j in range(i + 1, len(points)):
            delta = _minimum_image(points[j] - points[i], box_matrix, inverse_box, periodic_axes)
            squared = float(np.dot(delta, delta))
            evaluated += 1
            if squared <= cutoff_squared:
                pairs.append(NeighborPair(i=i, j=j, distance_angstrom=math.sqrt(max(0.0, squared))))
    total = len(points) * (len(points) - 1) // 2
    return NeighborSearchResult("reference", _sort_pairs(pairs), evaluated, total)


def numpy_pairs(
    coordinates: Any,
    cutoff: Any,
    *,
    box: Any = None,
    periodic: Any = None,
) -> NeighborSearchResult:
    """Vectorize each row against the remaining coordinates with bounded memory."""

    points = _coordinates(coordinates)
    periodic_axes = _periodic(periodic)
    box_matrix, inverse_box = _box(box, periodic_axes)
    cutoff_value = _cutoff(cutoff)
    cutoff_squared = cutoff_value * cutoff_value
    pairs: list[NeighborPair] = []
    evaluated = 0
    for i in range(max(0, len(points) - 1)):
        delta = points[i + 1 :] - points[i]
        delta = _minimum_image(delta, box_matrix, inverse_box, periodic_axes)
        squared = np.einsum("ij,ij->i", delta, delta)
        evaluated += int(squared.size)
        for offset in np.flatnonzero(squared <= cutoff_squared):
            value = float(squared[int(offset)])
            pairs.append(
                NeighborPair(
                    i=i,
                    j=i + 1 + int(offset),
                    distance_angstrom=math.sqrt(max(0.0, value)),
                )
            )
    total = len(points) * (len(points) - 1) // 2
    return NeighborSearchResult("numpy", _sort_pairs(pairs), evaluated, total)


def _cell_space(
    points: np.ndarray,
    cutoff: float,
    box: np.ndarray | None,
    inverse_box: np.ndarray | None,
    periodic: tuple[bool, bool, bool],
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int], np.ndarray]:
    if box is None or inverse_box is None:
        working = points.copy()
        origin = working.min(axis=0) if len(working) else np.zeros(3, dtype=np.float64)
        span = np.ptp(working, axis=0) if len(working) else np.zeros(3, dtype=np.float64)
        reach = np.full(3, cutoff, dtype=np.float64)
    else:
        working = points @ inverse_box
        for axis, enabled in enumerate(periodic):
            if enabled:
                working[:, axis] %= 1.0
        reciprocal_norms = np.linalg.norm(inverse_box, axis=0)
        reach = cutoff * reciprocal_norms
        origin = np.zeros(3, dtype=np.float64)
        span = np.zeros(3, dtype=np.float64)
        for axis, enabled in enumerate(periodic):
            if enabled:
                origin[axis] = 0.0
                span[axis] = 1.0
            elif len(working):
                origin[axis] = float(working[:, axis].min())
                span[axis] = float(working[:, axis].max() - origin[axis])

    counts: list[int] = []
    widths = np.ones(3, dtype=np.float64)
    for axis in range(3):
        axis_span = float(span[axis])
        axis_reach = float(reach[axis])
        if axis_span <= 0 or axis_reach <= 0 or axis_span <= axis_reach:
            count = 1
            width = axis_span if axis_span > 0 else 1.0
        else:
            count = max(1, math.floor(axis_span / axis_reach))
            width = axis_span / count
        counts.append(count)
        widths[axis] = width
    cell_counts = cast(tuple[int, int, int], tuple(counts))
    return working, origin, cell_counts, widths


def _cell_index(
    point: np.ndarray,
    origin: np.ndarray,
    counts: tuple[int, int, int],
    widths: np.ndarray,
    periodic: tuple[bool, bool, bool],
) -> tuple[int, int, int]:
    values: list[int] = []
    for axis in range(3):
        count = counts[axis]
        if count == 1:
            values.append(0)
            continue
        raw = math.floor((float(point[axis]) - float(origin[axis])) / float(widths[axis]))
        if periodic[axis]:
            raw %= count
        else:
            raw = min(max(raw, 0), count - 1)
        values.append(raw)
    return cast(tuple[int, int, int], tuple(values))


def _neighbor_cells(
    cell: tuple[int, int, int],
    counts: tuple[int, int, int],
    periodic: tuple[bool, bool, bool],
) -> tuple[tuple[int, int, int], ...]:
    neighbors: set[tuple[int, int, int]] = set()
    for offset in itertools.product((-1, 0, 1), repeat=3):
        values: list[int] = []
        valid = True
        for axis in range(3):
            value = cell[axis] + offset[axis]
            if periodic[axis]:
                value %= counts[axis]
            elif value < 0 or value >= counts[axis]:
                valid = False
                break
            values.append(value)
        if valid:
            neighbors.add(cast(tuple[int, int, int], tuple(values)))
    return tuple(sorted(neighbors))


def cell_list_pairs(
    coordinates: Any,
    cutoff: Any,
    *,
    box: Any = None,
    periodic: Any = None,
) -> NeighborSearchResult:
    """Search occupied neighboring cells and verify every candidate exactly."""

    points = _coordinates(coordinates)
    periodic_axes = _periodic(periodic)
    box_matrix, inverse_box = _box(box, periodic_axes)
    cutoff_value = _cutoff(cutoff)
    cutoff_squared = cutoff_value * cutoff_value
    working, origin, counts, widths = _cell_space(
        points,
        cutoff_value,
        box_matrix,
        inverse_box,
        periodic_axes,
    )
    cells: dict[tuple[int, int, int], list[int]] = {}
    for index, point in enumerate(working):
        cells.setdefault(_cell_index(point, origin, counts, widths, periodic_axes), []).append(index)

    pairs: list[NeighborPair] = []
    evaluated = 0
    for cell in sorted(cells):
        left_indices = cells[cell]
        for neighbor in _neighbor_cells(cell, counts, periodic_axes):
            if neighbor not in cells or neighbor < cell:
                continue
            right_indices = cells[neighbor]
            candidates: Iterable[tuple[int, int]]
            if neighbor == cell:
                candidates = (
                    (left_indices[a], left_indices[b])
                    for a in range(len(left_indices))
                    for b in range(a + 1, len(left_indices))
                )
            else:
                candidates = itertools.product(left_indices, right_indices)
            for i, j in candidates:
                if i > j:
                    i, j = j, i
                delta = _minimum_image(points[j] - points[i], box_matrix, inverse_box, periodic_axes)
                squared = float(np.dot(delta, delta))
                evaluated += 1
                if squared <= cutoff_squared:
                    pairs.append(
                        NeighborPair(
                            i=i,
                            j=j,
                            distance_angstrom=math.sqrt(max(0.0, squared)),
                        )
                    )

    total = len(points) * (len(points) - 1) // 2
    unique = {(pair.i, pair.j): pair for pair in pairs}
    return NeighborSearchResult("cell-list", _sort_pairs(unique.values()), evaluated, total)


def pairs_within_cutoff(
    coordinates: Any,
    cutoff: Any,
    *,
    box: Any = None,
    periodic: Any = None,
    backend: str = "auto",
) -> NeighborSearchResult:
    """Dispatch to one validated backend without implicit device execution."""

    points = _coordinates(coordinates)
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}")
    selected = "cell-list" if backend == "auto" and len(points) >= AUTO_CELL_LIST_ATOMS else backend
    if selected == "auto":
        selected = "numpy"
    routes = {
        "reference": reference_pairs,
        "numpy": numpy_pairs,
        "cell-list": cell_list_pairs,
    }
    return routes[selected](points, cutoff, box=box, periodic=periodic)


def nearest_pair_distance(
    coordinates: Any,
    *,
    box: Any = None,
    periodic: Any = None,
    backend: str = "cell-list",
) -> float | None:
    """Return the exact global nearest-pair distance with a safe adaptive bound."""

    points = _coordinates(coordinates)
    periodic_axes = _periodic(periodic)
    box_matrix, inverse_box = _box(box, periodic_axes)
    if len(points) < 2:
        return None

    working = points if inverse_box is None else points @ inverse_box
    sampled_pairs: set[tuple[int, int]] = set()
    for axis in range(3):
        order = np.argsort(working[:, axis], kind="mergesort")
        for left, right in itertools.pairwise(order):
            left_index = int(left)
            right_index = int(right)
            sampled_pairs.add((min(left_index, right_index), max(left_index, right_index)))
        if periodic_axes[axis] and len(order) > 1:
            left_index = int(order[0])
            right_index = int(order[-1])
            sampled_pairs.add((min(left_index, right_index), max(left_index, right_index)))
    sampled_pairs.add((0, 1))

    upper = min(_distance(points[i], points[j], box_matrix, inverse_box, periodic_axes) for i, j in sampled_pairs)
    if upper <= 0:
        return 0.0
    result = pairs_within_cutoff(
        points,
        math.nextafter(upper, math.inf),
        box=box_matrix,
        periodic=periodic_axes,
        backend=backend,
    )
    if not result.pairs:
        return upper
    return min(pair.distance_angstrom for pair in result.pairs)
