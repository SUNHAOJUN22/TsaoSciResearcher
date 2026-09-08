from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .contracts import (
    ContractValidationError,
    EnergyFormulation,
    StateBasis,
    validate_si_unit,
)

_DEFAULT_CATALOG_PATH = Path(__file__).with_name("data") / "state_variable_catalog_v2.json"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_DEFAULT_TERMINALS = ("E", "P", "D")
_SITE_INVENTORY_BASES = {
    "N_SITE_POTENTIAL",
    "N_SITE_VACANT",
    "N_SITE_INHIBITED_H2",
    "N_SITE_POISONED",
    "N_SITE_DEAD",
    "LAMBDA0",
}


@dataclass(frozen=True, slots=True)
class GeneratedStateVariable:
    state_id: str
    base_variable_id: str
    index: int
    unit: str
    basis: StateBasis
    model_level: int
    site_family_id: str | None
    terminal_id: str | None
    nonnegative: bool
    conserved_inventory_id: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "state_id": self.state_id,
            "base_variable_id": self.base_variable_id,
            "index": self.index,
            "unit": self.unit,
            "basis": self.basis.value,
            "model_level": self.model_level,
            "site_family_id": self.site_family_id,
            "terminal_id": self.terminal_id,
            "nonnegative": self.nonnegative,
            "conserved_inventory_id": self.conserved_inventory_id,
        }


