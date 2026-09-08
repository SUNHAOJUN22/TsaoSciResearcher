from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from tsao_computation.registries import accelerators, adapters, capabilities, workflows


def _validate_shape(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for key in schema.get("required", []):
        if key not in record:
            problems.append(f"missing required field: {key}")
    return problems


def main() -> int:
    problems: list[str] = []
    schema_paths = sorted(Path("schemas").glob("*.json"))
    schemas = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in schema_paths}
    collections = {
        "capability.schema": capabilities(),
        "adapter.schema": adapters(),
        "accelerator-profile.schema": accelerators(),
        "workflow.schema": workflows(),
    }
    for name, records in collections.items():
        schema = schemas.get(name)
        if schema is None:
            problems.append(f"missing schema: {name}.json")
            continue
        for index, record in enumerate(records):
            for issue in _validate_shape(record, schema):
                problems.append(f"{name}[{index}]: {issue}")
    jsonschema_module: Any
    try:
        import jsonschema as jsonschema_module
    except ImportError:
        jsonschema_module = None
    if jsonschema_module is not None:
        for name, records in collections.items():
            schema = schemas.get(name)
            if schema is None:
                continue
            jsonschema_module.Draft202012Validator.check_schema(schema)
            validator = jsonschema_module.Draft202012Validator(schema)
            for index, record in enumerate(records):
                for error in validator.iter_errors(record):
                    problems.append(f"{name}[{index}] {error.json_path}: {error.message}")
    report = {"schema_version": "1.1", "passed": not problems, "problems": problems}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
