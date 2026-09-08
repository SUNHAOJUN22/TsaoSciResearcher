"""The same input/output contracts govern preview, workers and imported results."""
from __future__ import annotations
from typing import Any
from jsonschema import Draft202012Validator, validators
from .core.jsonio import read_json, validate_json
from .workspace import root


def _is_reference(value: Any) -> bool:
    return type(value) is dict and set(value) == {"$ref"} and isinstance(value["$ref"], str)


def _defer(validator):
    def wrapped(context, rule, instance, schema):
        if not _is_reference(instance):
            yield from validator(context, rule, instance, schema)
    return wrapped


ReferenceValidator = validators.extend(Draft202012Validator,
    {name: _defer(check) for name, check in Draft202012Validator.VALIDATORS.items()})


def payload_contracts() -> dict:
    document = read_json(root() / "contracts/payloads.json")
    if document.get("schema_version") != "tsao.payload-contracts/1":
        raise ValueError("unsupported payload contract version")
    return document


def validate_payload(capability: str, payload: Any, *, output: bool = False, deferred: bool = False) -> None:
    validate_json(payload)
    group = "outputs" if output else "inputs"
    schemas = payload_contracts()[group]
    if capability not in schemas:
        raise ValueError("capability has no declared payload contract")
    schema = schemas[capability]
    validator = ReferenceValidator(schema) if deferred else Draft202012Validator(schema)
    error = next(validator.iter_errors(payload), None)
    if error is not None:
        # Report the structural location, not potentially confidential field values.
        location = ".".join(map(str, error.absolute_path)) or "$"
        raise ValueError(f"{capability} {group} contract failed at {location} ({error.validator})")


def enforce_lineage(capability: str, payload: dict, dependencies: dict) -> None:
    if capability != "materials.observation" or not dependencies:
        return
    kind = payload["observation"]["evidence_kind"]
    # All current executable producers are local references, not experiments or
    # qualified external simulations. Metadata lineage may never upgrade them.
    parent_kinds = {row.get("evidence_kind", "reference") for row in dependencies.values()}
    allowed = {"reference", "hypothesis"} if parent_kinds - {"measured"} else {"measured", "hypothesis"}
    if kind not in allowed:
        raise ValueError("derived observation cannot upgrade its dependency evidence kind")


def data_dependencies(payload: Any) -> set[str]:
    """Data references, not ordering-only prerequisites, determine evidence lineage."""
    if _is_reference(payload):
        return {payload["$ref"].split(".", 1)[0]}
    if isinstance(payload, dict):
        return set().union(*(data_dependencies(v) for v in payload.values())) if payload else set()
    if isinstance(payload, list):
        return set().union(*(data_dependencies(v) for v in payload)) if payload else set()
    return set()
