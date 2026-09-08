from __future__ import annotations

import math

import numpy as np

from ._utils import validate_flow_mapping


def balance_residual(
    inputs: dict[str, float],
    outputs: dict[str, float],
    generation: dict[str, float] | None = None,
) -> dict[str, float]:
    checked_inputs = validate_flow_mapping("inputs", inputs, allow_negative=False)
    checked_outputs = validate_flow_mapping("outputs", outputs, allow_negative=False)
    checked_generation = validate_flow_mapping("generation", generation or {}, allow_negative=True)
    keys = set(checked_inputs) | set(checked_outputs) | set(checked_generation)
    return {
        key: checked_inputs.get(key, 0.0)
        + checked_generation.get(key, 0.0)
        - checked_outputs.get(key, 0.0)
        for key in sorted(keys)
    }


def closure_fraction(inputs: dict[str, float], outputs: dict[str, float]) -> float:
    checked_inputs = validate_flow_mapping("inputs", inputs, allow_negative=False)
    checked_outputs = validate_flow_mapping("outputs", outputs, allow_negative=False)
    total_in = math.fsum(checked_inputs.values())
    if total_in <= 0:
        raise ValueError("input total must be positive")
    return 1.0 - abs(total_in - math.fsum(checked_outputs.values())) / total_in


def stoichiometric_rank(matrix: list[list[float]]) -> int:
    try:
        values = np.asarray(matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("rectangular numeric matrix required") from exc
    if values.ndim != 2 or values.size == 0 or 0 in values.shape:
        raise ValueError("non-empty 2D matrix required")
    if not np.isfinite(values).all():
        raise ValueError("matrix values must be finite")
    return int(np.linalg.matrix_rank(values))
