"""Single component registry for CLI, adapters, planning and diagnostics."""
from __future__ import annotations
import os
from pathlib import Path
from .core.jsonio import read_json


def root() -> Path:
    configured = os.environ.get("TSAO_WORKSPACE_ROOT")
    candidate = Path(configured).resolve() if configured else Path(__file__).resolve().parent.parent
    if not (candidate / "migration/source-lock.json").is_file():
        raise RuntimeError("domain execution needs the unified source checkout; set TSAO_WORKSPACE_ROOT")
    return candidate


def component_registry() -> dict[str, dict]:
    base = root()
    document = read_json(base / "contracts/components.json")
    if document.get("schema_version") != "tsao.components/1":
        raise ValueError("unsupported component registry")
    origins = {row["repository"]: row["destination"] for row in read_json(base / "migration/source-lock.json")["sources"]}
    result = {}
    for item in document["components"]:
        if not isinstance(item, dict) or set(item) != {"id", "path", "origin", "entry_module", "kind", "catalog_sources"}:
            raise ValueError("invalid component entry")
        key, path = item["id"], item["path"]
        if not isinstance(key, str) or not key.isidentifier() or key in result:
            raise ValueError("invalid or duplicate component identifier")
        if item["kind"] not in {"module", "script", "web"}:
            raise ValueError("invalid component kind")
        if item["kind"] == "module" and not isinstance(item["entry_module"], str):
            raise ValueError("module entry required")
        if origins.get(item["origin"]) != path or not (base / path).resolve().is_relative_to(base):
            raise ValueError("component location disagrees with preserved source identity")
        result[key] = item
    if len(result) != 7 or {item["origin"] for item in result.values()} != set(origins):
        raise ValueError("all seven origins need exactly one owned component")
    return result


def component_paths() -> dict[str, Path]:
    return {key: root() / row["path"] for key, row in component_registry().items()}
