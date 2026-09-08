"""Fail-closed Processing Skill contracts for status, balances, and numerics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import expm1, isfinite


class ContractError(ValueError):
    """Raised for invalid process-system contract inputs."""


_STATUS_RANK = {
    "PASS": 0,
    "NOT_EVALUATED": 1,
    "CONDITIONAL": 1,
    "HOLD": 2,
    "FAIL": 3,
}


def aggregate_status(statuses: Iterable[str]) -> str:
    values = list(statuses)
    if not values:
        return "HOLD"
    for status in values:
        if status not in _STATUS_RANK:
            raise ContractError(f"unknown status: {status}")
    worst = max(values, key=_STATUS_RANK.__getitem__)
    return "HOLD" if worst in {"NOT_EVALUATED", "CONDITIONAL"} else worst


def _real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a non-Boolean real")
    number = float(value)
    if not isfinite(number):
        raise ContractError(f"{name} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class Flow:
    value: float
    unit: str
    basis: str
    scale_to_canonical: float

    def canonical(self) -> float:
        number = _real(self.value, "flow")
        scale = _real(self.scale_to_canonical, "scale_to_canonical")
        if self.basis not in {"mass", "molar"} or scale <= 0.0 or not self.unit:
            raise ContractError("invalid flow metadata")
        return number * scale


def component_balance(
    inputs: Mapping[str, Flow],
    outputs: Mapping[str, Flow],
    generation: Mapping[str, Flow] | None = None,
    accumulation: Mapping[str, Flow] | None = None,
    *,
    atol: float,
    rtol: float,
) -> dict[str, object]:
    generated = generation or {}
    inventory_rate = accumulation or {}
    all_flows = [
        *inputs.values(),
        *outputs.values(),
        *generated.values(),
        *inventory_rate.values(),
    ]
    if not all_flows or len({flow.basis for flow in all_flows}) != 1:
        raise ContractError("one explicit mass or molar basis is required")
    absolute_tolerance = _real(atol, "atol")
    relative_tolerance = _real(rtol, "rtol")
    if absolute_tolerance < 0.0 or relative_tolerance < 0.0:
        raise ContractError("tolerances must be non-negative")

    residuals: dict[str, float] = {}
    failed: list[str] = []
    components = sorted(set(inputs) | set(outputs) | set(generated) | set(inventory_rate))
    for component in components:
        terms = (
            inputs[component].canonical() if component in inputs else 0.0,
            generated[component].canonical() if component in generated else 0.0,
            -(outputs[component].canonical() if component in outputs else 0.0),
            -(inventory_rate[component].canonical() if component in inventory_rate else 0.0),
        )
        residual = sum(terms)
        residuals[component] = residual
        scale = max(*(abs(term) for term in terms), 1.0e-30)
        if abs(residual) > absolute_tolerance + relative_tolerance * scale:
            failed.append(component)
    return {
        "status": "PASS" if not failed else "FAIL",
        "residuals": residuals,
        "failed_components": failed,
    }


def stable_conversion(value: object) -> float:
    argument = _real(value, "value")
    if argument < 0.0:
        raise ContractError("conversion argument must be non-negative")
    return -expm1(-argument)


def regression_metrics(observed: list[float], predicted: list[float]) -> dict[str, object]:
    if len(observed) != len(predicted) or not observed:
        raise ContractError("equal non-empty vectors are required")
    observed_values = [_real(value, "observed") for value in observed]
    predicted_values = [_real(value, "predicted") for value in predicted]
    errors = [
        predicted_value - observed_value
        for observed_value, predicted_value in zip(observed_values, predicted_values, strict=False)
    ]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = (sum(error * error for error in errors) / len(errors)) ** 0.5
    eligible = [
        abs(error / observed_value)
        for observed_value, error in zip(observed_values, errors, strict=False)
        if observed_value != 0.0
    ]
    return {
        "mae": mae,
        "rmse": rmse,
        "mape": sum(eligible) / len(eligible) if eligible else None,
        "mape_status": "DEFINED" if eligible else "UNDEFINED",
        "excluded_zero_observed": len(observed_values) - len(eligible),
    }


def public_distribution_status(records: list[Mapping[str, object]]) -> str:
    for record in records:
        if (
            record.get("confidentiality") in {"CONTROLLED_INTERNAL", "INTERNAL", "RESTRICTED"}
            or record.get("license_scope") == "PROJECT_CONTROLLED"
            or record.get("public_fixture_eligible") is not True
        ):
            return "BLOCKED_CONTROLLED_METADATA_CLASSIFICATION"
    return "PASS"
