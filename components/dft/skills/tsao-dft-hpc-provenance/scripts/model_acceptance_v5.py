"""Independent, hash-bound DFT-ML model acceptance contracts."""

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
ModelAcceptanceError = _core.ModelAcceptanceError
DatasetValidationArtifact = _core.DatasetValidationArtifact
ModelCard = _core.ModelCard
ModelApproval = _core.ModelApproval
sign_approval = _core.sign_approval
assess_model_card = _core.assess_model_card
validate_labels = _core.validate_labels
authorize_training = _core.authorize_training_v5
validate_predictive_model_card = _core.validate_predictive_model_card
