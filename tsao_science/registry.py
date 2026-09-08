"""Single capability inventory with component ownership and payload closure."""
from __future__ import annotations
from jsonschema import Draft202012Validator
from .core.jsonio import read_json
from .workspace import root, component_registry
from .contracts import payload_contracts


def capabilities() -> dict[str, dict]:
    base = root()
    owners = component_registry()
    registry = read_json(base / "contracts/capabilities.json")
    if registry.get("schema_version") != "tsao.capabilities/1":
        raise ValueError("unsupported capability registry")
    contracts = payload_contracts()
    result = {}
    for entry in registry["capabilities"]:
        if not isinstance(entry, dict) or set(entry) != {"id", "owner", "label", "mode", "source_files", "scientific_approval"}:
            raise ValueError("invalid capability entry")
        key = entry["id"]
        if not isinstance(key, str) or key in result or entry["owner"] not in owners:
            raise ValueError("invalid capability identity or owner")
        if entry["mode"] not in {"local-reference", "external-hold"} or entry["scientific_approval"] != "NOT_EVALUATED":
            raise ValueError("registry cannot confer scientific qualification")
        if not isinstance(entry["source_files"], list) or not entry["source_files"]:
            raise ValueError("capability needs implementation sources")
        for path in entry["source_files"]:
            if not isinstance(path, str):
                raise ValueError("implementation path must be a string")
            candidate = base / path
            resolved = candidate.resolve()
            if candidate.is_symlink() or not resolved.is_relative_to(base) or not resolved.is_file():
                raise ValueError(f"missing or invalid implementation for {key}")
            owner_path = (base / owners[entry["owner"]]["path"]).resolve()
            if not resolved.is_relative_to(owner_path) and not resolved.is_relative_to(base / "tsao_science"):
                raise ValueError("capability source crosses an unrelated component owner")
        if key not in contracts["inputs"] or (entry["mode"] == "local-reference" and key not in contracts["outputs"]):
            raise ValueError("capability input/output contract is incomplete")
        for group in ("inputs", "outputs"):
            if key in contracts[group]:
                Draft202012Validator.check_schema(contracts[group][key])
        result[key] = entry
    if set(contracts["inputs"]) != set(result) or set(contracts["outputs"]) != {k for k, row in result.items() if row["mode"] == "local-reference"}:
        raise ValueError("orphaned or missing runtime payload contract")
    return result
