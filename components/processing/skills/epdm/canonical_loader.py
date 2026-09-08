"""Transactional JSON-to-contract loader for EPDM V2 projects.

The loader validates structure, applies an explicit version migration decision,
constructs frozen contract dataclasses in a temporary registry, validates all
cross-registry references, and only then returns an immutable published
snapshot. No partial registry is exposed on failure.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import types
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

from . import _validation_v2_core as _validation
from .contracts import (
    ApplicabilityDomain,
    CalibrationPlan,
    CatalystPassport,
    ContractValidationError,
    DienePassport,
    EvidenceRecord,
    EvidenceReference,
    KineticDataset,
    KineticParameter,
    ModelQualification,
    RateLawDefinition,
    StateDefinition,
    ThermoPassport,
)
from .registry import ContractRegistry, CrossRegistryReferenceError, RegistryError

LOADER_VERSION = "1.0.0-phase-a1"
CANONICAL_PROJECT_SCHEMA = "TSAO-EPDM-CANONICAL-PROJECT-1"
SUPPORTED_PROJECT_SCHEMA_VERSION = "2.0.0"

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProjectMigrationReceipt:
    source_version: str
    target_version: str
    steps: tuple[str, ...]
    evidence_fabricated: bool = False


@dataclass(frozen=True, slots=True)
class CanonicalLoadIssue:
    phase: str
    path: str
    message: str


class CanonicalProjectLoadError(ValueError):
    """Fail-closed canonical-load error with an explicit processing phase."""

    def __init__(self, issue: CanonicalLoadIssue) -> None:
        self.issue = issue
        super().__init__(f"{issue.phase} at {issue.path}: {issue.message}")


@dataclass(frozen=True, slots=True)
class ContractRegistrySnapshot:
    evidence: Mapping[str, EvidenceRecord]
    applicability_domains: Mapping[str, ApplicabilityDomain]
    catalysts: Mapping[str, CatalystPassport]
    dienes: Mapping[str, DienePassport]
    rate_laws: Mapping[str, RateLawDefinition]
    kinetic_parameters: Mapping[str, KineticParameter]
    thermo_passports: Mapping[str, ThermoPassport]
    datasets: Mapping[str, KineticDataset]
    manifest: Mapping[str, Any]
    content_sha256: str

    def require(self, registry_name: str, identifier: str) -> object:
        registries: Mapping[str, Mapping[str, object]] = MappingProxyType(
            {
                "evidence": self.evidence,
                "applicability_domains": self.applicability_domains,
                "catalysts": self.catalysts,
                "dienes": self.dienes,
                "rate_laws": self.rate_laws,
                "kinetic_parameters": self.kinetic_parameters,
                "thermo_passports": self.thermo_passports,
                "datasets": self.datasets,
            }
        )
        try:
            registry = registries[registry_name]
        except KeyError as exc:
            raise KeyError(f"unknown registry snapshot: {registry_name}") from exc
        try:
            return registry[identifier]
        except KeyError as exc:
            raise KeyError(f"unresolved {registry_name} ID: {identifier}") from exc


@dataclass(frozen=True, slots=True)
class CanonicalProjectSnapshot:
    project_id: str
    schema_version: str
    loader_version: str
    migration: ProjectMigrationReceipt
    source_sha256: str
    publication_sha256: str
    registry: ContractRegistrySnapshot
    state_definitions: Mapping[str, StateDefinition]
    calibration_plans: Mapping[str, CalibrationPlan]
    qualification: ModelQualification
    canonical_project: Mapping[str, Any]
    manifest: Mapping[str, Any]

    def to_json(self) -> str:
        return _canonical_json(_thaw(self.manifest))


def _error(phase: str, path: str, message: str) -> CanonicalProjectLoadError:
    return CanonicalProjectLoadError(CanonicalLoadIssue(phase, path, message))


def _canonical_json(payload: object) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise _error("canonicalization", "$", str(exc)) from exc


def _sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__type__": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": {item.name: _thaw(getattr(value, item.name)) for item in fields(value)},
        }
    return value


def _json_copy(value: object) -> dict[str, Any]:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _error(
            "input",
            "$",
            "project must contain only finite JSON-compatible values",
        ) from exc
    if not isinstance(decoded, dict):
        raise _error("input", "$", "project root must be an object")
    return decoded


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error("json_parse", "$", f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise _error("json_parse", "$", f"non-finite JSON token is prohibited: {value}")


def parse_project_json(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise _error("json_parse", "$", "JSON input must be text")
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except CanonicalProjectLoadError:
        raise
    except json.JSONDecodeError as exc:
        raise _error(
            "json_parse",
            f"line {exc.lineno}, column {exc.colno}",
            exc.msg,
        ) from exc
    if not isinstance(payload, dict):
        raise _error("json_parse", "$", "project root must be an object")
    return payload


def migrate_project_payload(
    project: Mapping[str, Any],
) -> tuple[dict[str, Any], ProjectMigrationReceipt]:
    source = _json_copy(project)
    version = source.get("schema_version")
    if not isinstance(version, str) or not version:
        raise _error("version_migration", "$.schema_version", "schema_version is required")
    if version != SUPPORTED_PROJECT_SCHEMA_VERSION:
        raise _error(
            "version_migration",
            "$.schema_version",
            f"unsupported EPDM project schema version: {version!r}",
        )
    return source, ProjectMigrationReceipt(
        source_version=version,
        target_version=SUPPORTED_PROJECT_SCHEMA_VERSION,
        steps=("IDENTITY_2_0_0",),
        evidence_fabricated=False,
    )


def _strip_extensions(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload.pop("extensions", None)
    return payload


def _coerce(value: Any, annotation: Any, path: str) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        none_allowed = type(None) in args
        if value is None and none_allowed:
            return None
        failures: list[str] = []
        for candidate in args:
            if candidate is type(None):
                continue
            try:
                return _coerce(value, candidate, path)
            except CanonicalProjectLoadError as exc:
                failures.append(exc.issue.message)
        raise _error("dataclass_construction", path, " | ".join(failures))

    if origin is tuple:
        if not isinstance(value, list):
            raise _error("dataclass_construction", path, "expected an array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(
                _coerce(item, args[0], f"{path}[{index}]") for index, item in enumerate(value)
            )
        if len(value) != len(args):
            raise _error(
                "dataclass_construction",
                path,
                f"expected {len(args)} array items, got {len(value)}",
            )
        return tuple(
            _coerce(item, item_type, f"{path}[{index}]")
            for index, (item, item_type) in enumerate(zip(value, args, strict=True))
        )

    if origin in (dict, Mapping):
        if not isinstance(value, dict):
            raise _error("dataclass_construction", path, "expected an object")
        key_type, value_type = args
        return MappingProxyType(
            {
                _coerce(key, key_type, f"{path}.<key>"): _coerce(item, value_type, f"{path}.{key}")
                for key, item in value.items()
            }
        )

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        try:
            return annotation(value)
        except (TypeError, ValueError) as exc:
            raise _error(
                "dataclass_construction",
                path,
                f"invalid {annotation.__name__}: {value!r}",
            ) from exc

    if isinstance(annotation, type) and is_dataclass(annotation):
        if type(value) is annotation:
            return value
        if not isinstance(value, dict):
            raise _error("dataclass_construction", path, "expected an object")
        return _construct_dataclass(annotation, value, path)

    if annotation is str:
        if not isinstance(value, str):
            raise _error("dataclass_construction", path, "expected a string")
        return value
    if annotation is bool:
        if type(value) is not bool:
            raise _error("dataclass_construction", path, "expected a boolean")
        return value
    if annotation is int:
        if type(value) is not int:
            raise _error("dataclass_construction", path, "expected an integer")
        return value
    if annotation is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _error("dataclass_construction", path, "expected a number")
        converted = float(value)
        if not math.isfinite(converted):
            raise _error("dataclass_construction", path, "expected a finite number")
        return converted
    if annotation is Any:
        return copy.deepcopy(value)

    raise _error(
        "dataclass_construction",
        path,
        f"unsupported contract annotation: {annotation!r}",
    )


def _construct_dataclass(dataclass_type: type[T], record: Mapping[str, Any], path: str) -> T:
    hints = get_type_hints(dataclass_type)
    allowed = {item.name for item in fields(dataclass_type) if item.init}
    unknown = sorted(set(record) - allowed)
    if unknown:
        raise _error(
            "dataclass_construction",
            path,
            f"fields are not represented by {dataclass_type.__name__}: {unknown}",
        )
    kwargs: dict[str, Any] = {}
    for item in fields(dataclass_type):
        if not item.init or item.name not in record:
            continue
        kwargs[item.name] = _coerce(record[item.name], hints[item.name], f"{path}.{item.name}")
    try:
        return dataclass_type(**kwargs)
    except (ContractValidationError, TypeError, ValueError) as exc:
        raise _error("dataclass_construction", path, str(exc)) from exc


def _construct_evidence(record: Mapping[str, Any], path: str) -> EvidenceRecord:
    payload = _strip_extensions(record)
    reference_fields = {
        "evidence_id",
        "source_type",
        "source_id",
        "locator",
        "dataset_id",
        "sha256",
        "notes",
    }
    allowed = reference_fields | {"status", "applicability_domain_ids"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise _error(
            "dataclass_construction",
            path,
            f"fields are not represented by EvidenceRecord: {unknown}",
        )
    reference = _construct_dataclass(
        EvidenceReference,
        {key: payload[key] for key in reference_fields if key in payload},
        f"{path}.reference",
    )
    return _construct_dataclass(
        EvidenceRecord,
        {
            "reference": reference,
            "status": payload.get("status"),
            "applicability_domain_ids": payload.get("applicability_domain_ids", []),
        },
        path,
    )


def _index_records(
    records: object,
    id_field: str,
    path: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        raise _error("indexing", path, "expected an array")
    indexed: dict[str, dict[str, Any]] = {}
    for position, record in enumerate(records):
        record_path = f"{path}[{position}]"
        if not isinstance(record, dict):
            raise _error("indexing", record_path, "expected an object")
        identifier = record.get(id_field)
        if not isinstance(identifier, str):
            raise _error("indexing", f"{record_path}.{id_field}", "expected a string ID")
        if identifier in indexed:
            raise _error(
                "indexing",
                f"{record_path}.{id_field}",
                f"duplicate identifier: {identifier}",
            )
        indexed[identifier] = record
    return indexed


def _build_registry(project: Mapping[str, Any]) -> ContractRegistry:
    registry = ContractRegistry()

    for index, record in enumerate(project["evidence_ledger"]):
        evidence = _construct_evidence(record, f"$.evidence_ledger[{index}]")
        registry.evidence.register(evidence.reference.evidence_id, evidence)

    sections: tuple[tuple[str, type[Any], Any, str], ...] = (
        (
            "applicability_domains",
            ApplicabilityDomain,
            registry.applicability_domains,
            "applicability_domain_id",
        ),
        ("catalyst_passports", CatalystPassport, registry.catalysts, "catalyst_id"),
        ("diene_passports", DienePassport, registry.dienes, "diene_id"),
        (
            "thermo_passports",
            ThermoPassport,
            registry.thermo_passports,
            "thermo_passport_id",
        ),
        ("datasets", KineticDataset, registry.datasets, "dataset_id"),
    )
    for section, contract_type, target_registry, id_field in sections:
        for index, record in enumerate(project[section]):
            item = _construct_dataclass(
                contract_type,
                _strip_extensions(record),
                f"$.{section}[{index}]",
            )
            target_registry.register(getattr(item, id_field), item)

    global_rate_law_ids: set[str] = set()
    global_parameter_ids: set[str] = set()
    for set_index, parameter_set in enumerate(project["kinetic_parameter_sets"]):
        set_path = f"$.kinetic_parameter_sets[{set_index}]"
        if not isinstance(parameter_set, dict):
            raise _error("dataclass_construction", set_path, "expected an object")
        local_rate_law_ids: set[str] = set()
        for index, record in enumerate(parameter_set.get("rate_laws", [])):
            item = _construct_dataclass(
                RateLawDefinition,
                _strip_extensions(record),
                f"{set_path}.rate_laws[{index}]",
            )
            if item.rate_law_id in global_rate_law_ids:
                raise _error(
                    "indexing",
                    f"{set_path}.rate_laws[{index}].rate_law_id",
                    f"duplicate global rate-law ID: {item.rate_law_id}",
                )
            global_rate_law_ids.add(item.rate_law_id)
            local_rate_law_ids.add(item.rate_law_id)
            registry.rate_laws.register(item.rate_law_id, item)
        for index, record in enumerate(parameter_set.get("parameters", [])):
            item = _construct_dataclass(
                KineticParameter,
                _strip_extensions(record),
                f"{set_path}.parameters[{index}]",
            )
            if item.parameter_id in global_parameter_ids:
                raise _error(
                    "indexing",
                    f"{set_path}.parameters[{index}].parameter_id",
                    f"duplicate global parameter ID: {item.parameter_id}",
                )
            if item.rate_law_id not in local_rate_law_ids:
                raise _error(
                    "reference_validation",
                    f"{set_path}.parameters[{index}].rate_law_id",
                    f"rate law {item.rate_law_id!r} is outside its parameter set",
                )
            global_parameter_ids.add(item.parameter_id)
            registry.kinetic_parameters.register(item.parameter_id, item)

    try:
        registry.validate_references()
    except (CrossRegistryReferenceError, RegistryError) as exc:
        raise _error("reference_validation", "$", str(exc)) from exc
    return registry


def _registry_snapshot(registry: ContractRegistry) -> ContractRegistrySnapshot:
    manifest = _thaw(registry.manifest())
    content_sha256 = manifest["content_sha256"]
    return ContractRegistrySnapshot(
        evidence=registry.evidence.as_mapping(),
        applicability_domains=registry.applicability_domains.as_mapping(),
        catalysts=registry.catalysts.as_mapping(),
        dienes=registry.dienes.as_mapping(),
        rate_laws=registry.rate_laws.as_mapping(),
        kinetic_parameters=registry.kinetic_parameters.as_mapping(),
        thermo_passports=registry.thermo_passports.as_mapping(),
        datasets=registry.datasets.as_mapping(),
        manifest=_freeze(manifest),
        content_sha256=content_sha256,
    )


def _typed_mapping(
    records: object,
    id_field: str,
    contract_type: type[T],
    path: str,
) -> Mapping[str, T]:
    indexed = _index_records(records, id_field, path)
    result = {
        identifier: _construct_dataclass(
            contract_type,
            _strip_extensions(record),
            f"{path}[{identifier}]",
        )
        for identifier, record in indexed.items()
    }
    return MappingProxyType({identifier: result[identifier] for identifier in sorted(result)})


def _construct_qualification(project: Mapping[str, Any]) -> ModelQualification:
    qualification = project.get("qualification")
    if not isinstance(qualification, dict):
        raise _error("dataclass_construction", "$.qualification", "expected an object")
    core_fields = {
        "software_status",
        "thermodynamic_status",
        "kinetic_calibration_status",
        "independent_validation_status",
        "engineering_use_status",
        "gate_results",
        "model_generation",
    }
    payload = {key: qualification[key] for key in core_fields if key in qualification}
    return _construct_dataclass(ModelQualification, payload, "$.qualification")


def _build_snapshot(
    project: dict[str, Any],
    migration: ProjectMigrationReceipt,
) -> CanonicalProjectSnapshot:
    registry = _build_registry(project)
    registry_snapshot = _registry_snapshot(registry)
    state_definitions = _typed_mapping(
        project["state_definitions"],
        "state_definition_id",
        StateDefinition,
        "$.state_definitions",
    )
    calibration_plans = _typed_mapping(
        project["calibration_plans"],
        "calibration_plan_id",
        CalibrationPlan,
        "$.calibration_plans",
    )
    qualification = _construct_qualification(project)

    source_sha256 = _sha256(project)
    typed_auxiliary = {
        "state_definitions": _thaw(state_definitions),
        "calibration_plans": _thaw(calibration_plans),
        "qualification": _thaw(qualification),
    }
    manifest: dict[str, Any] = {
        "schema": CANONICAL_PROJECT_SCHEMA,
        "loader_version": LOADER_VERSION,
        "project_id": project["project_id"],
        "schema_version": project["schema_version"],
        "migration": _thaw(migration),
        "source_sha256": source_sha256,
        "registry_content_sha256": registry_snapshot.content_sha256,
        "registry_manifest": _thaw(registry_snapshot.manifest),
        "typed_auxiliary_sha256": _sha256(typed_auxiliary),
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "customer_qualification": "NOT_EVALUATED",
        "industrial_performance_guarantee": "NOT_EVALUATED",
    }
    publication_sha256 = _sha256(manifest)
    manifest["publication_sha256"] = publication_sha256

    return CanonicalProjectSnapshot(
        project_id=project["project_id"],
        schema_version=project["schema_version"],
        loader_version=LOADER_VERSION,
        migration=migration,
        source_sha256=source_sha256,
        publication_sha256=publication_sha256,
        registry=registry_snapshot,
        state_definitions=state_definitions,
        calibration_plans=calibration_plans,
        qualification=qualification,
        canonical_project=_freeze(project),
        manifest=_freeze(manifest),
    )


def load_canonical_project(
    project: object,
    *,
    schema_dir: Path | None = None,
) -> CanonicalProjectSnapshot:
    """Build and atomically publish an immutable V2 contract snapshot.

    The function has no externally visible intermediate state. It either returns
    a complete snapshot or raises :class:`CanonicalProjectLoadError`.
    """

    candidate, migration = migrate_project_payload(
        project if isinstance(project, Mapping) else _json_copy(project)
    )
    try:
        structural = _validation.validate_schema_instance(
            candidate,
            "epdm-project-v2.schema.json",
            schema_dir=schema_dir,
        )
    except Exception as exc:
        raise _error(
            "schema_validation",
            "$",
            f"schema registry could not be loaded: {type(exc).__name__}",
        ) from exc
    if structural:
        issue = structural[0]
        raise _error("schema_validation", issue.path, issue.message)
    try:
        return _build_snapshot(candidate, migration)
    except CanonicalProjectLoadError:
        raise
    except RegistryError as exc:
        raise _error("registry_publication", "$", str(exc)) from exc
    except Exception as exc:  # defensive public boundary
        raise _error(
            "internal",
            "$",
            f"unexpected canonical load failure: {type(exc).__name__}",
        ) from exc


def load_canonical_project_json(
    text: str,
    *,
    schema_dir: Path | None = None,
) -> CanonicalProjectSnapshot:
    return load_canonical_project(parse_project_json(text), schema_dir=schema_dir)


def load_canonical_project_file(
    path: Path,
    *,
    schema_dir: Path | None = None,
) -> CanonicalProjectSnapshot:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _error("file_read", str(path), str(exc)) from exc
    return load_canonical_project_json(text, schema_dir=schema_dir)