@dataclass(frozen=True, slots=True)
class GeneratedStateDefinition:
    generated_state_definition_id: str
    source_state_definition_id: str
    source_catalog_schema: str
    version: str
    model_level: int
    basis: StateBasis
    energy_formulation: EnergyFormulation
    site_family_ids: tuple[str, ...]
    terminal_ids: tuple[str, ...]
    variables: tuple[GeneratedStateVariable, ...]
    _index_by_id: Mapping[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        index_by_id = {variable.state_id: variable.index for variable in self.variables}
        if len(index_by_id) != len(self.variables):
            raise ContractValidationError("generated state IDs must be unique")
        if sorted(index_by_id.values()) != list(range(len(self.variables))):
            raise ContractValidationError("generated state indices must be contiguous")
        object.__setattr__(self, "_index_by_id", MappingProxyType(index_by_id))

    @property
    def size(self) -> int:
        return len(self.variables)

    @property
    def state_ids(self) -> tuple[str, ...]:
        return tuple(variable.state_id for variable in self.variables)

    @property
    def digest_sha256(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def index_of(self, state_id: str) -> int:
        try:
            return self._index_by_id[state_id]
        except KeyError as exc:
            raise KeyError(f"unknown generated state ID: {state_id}") from exc

    def zeros(self) -> tuple[float, ...]:
        return (0.0,) * self.size

    def validate_vector(
        self,
        values: Sequence[float],
        *,
        nonnegative_tolerance: float = 0.0,
    ) -> None:
        if len(values) != self.size:
            raise ContractValidationError(
                f"state vector length {len(values)} does not match definition size {self.size}"
            )
        if nonnegative_tolerance < 0:
            raise ContractValidationError("nonnegative_tolerance must be non-negative")
        for variable, value in zip(self.variables, values, strict=True):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ContractValidationError(f"state {variable.state_id} must be numeric")
            if not math.isfinite(float(value)):
                raise ContractValidationError(f"state {variable.state_id} must be finite")
            if variable.nonnegative and float(value) < -nonnegative_tolerance:
                raise ContractValidationError(f"state {variable.state_id} must be non-negative")

    def pack(
        self, values: Mapping[str, float], *, fill_missing: float | None = None
    ) -> tuple[float, ...]:
        unknown = sorted(set(values) - set(self._index_by_id))
        if unknown:
            raise ContractValidationError(f"unknown state IDs: {unknown}")
        if fill_missing is not None and (
            isinstance(fill_missing, bool) or not math.isfinite(fill_missing)
        ):
            raise ContractValidationError("fill_missing must be finite numeric")
        selected = [values.get(state_id, fill_missing) for state_id in self.state_ids]
        if fill_missing is None:
            missing = [state_id for state_id in self.state_ids if state_id not in values]
            if missing:
                raise ContractValidationError(f"missing state IDs: {missing}")
        if any(isinstance(value, bool) for value in selected):
            raise ContractValidationError("state values must be numeric and must not be boolean")
        try:
            vector = tuple(float(value) for value in selected)
        except (TypeError, ValueError) as exc:
            raise ContractValidationError("state values must be numeric") from exc
        self.validate_vector(vector)
        return vector

    def unpack(self, values: Sequence[float]) -> Mapping[str, float]:
        self.validate_vector(values)
        return MappingProxyType(
            {state_id: float(value) for state_id, value in zip(self.state_ids, values, strict=True)}
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "TSAO-EPDM-V2-GENERATED-STATE-DEFINITION-1",
            "generated_state_definition_id": self.generated_state_definition_id,
            "source_state_definition_id": self.source_state_definition_id,
            "source_catalog_schema": self.source_catalog_schema,
            "version": self.version,
            "model_level": self.model_level,
            "basis": self.basis.value,
            "energy_formulation": self.energy_formulation.value,
            "site_family_ids": list(self.site_family_ids),
            "terminal_ids": list(self.terminal_ids),
            "variables": [variable.as_dict() for variable in self.variables],
            "digest_sha256": self.digest_sha256_without_self,
            "numerical_execution": "NOT_IMPLEMENTED_PHASE_A2",
        }

    @property
    def digest_sha256_without_self(self) -> str:
        payload = {
            "schema": "TSAO-EPDM-V2-GENERATED-STATE-DEFINITION-1",
            "generated_state_definition_id": self.generated_state_definition_id,
            "source_state_definition_id": self.source_state_definition_id,
            "source_catalog_schema": self.source_catalog_schema,
            "version": self.version,
            "model_level": self.model_level,
            "basis": self.basis.value,
            "energy_formulation": self.energy_formulation.value,
            "site_family_ids": list(self.site_family_ids),
            "terminal_ids": list(self.terminal_ids),
            "variables": [variable.as_dict() for variable in self.variables],
            "numerical_execution": "NOT_IMPLEMENTED_PHASE_A2",
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def load_state_catalog(path: Path | None = None) -> dict[str, Any]:
    source = path or _DEFAULT_CATALOG_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != "TSAO-EPDM-V2-STATE-CATALOG-1":
        raise ContractValidationError("unsupported state catalog schema")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ContractValidationError("state catalog items must be a non-empty array")
    orders: list[int] = []
    variable_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            raise ContractValidationError("state catalog entries must be objects")
        order = item.get("order")
        variable_id = item.get("variable_id")
        if not isinstance(order, int) or order < 0:
            raise ContractValidationError("state catalog order must be non-negative integer")
        if not isinstance(variable_id, str) or not _IDENTIFIER.fullmatch(variable_id):
            raise ContractValidationError("state catalog variable_id is invalid")
        unit = item.get("unit")
        if not isinstance(unit, str):
            raise ContractValidationError("state catalog unit is required")
        validate_si_unit(unit)
        orders.append(order)
        variable_ids.append(variable_id)
    if len(orders) != len(set(orders)):
        raise ContractValidationError("state catalog orders must be unique")
    if len(variable_ids) != len(set(variable_ids)):
        raise ContractValidationError("state catalog variable IDs must be unique")
    return payload


def _validate_identifiers(values: tuple[str, ...], label: str) -> None:
    if not values:
        raise ContractValidationError(f"{label} must not be empty")
    if len(values) != len(set(values)):
        raise ContractValidationError(f"{label} must be unique")
    for value in values:
        if not _IDENTIFIER.fullmatch(value):
            raise ContractValidationError(f"invalid {label} identifier: {value}")


def _expanded_state_id(base: str, site: str | None, terminal: str | None) -> str:
    parts = [base]
    if site is not None:
        parts.append(site)
    if terminal is not None:
        parts.append(terminal)
    return ":".join(parts)


def generate_state_definition(
    *,
    source_state_definition_id: str,
    model_level: int,
    site_family_ids: Sequence[str],
    terminal_ids: Sequence[str] = _DEFAULT_TERMINALS,
    basis: StateBasis = StateBasis.EXTENSIVE_REACTOR_AMOUNT,
    energy_formulation: EnergyFormulation = EnergyFormulation.ISOTHERMAL,
    catalog: Mapping[str, Any] | None = None,
) -> GeneratedStateDefinition:
    if not _IDENTIFIER.fullmatch(source_state_definition_id):
        raise ContractValidationError("source_state_definition_id is invalid")
    if model_level not in {1, 2, 3}:
        raise ContractValidationError("model_level must be 1, 2, or 3")
    sites = tuple(site_family_ids)
    terminals = tuple(terminal_ids)
    _validate_identifiers(sites, "site_family_ids")
    _validate_identifiers(terminals, "terminal_ids")
    if set(terminals) - set(_DEFAULT_TERMINALS):
        raise ContractValidationError("terminal_ids must be a subset of E, P, and D")

    payload = dict(catalog) if catalog is not None else load_state_catalog()
    schema = payload.get("schema")
    if schema != "TSAO-EPDM-V2-STATE-CATALOG-1":
        raise ContractValidationError("unsupported state catalog schema")
    items = payload.get("items")
    if not isinstance(items, list):
        raise ContractValidationError("state catalog items must be an array")

    variables: list[GeneratedStateVariable] = []
    for item in sorted(items, key=lambda entry: entry["order"]):
        minimum = item.get("level_minimum")
        if not isinstance(minimum, int) or minimum not in {1, 2, 3}:
            raise ContractValidationError("state catalog level_minimum is invalid")
        if minimum > model_level:
            continue
        base = str(item["variable_id"])
        if base == "H_TOTAL" and energy_formulation == EnergyFormulation.ISOTHERMAL:
            continue
        item_basis = StateBasis(str(item["basis"]))
        if item_basis != basis:
            raise ContractValidationError("mixed state basis is prohibited")
        unit = str(item["unit"])
        validate_si_unit(unit)
        site_values: tuple[str | None, ...] = sites if item.get("site_family_indexed") else (None,)
        terminal_values: tuple[str | None, ...] = (
            terminals if item.get("terminal_indexed") else (None,)
        )
        for site in site_values:
            for terminal in terminal_values:
                state_id = _expanded_state_id(base, site, terminal)
                inventory = None
                if site is not None and base in _SITE_INVENTORY_BASES:
                    inventory = f"SITE_TOTAL:{site}"
                variables.append(
                    GeneratedStateVariable(
                        state_id=state_id,
                        base_variable_id=base,
                        index=len(variables),
                        unit=unit,
                        basis=basis,
                        model_level=minimum,
                        site_family_id=site,
                        terminal_id=terminal,
                        nonnegative=base != "H_TOTAL",
                        conserved_inventory_id=inventory,
                    )
                )

    generated_id = f"{source_state_definition_id}:L{model_level}:GENERATED"
    return GeneratedStateDefinition(
        generated_state_definition_id=generated_id,
        source_state_definition_id=source_state_definition_id,
        source_catalog_schema=str(schema),
        version="2.1.0",
        model_level=model_level,
        basis=basis,
        energy_formulation=energy_formulation,
        site_family_ids=sites,
        terminal_ids=terminals,
        variables=tuple(variables),
    )
