from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import exp, isfinite

BOLTZMANN_J_K = 1.380649e-23
PLANCK_J_S = 6.62607015e-34
GAS_CONSTANT_J_MOL_K = 8.31446261815324

FATAL_MARKERS = (
    "error termination",
    "fatal error",
    "segmentation fault",
    "zbrent fatal",
    "very serious problems",
    "brmix: very serious problems",
    "convergence not achieved",
    "maximum number of electronic steps reached",
)
SUCCESS_MARKERS = (
    "normal termination",
    "reached required accuracy",
    "job done",
    "program ended at",
)


@dataclass(frozen=True)
class ParseDecision:
    status: str
    reason_codes: tuple[str, ...]
    success_markers: tuple[str, ...]
    fatal_markers: tuple[str, ...]


def parse_termination(lines: Iterable[str]) -> ParseDecision:
    normalized = [line.casefold() for line in lines]
    successes = tuple(marker for marker in SUCCESS_MARKERS if any(marker in line for line in normalized))
    fatals = tuple(marker for marker in FATAL_MARKERS if any(marker in line for line in normalized))
    if fatals:
        return ParseDecision(
            status="FAILED",
            reason_codes=("FATAL_MARKER_PRESENT",),
            success_markers=successes,
            fatal_markers=fatals,
        )
    if successes:
        return ParseDecision(
            status="CONVERGED",
            reason_codes=(),
            success_markers=successes,
            fatal_markers=(),
        )
    return ParseDecision(
        status="INCOMPLETE",
        reason_codes=("NO_TERMINAL_EVIDENCE",),
        success_markers=(),
        fatal_markers=(),
    )


def tst_rate_constant(
    delta_g_activation_j_mol: float,
    temperature_k: float,
    *,
    standard_state_factor: float = 1.0,
) -> float:
    for name, raw in (
        ("delta_g_activation_j_mol", delta_g_activation_j_mol),
        ("temperature_k", temperature_k),
        ("standard_state_factor", standard_state_factor),
    ):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise TypeError(f"{name} must be a non-boolean real number")
        if not isfinite(float(raw)):
            raise ValueError(f"{name} must be finite")
    temperature_k = float(temperature_k)
    standard_state_factor = float(standard_state_factor)
    if temperature_k <= 0.0 or standard_state_factor <= 0.0:
        raise ValueError("temperature and standard-state factor must be positive")
    prefactor = BOLTZMANN_J_K * temperature_k / PLANCK_J_S
    exponent = -float(delta_g_activation_j_mol) / (GAS_CONSTANT_J_MOL_K * temperature_k)
    rate = prefactor * exp(exponent) * standard_state_factor
    if not isfinite(rate):
        raise OverflowError("non-finite TST rate")
    return rate


def validate_quantity_shape(kind: str, shape: tuple[int, ...], *, atom_count: int | None = None) -> None:
    expected: tuple[int, ...]
    if kind == "scalar":
        expected = ()
    elif kind == "forces":
        if atom_count is None or atom_count <= 0:
            raise ValueError("forces require a positive atom_count")
        expected = (atom_count, 3)
    elif kind == "stress_voigt":
        expected = (6,)
    elif kind == "stress_tensor":
        expected = (3, 3)
    else:
        raise ValueError(f"unknown quantity kind: {kind}")
    if shape != expected:
        raise ValueError(f"shape {shape} is invalid for {kind}; expected {expected}")


def external_execution_status(*, parser_converged: bool, signed_external_receipt: bool) -> str:
    if not parser_converged:
        return "COMPUTATION_NOT_CONVERGED"
    if not signed_external_receipt:
        return "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"
    return "EXTERNAL_EXECUTION_VERIFIED"
