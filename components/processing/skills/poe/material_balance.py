"""Dimensioned, component-wise material-balance validation.

The contract is intentionally strict. A material balance is complete only when
all required components close on one declared basis after unit conversion.
Unknown values are never replaced by physical zero, and cross-component
cancellation cannot turn a failed component balance into PASS.
"""

from __future__ import annotations

import json
import math
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "tsao.material-balance.v2"
_ALLOWED_BASES = frozenset({"mass", "molar"})
_ALLOWED_DESTINATIONS = frozenset({"EXTERNAL", "EMISSION", "LOSS"})
_CANONICAL_UNIT = {"mass": "kg/s", "molar": "mol/s"}
_COMPOSITION_BASIS = {"mass": "mass_fraction", "molar": "mole_fraction"}

_MASS_FLOW_FACTORS = {
    "kg/s": 1.0,
    "kg/min": 1.0 / 60.0,
    "kg/h": 1.0 / 3600.0,
    "g/s": 1.0e-3,
    "g/min": 1.0e-3 / 60.0,
    "g/h": 1.0e-3 / 3600.0,
    "t/s": 1.0e3,
    "t/min": 1.0e3 / 60.0,
    "t/h": 1.0e3 / 3600.0,
}
_MOLAR_FLOW_FACTORS = {
    "mol/s": 1.0,
    "mol/min": 1.0 / 60.0,
    "mol/h": 1.0 / 3600.0,
    "kmol/s": 1.0e3,
    "kmol/min": 1.0e3 / 60.0,
    "kmol/h": 1.0e3 / 3600.0,
}


class MaterialBalanceContractError(ValueError):
    """Raised internally when the quantity contract is invalid."""


@dataclass(frozen=True, slots=True)
class ComponentBalance:
    component: str
    basis: str
    canonical_unit: str
    incoming: float
    outgoing: float
    generation: float
    consumption: float
    accumulation: float
    residual: float
    absolute_residual: float
    absolute_tolerance: float
    relative_tolerance: float
    reference_scale: float
    allowed_residual: float
    component_pass: bool


@dataclass(frozen=True, slots=True)
class MaterialBalanceResult:
    schema_version: str
    status: str
    passed: bool
    basis: str | None
    canonical_unit: str | None
    errors: tuple[str, ...]
    reason_codes: tuple[str, ...]
    failed_components: tuple[str, ...]
    components: tuple[dict[str, Any], ...]
    total: dict[str, Any] | None


