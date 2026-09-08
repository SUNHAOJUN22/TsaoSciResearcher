"""One runtime catalog: execution modes are not inferred from documentation counts."""
from __future__ import annotations
from .core.jsonio import read_json
from .workspace import root


def capabilities() -> dict[str, dict]:
    registry = read_json(root() / "contracts/capabilities.json")
    result = {}
    for entry in registry["capabilities"]:
        key = entry["id"]
        if key in result:
            raise ValueError("duplicate capability id")
        for path in entry["source_files"]:
            resolved = (root() / path).resolve()
            if not resolved.is_relative_to(root()) or not resolved.is_file():
                raise ValueError(f"missing or invalid implementation for {key}")
        result[key] = entry
    return result
