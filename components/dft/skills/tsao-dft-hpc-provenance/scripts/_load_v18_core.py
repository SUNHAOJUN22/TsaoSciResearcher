"""Load the repository-local V18 contract core from a hyphenated Skill path."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_core() -> ModuleType:
    name = "tsao_dft_scientific_contracts_core_v18"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = Path(__file__).with_name("scientific_contracts_core_v18.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