def _normalize_unit(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = normalized.replace("−", "-").replace("·", "*").replace("⋅", "*")
    normalized = normalized.replace("hours", "h").replace("hour", "h")
    normalized = normalized.replace("hrs", "h").replace("hr", "h")
    normalized = normalized.replace("minutes", "min").replace("minute", "min")
    normalized = normalized.replace("seconds", "s").replace("second", "s")
    normalized = "".join(normalized.split())
    normalized = normalized.replace("/sec", "/s").replace("/min.", "/min")
    return normalized


def _finite_real(value: object, label: str, *, allow_string: bool = False) -> float:
    if isinstance(value, bool):
        raise MaterialBalanceContractError(f"{label} must be a finite real number, not Bool")
    if isinstance(value, (int, float)):
        number = float(value)
    elif allow_string and isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise MaterialBalanceContractError(f"{label} must not be empty")
        try:
            number = float(stripped)
        except ValueError as exc:
            raise MaterialBalanceContractError(f"{label} must be numeric") from exc
    else:
        raise MaterialBalanceContractError(f"{label} must be a finite real number")
    if not math.isfinite(number):
        raise MaterialBalanceContractError(f"{label} must be finite")
    return number


def _positive_finite(value: object, label: str, *, allow_zero: bool = False) -> float:
    number = _finite_real(value, label)
    if number < 0 or (number == 0 and not allow_zero):
        comparison = "non-negative" if allow_zero else "positive"
        raise MaterialBalanceContractError(f"{label} must be {comparison}")
    return number


def _unit_factor(basis: str, unit: object, label: str) -> float:
    if not isinstance(unit, str) or not unit.strip():
        raise MaterialBalanceContractError(f"{label}.unit is required")
    normalized = _normalize_unit(unit)
    table = _MASS_FLOW_FACTORS if basis == "mass" else _MOLAR_FLOW_FACTORS
    if normalized not in table:
        raise MaterialBalanceContractError(
            f"{label}.unit {unit!r} is not a supported {basis} flow unit"
        )
    return table[normalized]


def _quantity_to_canonical(
    quantity: object,
    *,
    expected_basis: str,
    label: str,
    non_negative: bool = False,
    allow_string: bool = False,
) -> float:
    if not isinstance(quantity, Mapping):
        raise MaterialBalanceContractError(f"{label} must be a quantity object")
    basis = quantity.get("basis")
    if basis != expected_basis:
        raise MaterialBalanceContractError(
            f"{label}.basis must be {expected_basis!r}, found {basis!r}"
        )
    value = _finite_real(quantity.get("value"), f"{label}.value", allow_string=allow_string)
    if non_negative and value < 0:
        raise MaterialBalanceContractError(f"{label}.value must be non-negative")
    return value * _unit_factor(expected_basis, quantity.get("unit"), label)


def _normalize_components(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise MaterialBalanceContractError("components must be a non-empty string list")
    components = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if not components or len(components) != len(value) or len(set(components)) != len(components):
        raise MaterialBalanceContractError("components must be unique non-empty strings")
    return components


def _molecular_weights(case: Mapping[str, Any], components: Iterable[str]) -> dict[str, float]:
    raw = case.get("molecular_weights_g_mol")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise MaterialBalanceContractError("molecular_weights_g_mol must be an object")
    result: dict[str, float] = {}
    unknown = set(raw) - set(components)
    if unknown:
        raise MaterialBalanceContractError(
            f"molecular_weights_g_mol contains unknown components: {sorted(unknown)}"
        )
    for component, value in raw.items():
        result[str(component)] = _positive_finite(value, f"molecular_weights_g_mol.{component}")
    return result


def _validate_composition(
    stream: Mapping[str, Any], components: tuple[str, ...], stream_id: str, basis: str
) -> dict[str, float]:
    expected = _COMPOSITION_BASIS[basis]
    if stream.get("composition_basis") != expected:
        raise MaterialBalanceContractError(
            f"stream {stream_id} composition_basis must be {expected!r} for {basis} flow"
        )
    raw = stream.get("composition")
    if not isinstance(raw, Mapping) or not raw:
        raise MaterialBalanceContractError(
            f"stream {stream_id} composition must be a non-empty object"
        )
    unknown = set(raw) - set(components)
    if unknown:
        raise MaterialBalanceContractError(
            f"stream {stream_id} contains unknown components: {sorted(unknown)}"
        )
    composition: dict[str, float] = {component: 0.0 for component in components}
    for component, value in raw.items():
        number = _finite_real(value, f"stream {stream_id} composition.{component}")
        if number < 0 or number > 1:
            raise MaterialBalanceContractError(
                f"stream {stream_id} composition.{component} must be in [0, 1]"
            )
        composition[str(component)] = number
    total = math.fsum(composition.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
        raise MaterialBalanceContractError(
            f"stream {stream_id} composition must sum to one; found {total:.17g}"
        )
    return composition


def _convert_component_rate(
    value: float,
    *,
    from_basis: str,
    to_basis: str,
    component: str,
    molecular_weights: Mapping[str, float],
) -> float:
    if from_basis == to_basis:
        return value
    molecular_weight = molecular_weights.get(component)
    if molecular_weight is None:
        raise MaterialBalanceContractError(
            f"cross-basis conversion for {component} requires molecular_weights_g_mol.{component}"
        )
    if from_basis == "mass" and to_basis == "molar":
        return value * 1000.0 / molecular_weight
    if from_basis == "molar" and to_basis == "mass":
        return value * molecular_weight / 1000.0
    raise MaterialBalanceContractError(f"unsupported basis conversion: {from_basis} -> {to_basis}")


def _stream_component_rates(
    stream: Mapping[str, Any],
    *,
    components: tuple[str, ...],
    selected_basis: str,
    molecular_weights: Mapping[str, float],
    index: int,
) -> tuple[str, object, object, dict[str, float]]:
    stream_id = stream.get("stream_id")
    if not isinstance(stream_id, str) or not stream_id.strip():
        raise MaterialBalanceContractError(f"stream {index} needs a non-empty stream_id")
    stream_id = stream_id.strip()
    flow = stream.get("flow")
    if not isinstance(flow, Mapping):
        if "flow_kg_h" in stream:
            raise MaterialBalanceContractError(
                f"stream {stream_id} uses deprecated flow_kg_h; migrate to flow {{value, unit, basis}}"
            )
        raise MaterialBalanceContractError(
            f"stream {stream_id}.flow must declare value, unit, and basis"
        )
    basis = flow.get("basis")
    if basis not in _ALLOWED_BASES:
        raise MaterialBalanceContractError(f"stream {stream_id}.flow.basis must be mass or molar")
    native_rate = _quantity_to_canonical(
        flow,
        expected_basis=str(basis),
        label=f"stream {stream_id}.flow",
        non_negative=True,
    )
    composition = _validate_composition(stream, components, stream_id, str(basis))
    rates = {
        component: _convert_component_rate(
            native_rate * composition[component],
            from_basis=str(basis),
            to_basis=selected_basis,
            component=component,
            molecular_weights=molecular_weights,
        )
        for component in components
    }
    return stream_id, stream.get("from"), stream.get("to"), rates


def _reaction_rates(
    case: Mapping[str, Any],
    *,
    components: tuple[str, ...],
    selected_basis: str,
    molecular_weights: Mapping[str, float],
) -> dict[str, float]:
    totals = {component: 0.0 for component in components}
    reactions = case.get("reactions", [])
    if reactions is None:
        reactions = []
    if not isinstance(reactions, list):
        raise MaterialBalanceContractError("reactions must be a list")
    seen: set[str] = set()
    for index, reaction in enumerate(reactions, start=1):
        if not isinstance(reaction, Mapping):
            raise MaterialBalanceContractError(f"reaction {index} must be an object")
        reaction_id = reaction.get("reaction_id")
        if not isinstance(reaction_id, str) or not reaction_id.strip() or reaction_id in seen:
            raise MaterialBalanceContractError(
                f"reaction {index} needs a unique non-empty reaction_id"
            )
        seen.add(reaction_id)
        stoichiometry = reaction.get("stoichiometry")
        if not isinstance(stoichiometry, Mapping) or not stoichiometry:
            raise MaterialBalanceContractError(
                f"reaction {reaction_id}.stoichiometry must be a non-empty object"
            )
        unknown = set(stoichiometry) - set(components)
        if unknown:
            raise MaterialBalanceContractError(
                f"reaction {reaction_id} contains unknown components: {sorted(unknown)}"
            )
        coefficients: dict[str, float] = {}
        for component, raw in stoichiometry.items():
            coefficient = _finite_real(raw, f"reaction {reaction_id}.stoichiometry.{component}")
            if coefficient == 0:
                raise MaterialBalanceContractError(
                    f"reaction {reaction_id}.stoichiometry.{component} must be non-zero"
                )
            coefficients[str(component)] = coefficient
        extent = _quantity_to_canonical(
            reaction.get("extent"),
            expected_basis="molar",
            label=f"reaction {reaction_id}.extent",
            non_negative=True,
        )
        if selected_basis == "mass":
            missing = sorted(set(coefficients) - set(molecular_weights))
            if missing:
                raise MaterialBalanceContractError(
                    f"reaction {reaction_id} mass-basis verification needs molecular weights for {missing}"
                )
            molar_mass_residual = math.fsum(
                coefficient * molecular_weights[component]
                for component, coefficient in coefficients.items()
            )
            scale = math.fsum(
                abs(coefficient * molecular_weights[component])
                for component, coefficient in coefficients.items()
            )
            if not math.isclose(
                molar_mass_residual, 0.0, rel_tol=0.0, abs_tol=max(1e-10, scale * 1e-10)
            ):
                raise MaterialBalanceContractError(
                    f"reaction {reaction_id} stoichiometry is not mass-consistent with declared molecular weights"
                )
        for component, coefficient in coefficients.items():
            native_molar = coefficient * extent
            totals[component] += _convert_component_rate(
                native_molar,
                from_basis="molar",
                to_basis=selected_basis,
                component=component,
                molecular_weights=molecular_weights,
            )
    return totals


def _component_quantity_map(
    raw: object,
    *,
    components: tuple[str, ...],
    basis: str,
    label: str,
    non_negative: bool,
) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise MaterialBalanceContractError(f"{label} must be an object with every component")
    if set(raw) != set(components):
        missing = sorted(set(components) - set(raw))
        unknown = sorted(set(raw) - set(components))
        raise MaterialBalanceContractError(
            f"{label} must exactly cover components; missing={missing}, unknown={unknown}"
        )
    return {
        component: _quantity_to_canonical(
            raw[component],
            expected_basis=basis,
            label=f"{label}.{component}",
            non_negative=non_negative,
        )
        for component in components
    }


def _tolerance_contract(
    case: Mapping[str, Any],
    *,
    components: tuple[str, ...],
    basis: str,
) -> tuple[dict[str, float], float, dict[str, float]]:
    balance = case.get("balance")
    if not isinstance(balance, Mapping):
        raise MaterialBalanceContractError("balance contract is required")
    absolute_raw = balance.get("absolute_tolerances")
    if absolute_raw is None:
        global_absolute = _quantity_to_canonical(
            balance.get("absolute_tolerance"),
            expected_basis=basis,
            label="balance.absolute_tolerance",
            non_negative=True,
        )
        absolute = {component: global_absolute for component in components}
    else:
        absolute = _component_quantity_map(
            absolute_raw,
            components=components,
            basis=basis,
            label="balance.absolute_tolerances",
            non_negative=True,
        )
    relative = _finite_real(balance.get("relative_tolerance"), "balance.relative_tolerance")
    if relative < 0 or relative > 1:
        raise MaterialBalanceContractError("balance.relative_tolerance must be in [0, 1]")
    reference = _component_quantity_map(
        balance.get("reference_scales"),
        components=components,
        basis=basis,
        label="balance.reference_scales",
        non_negative=True,
    )
    if any(value == 0 for value in reference.values()):
        zero_components = sorted(component for component, value in reference.items() if value == 0)
        raise MaterialBalanceContractError(
            f"balance.reference_scales must be positive for every component: {zero_components}"
        )
    return absolute, relative, reference


def evaluate_material_balance(case: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and evaluate a system-boundary material balance.

    Returned JSON is strict and finite. Contract defects and physical closure
    failures both produce FAIL, with distinct reason codes.
    """

    errors: list[str] = []
    reason_codes: set[str] = set()
    basis: str | None = None
    canonical_unit: str | None = None
    components_result: list[ComponentBalance] = []
    total_result: dict[str, Any] | None = None

    try:
        if not isinstance(case, Mapping):
            raise MaterialBalanceContractError("process case must be an object")
        components = _normalize_components(case.get("components"))
        basis_value = case.get("balance_basis")
        if basis_value not in _ALLOWED_BASES:
            raise MaterialBalanceContractError("balance_basis must be mass or molar")
        basis = str(basis_value)
        canonical_unit = _CANONICAL_UNIT[basis]
        molecular_weights = _molecular_weights(case, components)

        streams = case.get("streams")
        if not isinstance(streams, list) or not streams:
            raise MaterialBalanceContractError("streams must be a non-empty list")
        incoming = {component: 0.0 for component in components}
        outgoing = {component: 0.0 for component in components}
        seen_streams: set[str] = set()
        for index, stream in enumerate(streams, start=1):
            if not isinstance(stream, Mapping):
                raise MaterialBalanceContractError(f"stream {index} must be an object")
            stream_id, source, target, rates = _stream_component_rates(
                stream,
                components=components,
                selected_basis=basis,
                molecular_weights=molecular_weights,
                index=index,
            )
            if stream_id in seen_streams:
                raise MaterialBalanceContractError(f"duplicate stream_id: {stream_id}")
            seen_streams.add(stream_id)
            if source == "EXTERNAL" and target == "EXTERNAL":
                raise MaterialBalanceContractError(
                    f"stream {stream_id} cannot be EXTERNAL on both boundaries"
                )
            if source == "EXTERNAL":
                for component, value in rates.items():
                    incoming[component] += value
            if target in _ALLOWED_DESTINATIONS:
                for component, value in rates.items():
                    outgoing[component] += value

        net_reaction = _reaction_rates(
            case,
            components=components,
            selected_basis=basis,
            molecular_weights=molecular_weights,
        )
        generation = {component: max(value, 0.0) for component, value in net_reaction.items()}
        consumption = {component: max(-value, 0.0) for component, value in net_reaction.items()}

        mode = case.get("mode")
        balance_contract = case.get("balance")
        if not isinstance(balance_contract, Mapping):
            raise MaterialBalanceContractError("balance contract is required")
        if mode == "steady":
            if balance_contract.get("steady_state_declared") is not True:
                raise MaterialBalanceContractError(
                    "steady mode requires balance.steady_state_declared=true"
                )
            accumulation = _component_quantity_map(
                case.get("accumulation"),
                components=components,
                basis=basis,
                label="accumulation",
                non_negative=False,
            )
            nonzero = [component for component, value in accumulation.items() if value != 0]
            if nonzero:
                raise MaterialBalanceContractError(
                    f"steady mode accumulation must be exactly zero: {sorted(nonzero)}"
                )
        elif mode == "dynamic":
            accumulation = _component_quantity_map(
                case.get("accumulation"),
                components=components,
                basis=basis,
                label="accumulation",
                non_negative=False,
            )
        else:
            raise MaterialBalanceContractError("mode must be steady or dynamic")

        absolute_tolerances, relative_tolerance, reference_scales = _tolerance_contract(
            case, components=components, basis=basis
        )
        failed_components: list[str] = []
        for component in components:
            right_hand_side = (
                incoming[component]
                - outgoing[component]
                + generation[component]
                - consumption[component]
            )
            residual = accumulation[component] - right_hand_side
            allowed = (
                absolute_tolerances[component] + relative_tolerance * reference_scales[component]
            )
            passed = abs(residual) <= allowed
            if not passed:
                failed_components.append(component)
            components_result.append(
                ComponentBalance(
                    component=component,
                    basis=basis,
                    canonical_unit=canonical_unit,
                    incoming=incoming[component],
                    outgoing=outgoing[component],
                    generation=generation[component],
                    consumption=consumption[component],
                    accumulation=accumulation[component],
                    residual=residual,
                    absolute_residual=abs(residual),
                    absolute_tolerance=absolute_tolerances[component],
                    relative_tolerance=relative_tolerance,
                    reference_scale=reference_scales[component],
                    allowed_residual=allowed,
                    component_pass=passed,
                )
            )
        total_in = math.fsum(item.incoming for item in components_result)
        total_out = math.fsum(item.outgoing for item in components_result)
        total_gen = math.fsum(item.generation for item in components_result)
        total_cons = math.fsum(item.consumption for item in components_result)
        total_acc = math.fsum(item.accumulation for item in components_result)
        total_residual = total_acc - (total_in - total_out + total_gen - total_cons)
        total_allowed = math.fsum(item.absolute_tolerance for item in components_result) + (
            relative_tolerance * math.fsum(item.reference_scale for item in components_result)
        )
        total_pass = abs(total_residual) <= total_allowed
        total_result = {
            "basis": basis,
            "canonical_unit": canonical_unit,
            "incoming": total_in,
            "outgoing": total_out,
            "generation": total_gen,
            "consumption": total_cons,
            "accumulation": total_acc,
            "residual": total_residual,
            "absolute_residual": abs(total_residual),
            "allowed_residual": total_allowed,
            "total_pass": total_pass,
        }
        if failed_components:
            reason_codes.add("COMPONENT_BALANCE_NOT_CLOSED")
        if not total_pass:
            reason_codes.add("TOTAL_BALANCE_NOT_CLOSED")
        passed = not failed_components and total_pass
        result = MaterialBalanceResult(
            schema_version=SCHEMA_VERSION,
            status="PASS" if passed else "FAIL",
            passed=passed,
            basis=basis,
            canonical_unit=canonical_unit,
            errors=(),
            reason_codes=tuple(sorted(reason_codes or {"BALANCE_CLOSED"})),
            failed_components=tuple(sorted(failed_components)),
            components=tuple(asdict(item) for item in components_result),
            total=total_result,
        )
        payload = asdict(result)
        payload["pass"] = payload.pop("passed")
        return payload
    except MaterialBalanceContractError as exc:
        errors.append(str(exc))
        reason_codes.add("INVALID_MATERIAL_BALANCE_CONTRACT")
        result = MaterialBalanceResult(
            schema_version=SCHEMA_VERSION,
            status="FAIL",
            passed=False,
            basis=basis,
            canonical_unit=canonical_unit,
            errors=tuple(errors),
            reason_codes=tuple(sorted(reason_codes)),
            failed_components=(),
            components=tuple(asdict(item) for item in components_result),
            total=total_result,
        )
        payload = asdict(result)
        payload["pass"] = payload.pop("passed")
        return payload


def check_component_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, Any]:
    """Evaluate component rows from the strict CSV adapter.

    Every row declares one basis, amount unit, time unit, all balance terms,
    absolute/relative tolerance, and reference scale. All rows must share one
    basis, but each row may use a different compatible representation unit.
    """

    if not rows:
        raise MaterialBalanceContractError("balance table is empty")
    seen: set[str] = set()
    declared_basis: str | None = None
    component_results: list[ComponentBalance] = []
    for index, row in enumerate(rows, start=2):
        component_raw = row.get("component")
        if not isinstance(component_raw, str) or not component_raw.strip():
            raise MaterialBalanceContractError(f"row {index}: component is required")
        component = component_raw.strip()
        if component in seen:
            raise MaterialBalanceContractError(f"row {index}: duplicate component {component}")
        seen.add(component)

        basis_raw = row.get("quantity_basis")
        if basis_raw not in _ALLOWED_BASES:
            raise MaterialBalanceContractError(f"row {index}: quantity_basis must be mass or molar")
        basis = str(basis_raw)
        if declared_basis is None:
            declared_basis = basis
        elif basis != declared_basis:
            raise MaterialBalanceContractError(
                f"row {index}: mixed mass/molar basis is not allowed"
            )

        amount_unit = row.get("quantity_unit")
        time_unit = row.get("time_unit")
        if not isinstance(amount_unit, str) or not amount_unit.strip():
            raise MaterialBalanceContractError(f"row {index}: quantity_unit is required")
        if not isinstance(time_unit, str) or not time_unit.strip():
            raise MaterialBalanceContractError(f"row {index}: time_unit is required")
        unit = f"{amount_unit.strip()}/{time_unit.strip()}"
        factor = _unit_factor(basis, unit, f"row {index}")

        def term(
            name: str,
            *,
            non_negative: bool,
            current_row: Mapping[str, object] = row,
            row_number: int = index,
            unit_factor: float = factor,
        ) -> float:
            value = _finite_real(
                current_row.get(name), f"row {row_number} {name}", allow_string=True
            )
            if non_negative and value < 0:
                raise MaterialBalanceContractError(f"row {row_number} {name} must be non-negative")
            converted = value * unit_factor
            if not math.isfinite(converted):
                raise MaterialBalanceContractError(
                    f"row {row_number} {name} conversion is non-finite"
                )
            return converted

        incoming = term("in", non_negative=True)
        outgoing = term("out", non_negative=True)
        generation = term("generation", non_negative=True)
        consumption = term("consumption", non_negative=True)
        accumulation = term("accumulation", non_negative=False)
        absolute_tolerance = term("absolute_tolerance", non_negative=True)
        relative_tolerance = _finite_real(
            row.get("relative_tolerance"),
            f"row {index} relative_tolerance",
            allow_string=True,
        )
        if relative_tolerance < 0 or relative_tolerance > 1:
            raise MaterialBalanceContractError(f"row {index}: relative_tolerance must be in [0, 1]")
        reference_scale = term("reference_scale", non_negative=True)
        if reference_scale <= 0:
            raise MaterialBalanceContractError(f"row {index}: reference_scale must be positive")

        residual = accumulation - (incoming - outgoing + generation - consumption)
        if not math.isfinite(residual):
            raise MaterialBalanceContractError(f"row {index}: residual is non-finite")
        allowed = absolute_tolerance + relative_tolerance * reference_scale
        if not math.isfinite(allowed):
            raise MaterialBalanceContractError(f"row {index}: allowed residual is non-finite")
        component_results.append(
            ComponentBalance(
                component=component,
                basis=basis,
                canonical_unit=_CANONICAL_UNIT[basis],
                incoming=incoming,
                outgoing=outgoing,
                generation=generation,
                consumption=consumption,
                accumulation=accumulation,
                residual=residual,
                absolute_residual=abs(residual),
                absolute_tolerance=absolute_tolerance,
                relative_tolerance=relative_tolerance,
                reference_scale=reference_scale,
                allowed_residual=allowed,
                component_pass=abs(residual) <= allowed,
            )
        )

    if declared_basis is None:  # guarded by the non-empty rows check
        raise MaterialBalanceContractError("balance basis is missing")

    total_in = math.fsum(item.incoming for item in component_results)
    total_out = math.fsum(item.outgoing for item in component_results)
    total_generation = math.fsum(item.generation for item in component_results)
    total_consumption = math.fsum(item.consumption for item in component_results)
    total_accumulation = math.fsum(item.accumulation for item in component_results)
    total_residual = total_accumulation - (
        total_in - total_out + total_generation - total_consumption
    )
    total_allowed = math.fsum(item.absolute_tolerance for item in component_results) + math.fsum(
        item.relative_tolerance * item.reference_scale for item in component_results
    )
    total_pass = abs(total_residual) <= total_allowed
    failed_components = tuple(
        item.component for item in component_results if not item.component_pass
    )
    component_pass = not failed_components
    passed = component_pass and total_pass
    reason_codes: list[str] = []
    if not component_pass:
        reason_codes.append("COMPONENT_BALANCE_NOT_CLOSED")
    if not total_pass:
        reason_codes.append("TOTAL_BALANCE_NOT_CLOSED")
    if passed:
        reason_codes.append("BALANCE_CLOSED")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if passed else "FAIL",
        "pass": passed,
        "basis": declared_basis,
        "canonical_unit": _CANONICAL_UNIT[declared_basis],
        "errors": [],
        "reason_codes": reason_codes,
        "failed_components": list(failed_components),
        "components": [asdict(item) for item in component_results],
        "component_balances_pass": component_pass,
        "total_balance_pass": total_pass,
        "total": {
            "basis": declared_basis,
            "canonical_unit": _CANONICAL_UNIT[declared_basis],
            "incoming": total_in,
            "outgoing": total_out,
            "generation": total_generation,
            "consumption": total_consumption,
            "accumulation": total_accumulation,
            "residual": total_residual,
            "absolute_residual": abs(total_residual),
            "allowed_residual": total_allowed,
            "total_pass": total_pass,
        },
    }
    json.dumps(payload, allow_nan=False)
    return payload
