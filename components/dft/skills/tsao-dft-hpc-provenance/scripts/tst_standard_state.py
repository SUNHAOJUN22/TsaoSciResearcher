"""Dimensionally explicit transition-state-theory standard-state contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_LOADER_PATH = Path(__file__).with_name("_load_v18_core.py")
_LOADER_SPEC = importlib.util.spec_from_file_location("tsao_dft_v18_core_loader", _LOADER_PATH)
if _LOADER_SPEC is None or _LOADER_SPEC.loader is None:
    raise RuntimeError(f"cannot load {_LOADER_PATH}")
_LOADER = importlib.util.module_from_spec(_LOADER_SPEC)
sys.modules.setdefault(_LOADER_SPEC.name, _LOADER)
_LOADER_SPEC.loader.exec_module(_LOADER)
_core = _LOADER.load_core()
BOLTZMANN = _core.K_B
PLANCK = _core.H
GAS_CONSTANT = _core.R
StandardState = _core.StandardState
RateResult = _core.RateResult
TSTContractError = _core.TSTContractError


def eyring_rate(barrier, *, barrier_unit: str, temperature_K, molecularity: int = 1, standard_state=None):
    return _core.eyring_rate(
        barrier,
        barrier_unit=barrier_unit,
        temperature_K=temperature_K,
        molecularity=molecularity,
        standard_state=standard_state,
    )
