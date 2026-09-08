"""Resolve the one governed source checkout, never infer missing domain engines."""
from __future__ import annotations
import os
from pathlib import Path


def root() -> Path:
    configured = os.environ.get("TSAO_WORKSPACE_ROOT")
    candidate = Path(configured).resolve() if configured else Path(__file__).resolve().parent.parent
    if not (candidate / "migration/source-lock.json").is_file():
        raise RuntimeError("domain execution needs the unified source checkout; set TSAO_WORKSPACE_ROOT")
    return candidate


def component_paths() -> dict[str, Path]:
    base = root()
    return {
        "research": base / "components/research",
        "computation": base / "components/computation",
        "aspen": base / "components/aspen",
        "dft": base / "components/dft",
        "processing": base / "components/processing",
        "resindb": base / "apps/resindb",
        "reasoning": base / "skills/reasoning",
    }
