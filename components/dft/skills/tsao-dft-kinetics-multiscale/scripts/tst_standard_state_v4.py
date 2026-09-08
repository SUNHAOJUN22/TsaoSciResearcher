"""Compatibility TST API for the kinetics multiscale Skill."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_CORE_PATH = Path(__file__).resolve().parents[2] / "tsao-dft-hpc-provenance/scripts/scientific_contracts_core_v18.py"
_NAME = "tsao_dft_scientific_contracts_core_v18"
_core = sys.modules.get(_NAME)
if _core is None:
    _spec = importlib.util.spec_from_file_location(_NAME, _CORE_PATH)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"cannot load {_CORE_PATH}")
    _core = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _core
    _spec.loader.exec_module(_core)

BOLTZMANN = _core.K_B
PLANCK = _core.H
GAS_CONSTANT = _core.R
StandardState = _core.StandardState
RateResult = _core.RateResult
TSTContractError = _core.TSTContractError


def eyring_rate(*, barrier, barrier_unit: str, temperature_K, molecularity: int = 1, standard_state=None):
    if _core is None:
        raise RuntimeError("scientific contracts core could not be loaded")
    return _core.eyring_rate(
        barrier,
        barrier_unit=barrier_unit,
        temperature_K=temperature_K,
        molecularity=molecularity,
        standard_state=standard_state,
        missing_standard_state_returns_invalid=True,
    )
