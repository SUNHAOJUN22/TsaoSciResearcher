"""Version-4 fail-closed engine parser and quantity compatibility contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_LOADER_PATH = Path(__file__).with_name("_load_v18_core.py")
_LOADER_SPEC = importlib.util.spec_from_file_location("tsao_dft_v18_core_loader", _LOADER_PATH)
if _LOADER_SPEC is None or _LOADER_SPEC.loader is None:
    raise RuntimeError(f"cannot load {_LOADER_PATH}")
_LOADER = importlib.util.module_from_spec(_LOADER_SPEC)
sys.modules.setdefault(_LOADER_SPEC.name, _LOADER)
_LOADER_SPEC.loader.exec_module(_LOADER)
_core = _LOADER.load_core()
ParserContractError = _core.ParserContractError
QuantityRecord = _core.QuantityRecord
JobRecord = _core.JobRecord
ParserRecord = _core.ParserRecord


def parse_engine_output(engine: str, text: str) -> Any:
    return _core.parse_engine_output(engine, text, accepted_status="CONVERGED", failure_prefix="")


def parse_engine_stream(engine: str, chunks, *, max_bytes: int = 64 * 1024 * 1024) -> Any:
    result = _core.parse_engine_stream(engine, chunks, max_bytes=max_bytes)
    if result.parser_accepted:
        return ParserRecord(result.engine, "CONVERGED", True, 0, result.reason_codes, result.jobs, result.truncated)
    return result
