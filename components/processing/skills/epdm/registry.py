from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from threading import RLock
from types import MappingProxyType
from typing import Any, Generic, TypeVar, cast

from .contracts import (
    ApplicabilityDomain,
    CatalystPassport,
    DienePassport,
    EvidenceRecord,
    KineticDataset,
    KineticParameter,
    RateLawDefinition,
    ThermoPassport,
    ValidationCriterion,
)

T = TypeVar("T")

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_MANIFEST_SCHEMA = "TSAO-EPDM-REGISTRY-MANIFEST-1"


class RegistryError(ValueError):
    """Base registry contract failure."""


class RegistryIdentifierError(RegistryError):
    pass


class DuplicateRegistryIdError(RegistryError):
    pass


class UnresolvedRegistryIdError(RegistryError):
    pass


class RegistryItemTypeError(RegistryError):
    pass


class CrossRegistryReferenceError(RegistryError):
    pass


@dataclass(frozen=True, slots=True)
class RegistryReceipt:
    registry_label: str
    identifier: str
    item_type: str
    item_sha256: str
    registry_version: int


@dataclass(frozen=True, slots=True)
class _StoredEntry(Generic[T]):
    item: T
    sha256: str


def _qualified_type(value: type[object]) -> str:
    return f"{value.__module__}.{value.__qualname__}"


def _require_identifier(identifier: object, label: str) -> str:
    if not isinstance(identifier, str) or not _ID_PATTERN.fullmatch(identifier):
        raise RegistryIdentifierError(f"{label} must be a non-empty stable identifier")
    return identifier


