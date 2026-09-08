"""Composite version-4 DFT scientific contracts."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

_LOADER_PATH = Path(__file__).with_name("_load_v18_core.py")
_LOADER_SPEC = importlib.util.spec_from_file_location("tsao_dft_v18_core_loader", _LOADER_PATH)
if _LOADER_SPEC is None or _LOADER_SPEC.loader is None:
    raise RuntimeError(f"cannot load {_LOADER_PATH}")
_LOADER = importlib.util.module_from_spec(_LOADER_SPEC)
sys.modules.setdefault(_LOADER_SPEC.name, _LOADER)
_LOADER_SPEC.loader.exec_module(_LOADER)
_core = _LOADER.load_core()
K_B = _core.K_B
H = _core.H
R = _core.R
DFTContractError = _core.DFTContractError
StandardState = _core.StandardState


@dataclass(frozen=True)
class EngineDecision:
    parser_accepted: bool
    reason_codes: tuple[str, ...]
    segment_count: int
    final_segment: int


@dataclass(frozen=True)
class QuantityDecision:
    accepted: bool
    reason_codes: tuple[str, ...]


def evaluate_engine_output(engine: str, text: str) -> EngineDecision:
    record = _core.parse_engine_output(engine, text, accepted_status="CONVERGED", failure_prefix="")
    reasons = record.reason_codes
    if record.status in {"FATAL", "NONCONVERGED"}:
        reasons = ("FATAL_OR_NONCONVERGENCE_MARKER",)
    elif record.status == "INCOMPLETE":
        reasons = ("NORMAL_TERMINATION_MISSING",)
    return EngineDecision(record.parser_accepted, reasons, len(record.jobs), max(0, len(record.jobs) - 1))


def tst_rate(*, barrier, barrier_unit: str, temperature_K, molecularity: int = 1, standard_state=None):
    return _core.eyring_rate(
        barrier,
        barrier_unit=barrier_unit,
        temperature_K=temperature_K,
        molecularity=molecularity,
        standard_state=standard_state,
    )


def validate_quantity_shape(value) -> QuantityDecision:
    try:
        kind = value.get("quantity_kind")
        aggregation = value.get("aggregation")
        values = value.get("values")
        convention = value.get("component_convention")
        if kind != "stress_tensor" or aggregation != "full":
            return QuantityDecision(False, ("KIND_OR_AGGREGATION_INVALID",))
        if not isinstance(values, (list, tuple)) or len(values) != 6:
            return QuantityDecision(False, ("FULL_STRESS_REQUIRES_VOIGT_6",))
        _core.TypedQuantity(
            quantity_kind="stress_tensor_full",
            values=values,
            unit="GPa",
            shape=(6,),
            aggregation="full",
            component_convention=convention,
        )
    except (AttributeError, _core.DFTContractError):
        return QuantityDecision(False, ("QUANTITY_INVALID",))
    return QuantityDecision(True, ())
