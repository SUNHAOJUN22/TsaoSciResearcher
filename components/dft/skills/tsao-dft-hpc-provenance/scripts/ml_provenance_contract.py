"""Checksum-bound DFT dataset and predictive-model evidence contracts."""

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
MLProvenanceError = _core.MLProvenanceError
DatasetValidationArtifact = _core.DatasetValidationArtifactV4


def authorize_training(dataset_path, artifact, *, expected_schema: str):
    return _core.authorize_training_v4(dataset_path, artifact, expected_schema=expected_schema)


def validate_model_card(card):
    return _core.validate_model_card_v4(card)