def _snapshot(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        kwargs = {
            item.name: _snapshot(getattr(value, item.name)) for item in fields(value) if item.init
        }
        try:
            return type(value)(**kwargs)
        except (TypeError, ValueError) as exc:
            raise RegistryItemTypeError(
                f"cannot snapshot {_qualified_type(type(value))}: {exc}"
            ) from exc
    if isinstance(value, Enum):
        return value
    if isinstance(value, Mapping):
        return {_snapshot(key): _snapshot(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_snapshot(item) for item in value)
    if isinstance(value, list):
        return [_snapshot(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RegistryItemTypeError("registry snapshots require finite numeric values")
        return value
    raise RegistryItemTypeError(
        f"registry snapshots do not support mutable or opaque type {_qualified_type(type(value))}"
    )


def _canonical_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__type__": _qualified_type(type(value)),
            "fields": {
                item.name: _canonical_value(getattr(value, item.name)) for item in fields(value)
            },
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        canonical: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise RegistryItemTypeError("registry manifest mapping keys must be strings")
            canonical[key] = _canonical_value(value[key])
        return canonical
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RegistryItemTypeError("registry manifests require finite numeric values")
        return value
    raise RegistryItemTypeError(
        f"registry manifests do not support type {_qualified_type(type(value))}"
    )


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _read_identifier_path(item: object, path: str) -> object:
    value: object = item
    for part in path.split("."):
        try:
            value = getattr(value, part)
        except AttributeError as exc:
            raise RegistryItemTypeError(
                f"registered object lacks identifier path {path!r}"
            ) from exc
    return value


class IndexedRegistry(Generic[T]):
    """Thread-safe, snapshot-isolated, append-only registry.

    Registration is atomic. Duplicate IDs and type changes are rejected; there is
    deliberately no implicit replacement API.
    """

    __slots__ = (
        "_identifier_path",
        "_item_type",
        "_items",
        "_label",
        "_lock",
        "_version",
    )

    def __init__(
        self,
        label: str,
        item_type: type[T] | None = None,
        identifier_path: str | None = None,
        *,
        lock: RLock | None = None,
    ) -> None:
        self._label = _require_identifier(label, "registry label")
        if item_type is not None and (
            not isinstance(item_type, type) or not is_dataclass(item_type)
        ):
            raise RegistryItemTypeError("item_type must be a dataclass type")
        if identifier_path is not None and not identifier_path.strip():
            raise RegistryIdentifierError("identifier_path must not be empty")
        self._item_type = item_type
        self._identifier_path = identifier_path
        self._items: dict[str, _StoredEntry[T]] = {}
        self._lock = lock if lock is not None else RLock()
        self._version = 0

    @property
    def label(self) -> str:
        return self._label

    @property
    def item_type(self) -> type[T] | None:
        with self._lock:
            return self._item_type

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def register(self, identifier: str, item: T) -> RegistryReceipt:
        normalized_id = _require_identifier(identifier, f"{self.label} ID")
        if not is_dataclass(item) or isinstance(item, type):
            raise RegistryItemTypeError(
                f"{self.label} registry requires a dataclass object, "
                f"got {_qualified_type(type(item))}"
            )

        candidate_type = type(item)
        with self._lock:
            expected_type = self._item_type
        if expected_type is not None and candidate_type is not expected_type:
            raise RegistryItemTypeError(
                f"{self.label} registry requires {_qualified_type(expected_type)}, "
                f"got {_qualified_type(candidate_type)}"
            )

        stored = cast(T, _snapshot(item))
        if self._identifier_path is not None:
            embedded = _read_identifier_path(stored, self._identifier_path)
            if embedded != normalized_id:
                raise RegistryIdentifierError(
                    f"{self.label} registry key {normalized_id!r} does not match "
                    f"object identifier {embedded!r}"
                )
        item_payload = {
            "identifier": normalized_id,
            "item_type": _qualified_type(candidate_type),
            "item": _canonical_value(stored),
        }
        item_sha256 = _digest(item_payload)

        with self._lock:
            if self._item_type is None:
                self._item_type = candidate_type
            elif candidate_type is not self._item_type:
                raise RegistryItemTypeError(
                    f"{self.label} registry requires {_qualified_type(self._item_type)}, "
                    f"got {_qualified_type(candidate_type)}"
                )
            existing = self._items.get(normalized_id)
            if existing is not None:
                raise DuplicateRegistryIdError(
                    f"duplicate {self.label} ID: {normalized_id}; "
                    f"existing_sha256={existing.sha256}; attempted_sha256={item_sha256}"
                )
            self._items[normalized_id] = _StoredEntry(stored, item_sha256)
            self._version += 1
            version = self._version

        return RegistryReceipt(
            registry_label=self.label,
            identifier=normalized_id,
            item_type=_qualified_type(candidate_type),
            item_sha256=item_sha256,
            registry_version=version,
        )

    def require(self, identifier: str) -> T:
        normalized_id = _require_identifier(identifier, f"{self.label} ID")
        with self._lock:
            entry = self._items.get(normalized_id)
        if entry is None:
            raise UnresolvedRegistryIdError(f"unresolved {self.label} ID: {normalized_id}")
        return cast(T, _snapshot(entry.item))

    def get(self, identifier: str) -> T:
        """Fail-closed lookup retained under the historical method name."""
        return self.require(identifier)

    def find(self, identifier: str) -> T | None:
        normalized_id = _require_identifier(identifier, f"{self.label} ID")
        with self._lock:
            entry = self._items.get(normalized_id)
        return None if entry is None else cast(T, _snapshot(entry.item))

    def contains(self, identifier: str) -> bool:
        normalized_id = _require_identifier(identifier, f"{self.label} ID")
        with self._lock:
            return normalized_id in self._items

    def identifiers(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._items))

    def as_mapping(self) -> Mapping[str, T]:
        with self._lock:
            entries = tuple(
                (identifier, self._items[identifier]) for identifier in sorted(self._items)
            )
        return MappingProxyType(
            {identifier: cast(T, _snapshot(entry.item)) for identifier, entry in entries}
        )

    def manifest(self) -> Mapping[str, Any]:
        with self._lock:
            entries = tuple(
                (identifier, self._items[identifier]) for identifier in sorted(self._items)
            )
            item_type = self._item_type
            version = self._version
        payload: dict[str, Any] = {
            "schema": _MANIFEST_SCHEMA,
            "registry_label": self.label,
            "registry_version": version,
            "item_type": None if item_type is None else _qualified_type(item_type),
            "entry_count": len(entries),
            "entries": [
                {
                    "identifier": identifier,
                    "sha256": entry.sha256,
                    "item": _canonical_value(entry.item),
                }
                for identifier, entry in entries
            ],
        }
        payload["content_sha256"] = _digest(payload)
        return MappingProxyType(payload)

    def to_json(self) -> str:
        return _canonical_json(dict(self.manifest()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


_REGISTRY_ORDER = (
    "applicability_domains",
    "catalysts",
    "criteria",
    "datasets",
    "dienes",
    "evidence",
    "kinetic_parameters",
    "rate_laws",
    "thermo_passports",
)


class ContractRegistry:
    """Coordinated EPDM contract registries with cross-reference validation."""

    __slots__ = (*_REGISTRY_ORDER, "_lock")

    def __init__(self) -> None:
        self._lock = RLock()
        self.evidence = IndexedRegistry(
            "evidence", EvidenceRecord, "reference.evidence_id", lock=self._lock
        )
        self.applicability_domains = IndexedRegistry(
            "applicability-domain",
            ApplicabilityDomain,
            "applicability_domain_id",
            lock=self._lock,
        )
        self.catalysts = IndexedRegistry(
            "catalyst", CatalystPassport, "catalyst_id", lock=self._lock
        )
        self.dienes = IndexedRegistry("diene", DienePassport, "diene_id", lock=self._lock)
        self.rate_laws = IndexedRegistry(
            "rate-law", RateLawDefinition, "rate_law_id", lock=self._lock
        )
        self.kinetic_parameters = IndexedRegistry(
            "kinetic-parameter", KineticParameter, "parameter_id", lock=self._lock
        )
        self.thermo_passports = IndexedRegistry(
            "thermo-passport", ThermoPassport, "thermo_passport_id", lock=self._lock
        )
        self.datasets = IndexedRegistry("dataset", KineticDataset, "dataset_id", lock=self._lock)
        self.criteria = IndexedRegistry(
            "criterion", ValidationCriterion, "criterion_id", lock=self._lock
        )

    def _registries(self) -> Mapping[str, IndexedRegistry[Any]]:
        return MappingProxyType(
            {name: cast(IndexedRegistry[Any], getattr(self, name)) for name in _REGISTRY_ORDER}
        )

    def validate_references(self) -> None:
        with self._lock:
            snapshots = {
                name: registry.as_mapping() for name, registry in self._registries().items()
            }

        issues: list[str] = []

        def require(
            source_registry: str,
            source_id: str,
            field: str,
            target_registry: str,
            target_id: str | None,
        ) -> None:
            if target_id is None or target_id not in snapshots[target_registry]:
                issues.append(
                    f"{source_registry}[{source_id}].{field} -> "
                    f"{target_registry}[{target_id}] is unresolved"
                )

        for evidence_id, record in snapshots["evidence"].items():
            for domain_id in record.applicability_domain_ids:
                require(
                    "evidence",
                    evidence_id,
                    "applicability_domain_ids",
                    "applicability_domains",
                    domain_id,
                )
            if record.reference.dataset_id is not None:
                require(
                    "evidence",
                    evidence_id,
                    "reference.dataset_id",
                    "datasets",
                    record.reference.dataset_id,
                )

        for domain_id, domain in snapshots["applicability_domains"].items():
            for catalyst_id in domain.catalyst_ids:
                require(
                    "applicability_domains",
                    domain_id,
                    "catalyst_ids",
                    "catalysts",
                    catalyst_id,
                )
            for diene_id in domain.diene_ids:
                require("applicability_domains", domain_id, "diene_ids", "dienes", diene_id)

        for catalyst_id, catalyst in snapshots["catalysts"].items():
            require(
                "catalysts",
                catalyst_id,
                "applicability_domain_id",
                "applicability_domains",
                catalyst.applicability_domain_id,
            )
            for evidence_id in catalyst.evidence_ids:
                require("catalysts", catalyst_id, "evidence_ids", "evidence", evidence_id)

        for diene_id, diene in snapshots["dienes"].items():
            require(
                "dienes",
                diene_id,
                "applicability_domain_id",
                "applicability_domains",
                diene.applicability_domain_id,
            )
            for evidence_id in diene.evidence_ids:
                require("dienes", diene_id, "evidence_ids", "evidence", evidence_id)

        for rate_law_id, rate_law in snapshots["rate_laws"].items():
            for parameter_id, role in rate_law.parameter_roles.items():
                require(
                    "rate_laws",
                    rate_law_id,
                    "parameter_roles",
                    "kinetic_parameters",
                    parameter_id,
                )
                parameter = snapshots["kinetic_parameters"].get(parameter_id)
                if parameter is not None and (
                    parameter.rate_law_id != rate_law_id or parameter.parameter_role != role
                ):
                    issues.append(
                        f"rate_laws[{rate_law_id}].parameter_roles[{parameter_id}] "
                        "disagrees with kinetic parameter binding"
                    )

        for parameter_id, parameter in snapshots["kinetic_parameters"].items():
            require(
                "kinetic_parameters",
                parameter_id,
                "rate_law_id",
                "rate_laws",
                parameter.rate_law_id,
            )
            require(
                "kinetic_parameters",
                parameter_id,
                "evidence_id",
                "evidence",
                parameter.evidence_id,
            )
            require(
                "kinetic_parameters",
                parameter_id,
                "applicability_domain_id",
                "applicability_domains",
                parameter.applicability_domain_id,
            )
            rate_law = snapshots["rate_laws"].get(parameter.rate_law_id)
            if (
                rate_law is not None
                and rate_law.parameter_roles.get(parameter_id) != parameter.parameter_role
            ):
                issues.append(
                    f"kinetic_parameters[{parameter_id}].parameter_role is not declared "
                    f"by rate_laws[{parameter.rate_law_id}]"
                )

        for thermo_id, thermo in snapshots["thermo_passports"].items():
            for evidence_id in thermo.evidence_ids:
                require("thermo_passports", thermo_id, "evidence_ids", "evidence", evidence_id)
            for dataset_id in thermo.validation_dataset_ids:
                require(
                    "thermo_passports",
                    thermo_id,
                    "validation_dataset_ids",
                    "datasets",
                    dataset_id,
                )

        for dataset_id, dataset in snapshots["datasets"].items():
            require("datasets", dataset_id, "catalyst_id", "catalysts", dataset.catalyst_id)
            require("datasets", dataset_id, "diene_id", "dienes", dataset.diene_id)
            for evidence_id in dataset.evidence_ids:
                require("datasets", dataset_id, "evidence_ids", "evidence", evidence_id)
            for target in dataset.targets:
                require(
                    "datasets",
                    dataset_id,
                    "targets.evidence_id",
                    "evidence",
                    target.evidence_id,
                )

        for criterion_id, criterion in snapshots["criteria"].items():
            for dataset_id in criterion.dataset_ids:
                require("criteria", criterion_id, "dataset_ids", "datasets", dataset_id)

        if issues:
            raise CrossRegistryReferenceError(
                "cross-registry reference validation failed: " + "; ".join(sorted(set(issues)))
            )

    def manifest(self) -> Mapping[str, Any]:
        with self._lock:
            registries = {
                name: dict(registry.manifest()) for name, registry in self._registries().items()
            }
        payload: dict[str, Any] = {
            "schema": _MANIFEST_SCHEMA,
            "registry_set": "EPDM_PHASE_A1_CONTRACTS",
            "registries": registries,
        }
        payload["content_sha256"] = _digest(payload)
        return MappingProxyType(payload)

    def to_json(self) -> str:
        return _canonical_json(dict(self.manifest()))


def registry_from_pairs(
    label: str,
    pairs: Iterable[tuple[str, T]],
    *,
    item_type: type[T] | None = None,
    identifier_path: str | None = None,
) -> IndexedRegistry[T]:
    registry = IndexedRegistry(label, item_type, identifier_path)
    for identifier, item in pairs:
        registry.register(identifier, item)
    return registry
