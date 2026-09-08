"""Fail-closed parser, TST, and model-acceptance contracts for TSAO DFT."""

from __future__ import annotations

from math import exp, isfinite


class ContractError(ValueError):
    """Raised for invalid DFT scientific-contract input."""


_FATAL_MARKERS = (
    "error termination",
    "zbrent: fatal",
    "error in routine",
    "convergence not achieved",
    "abort",
    "scf not converged",
)
_SUCCESS_MARKERS = (
    "normal termination",
    "general timing and accounting",
    "job done",
    "program ended",
)


def parser_status(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return "HOLD_INCOMPLETE"
    segments = [segment for segment in text.lower().split("\n--job--\n") if segment.strip()]
    final_segment = segments[-1]
    if any(marker in final_segment for marker in _FATAL_MARKERS):
        return "FAIL_FATAL"
    if any(marker in final_segment for marker in _SUCCESS_MARKERS):
        return "PASS"
    return "HOLD_INCOMPLETE"


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a non-Boolean real")
    number = float(value)
    if not isfinite(number):
        raise ContractError(f"{name} must be finite")
    return number


def tst_rate(
    *,
    delta_g_j_mol: float,
    temperature_k: float,
    molecularity: int,
    standard_state_mol_l: float | None = None,
    kappa: float = 1.0,
) -> tuple[float, str]:
    barrier = _finite(delta_g_j_mol, "delta_g_j_mol")
    temperature = _finite(temperature_k, "temperature_k")
    transmission = _finite(kappa, "kappa")
    if temperature <= 0.0 or not 0.0 < transmission <= 1.0:
        raise ContractError("temperature and transmission coefficient are invalid")
    if isinstance(molecularity, bool) or not isinstance(molecularity, int) or molecularity < 1:
        raise ContractError("molecularity must be a positive integer")
    if molecularity > 1:
        if standard_state_mol_l is None:
            raise ContractError("explicit standard state is required")
        standard_state = _finite(standard_state_mol_l, "standard_state_mol_l")
        if standard_state <= 0.0:
            raise ContractError("standard state must be positive")
    else:
        standard_state = 1.0

    boltzmann = 1.380649e-23
    planck = 6.62607015e-34
    gas_constant = 8.314462618
    first_order_rate = transmission * boltzmann * temperature / planck * exp(-barrier / (gas_constant * temperature))
    rate = first_order_rate * standard_state ** (1 - molecularity)
    unit = "s^-1" if molecularity == 1 else f"L^{molecularity - 1} mol^{1 - molecularity} s^-1"
    return rate, unit


def model_acceptance(card: dict[str, object]) -> str:
    required = {
        "dataset_sha256",
        "model_sha256",
        "code_sha256",
        "environment_sha256",
        "applicability_domain",
        "calibrated_uncertainty",
        "holdout_validation",
        "independent_approval",
    }
    if not required.issubset(card):
        return "HOLD_INCOMPLETE_EVIDENCE"
    for key in ("dataset_sha256", "model_sha256", "code_sha256", "environment_sha256"):
        value = card[key]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            return "INVALID_DIGEST"
    if card["independent_approval"] is not True:
        return "HOLD_INDEPENDENT_APPROVAL"
    return "ACCEPTED"
