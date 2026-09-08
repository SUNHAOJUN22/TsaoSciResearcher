"""Stable v4 parser API over the shared fail-closed contract core."""

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
ParserRecord = _core.ParserRecord


def parse_engine_output(engine: str, text: str) -> Any:
    record = _core.parse_engine_output(engine, text, accepted_status="ACCEPTED", failure_prefix="")
    if record.status in {"FATAL", "NONCONVERGED"}:
        return ParserRecord(
            record.engine,
            f"FAILED_{record.status}",
            False,
            record.exit_code,
            record.reason_codes,
            record.jobs,
            record.truncated,
        )
    return record


def parse_engine_stream(engine: str, chunks, *, max_bytes: int = 64 * 1024 * 1024) -> Any:
    return _core.parse_engine_stream(engine, chunks, max_bytes=max_bytes)
