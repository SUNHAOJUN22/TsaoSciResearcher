from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import expm1, fsum, isfinite

STATUS_RANK: dict[str, int] = {
    "PASS": 0,
    "NOT_EVALUATED": 1,
    "CONDITIONAL": 1,
    "HOLD": 2,
    "FAIL": 3,
}


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str
    dimension: str
    scale_to_si: float

    def canonical(self) -> float:
        for name, raw in (("value", self.value), ("scale_to_si", self.scale_to_si)):
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise TypeError(f"{name} must be a non-boolean real number")
            if not isfinite(float(raw)):
                raise ValueError(f"{name} must be finite")
        if self.scale_to_si <= 0.0:
            raise ValueError("scale_to_si must be positive")
        if not self.unit or not self.dimension:
            raise ValueError("unit and dimension are required")
        return float(self.value) * float(self.scale_to_si)


@dataclass(frozen=True)
class BalanceDecision:
    status: str
    residuals: Mapping[str, float]
    reason_codes: tuple[str, ...]


def aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "NOT_EVALUATED"
    unknown = sorted(set(statuses) - STATUS_RANK.keys())
    if unknown:
        raise ValueError(f"unknown status values: {unknown}")
    return max(statuses, key=lambda status: STATUS_RANK[status])


def component_balance(
    inputs: Mapping[str, Quantity],
    outputs: Mapping[str, Quantity],
    sources: Mapping[str, Quantity] | None = None,
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> BalanceDecision:
    for name, raw in (
        ("absolute_tolerance", absolute_tolerance),
        ("relative_tolerance", relative_tolerance),
    ):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise TypeError(f"{name} must be a non-boolean real number")
        if not isfinite(float(raw)) or float(raw) < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")
    source_map = sources or {}
    quantities = [*inputs.values(), *outputs.values(), *source_map.values()]
    if not quantities:
        raise ValueError("at least one component quantity is required")
    dimensions = {quantity.dimension for quantity in quantities}
    if len(dimensions) != 1:
        raise ValueError("all balance quantities must share one basis dimension")
    residuals: dict[str, float] = {}
    reasons: list[str] = []
    for component in sorted(set(inputs) | set(outputs) | set(source_map)):
        inlet = inputs[component].canonical() if component in inputs else 0.0
        outlet = outputs[component].canonical() if component in outputs else 0.0
        source = source_map[component].canonical() if component in source_map else 0.0
        residual = fsum((inlet, source, -outlet))
        residuals[component] = residual
        scale = max(abs(inlet), abs(outlet), abs(source), 1.0)
        threshold = float(absolute_tolerance) + float(relative_tolerance) * scale
        if abs(residual) > threshold:
            reasons.append(f"COMPONENT_RESIDUAL:{component}")
    return BalanceDecision("PASS" if not reasons else "FAIL", residuals, tuple(reasons))


def stable_first_order_conversion(exposure: float) -> float:
    if isinstance(exposure, bool) or not isinstance(exposure, (int, float)):
        raise TypeError("exposure must be a non-boolean real number")
    exposure = float(exposure)
    if not isfinite(exposure) or exposure < 0.0:
        raise ValueError("exposure must be finite and non-negative")
    return -expm1(-exposure)


def mean_absolute_percentage_error(observed: list[float], predicted: list[float]) -> float | None:
    if len(observed) != len(predicted) or not observed:
        raise ValueError("observed and predicted must be non-empty and have equal length")
    terms: list[float] = []
    for actual, estimate in zip(observed, predicted, strict=True):
        if isinstance(actual, bool) or isinstance(estimate, bool):
            raise TypeError("series values must be non-boolean real numbers")
        actual = float(actual)
        estimate = float(estimate)
        if not isfinite(actual) or not isfinite(estimate):
            raise ValueError("series values must be finite")
        if actual != 0.0:
            terms.append(abs((actual - estimate) / actual))
    return None if not terms else fsum(terms) / len(terms)
