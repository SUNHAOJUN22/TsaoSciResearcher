from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

_BOUNDARY_NODES = {"BOUNDARY_IN", "BOUNDARY_OUT", "ENVIRONMENT"}
_ACCEPTANCE_STATES = {"NOT_EVALUATED", "HOLD", "CONDITIONAL", "PASS", "FAIL"}
_EVIDENCE_STATES = {"REPORTED", "CALCULATED", "QUALIFIED", "HOLD", "SUPERSEDED", "RETRACTED"}


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _records(value: object, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            errors.append(f"{label} row {index} must be an object")
        else:
            records.append(item)
    return records


def _unique_ids(
    records: list[dict[str, Any]], field: str, label: str, errors: list[str]
) -> set[str]:
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} row {index} has invalid {field}")
            continue
        if value in seen:
            errors.append(f"duplicate {label} {field}: {value}")
        seen.add(value)
    return seen


def _nonnegative_component_map(
    value: object,
    *,
    label: str,
    components: set[str],
    errors: list[str],
) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    result: dict[str, float] = {}
    for component, raw in value.items():
        if component not in components:
            errors.append(f"{label} uses undeclared component: {component}")
            continue
        try:
            amount = _finite(raw, f"{label} {component}")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if amount < 0:
            errors.append(f"{label} {component} must be non-negative")
            continue
        result[component] = amount
    return result


def process_package_template(process_family: str) -> dict[str, Any]:
    if not isinstance(process_family, str) or not process_family.strip():
        raise ValueError("process_family must be a non-empty string")
    return {
        "package_id": "TEMPLATE-NOT-A-DESIGN-BASIS",
        "process_family": process_family.strip(),
        "status": "NOT_EVALUATED",
        "tolerances": {
            "composition_abs": 1e-6,
            "mass_relative": 1e-4,
            "component_relative": 1e-4,
            "energy_relative": 1e-3,
        },
        "design_basis": {
            "basis_version": "DRAFT",
            "capacity_kg_h": 1.0,
            "operating_hours_h_y": 1.0,
            "components": ["COMPONENT-A"],
        },
        "streams": [],
        "equipment": [],
        "utilities": [],
        "controls": [],
        "hse": [],
        "evidence_ledger": [],
        "acceptance": [],
        "approvals": {},
    }


def validate_process_package(package: object) -> dict[str, Any]:
    errors: list[str] = []
    holds: list[str] = []
    reason_codes: set[str] = set()
    if not isinstance(package, dict):
        return {
            "status": "FAIL",
            "pass": False,
            "errors": ["package root must be an object"],
            "holds": [],
            "reason_codes": ["INVALID_PACKAGE_ROOT"],
        }

    package_id = package.get("package_id")
    process_family = package.get("process_family")
    declared_status = package.get("status", "NOT_EVALUATED")
    if not isinstance(package_id, str) or not package_id.strip():
        errors.append("package_id is required")
        reason_codes.add("MISSING_PACKAGE_ID")
    if not isinstance(process_family, str) or not process_family.strip():
        errors.append("process_family is required")
        reason_codes.add("MISSING_PROCESS_FAMILY")
    if declared_status not in _ACCEPTANCE_STATES:
        errors.append("package status is invalid")
        reason_codes.add("INVALID_DECLARED_STATUS")
    if package_id == "TEMPLATE-NOT-A-DESIGN-BASIS":
        holds.append("template package is not an approved design basis")
        reason_codes.add("TEMPLATE_NOT_DESIGN_BASIS")

    tolerances = package.get("tolerances", {})
    if not isinstance(tolerances, dict):
        errors.append("tolerances must be an object")
        tolerances = {}
    try:
        composition_tol = _finite(tolerances.get("composition_abs", 1e-6), "composition tolerance")
        mass_tol = _finite(tolerances.get("mass_relative", 1e-4), "mass tolerance")
        component_tol = _finite(
            tolerances.get("component_relative", mass_tol), "component tolerance"
        )
        energy_tol = _finite(tolerances.get("energy_relative", 1e-3), "energy tolerance")
        if min(composition_tol, mass_tol, component_tol, energy_tol) < 0:
            raise ValueError("tolerances must be non-negative")
    except ValueError as exc:
        errors.append(str(exc))
        reason_codes.add("INVALID_TOLERANCE")
        composition_tol, mass_tol, component_tol, energy_tol = 1e-6, 1e-4, 1e-4, 1e-3

    design_basis = package.get("design_basis")
    components: set[str] = set()
    if not isinstance(design_basis, dict):
        errors.append("design_basis must be an object")
        reason_codes.add("INVALID_DESIGN_BASIS")
    else:
        for field in ("basis_version", "components"):
            if field not in design_basis:
                errors.append(f"design_basis.{field} is required")
        try:
            if _finite(design_basis.get("capacity_kg_h"), "design capacity") <= 0:
                errors.append("design capacity must be positive")
            if _finite(design_basis.get("operating_hours_h_y"), "operating hours") <= 0:
                errors.append("operating hours must be positive")
        except ValueError as exc:
            errors.append(str(exc))
        raw_components = design_basis.get("components")
        if not isinstance(raw_components, list) or not raw_components:
            errors.append("design_basis.components must be a non-empty list")
        else:
            for item in raw_components:
                if not isinstance(item, str) or not item.strip():
                    errors.append("design_basis.components contains an invalid component")
                elif item in components:
                    errors.append(f"duplicate design component: {item}")
                else:
                    components.add(item)

    streams = _records(package.get("streams"), "streams", errors)
    equipment = _records(package.get("equipment"), "equipment", errors)
    utilities = _records(package.get("utilities", []), "utilities", errors)
    controls = _records(package.get("controls", []), "controls", errors)
    hazards = _records(package.get("hse", []), "hse", errors)
    evidence = _records(package.get("evidence_ledger", []), "evidence_ledger", errors)
    acceptance = _records(package.get("acceptance", []), "acceptance", errors)

    _unique_ids(streams, "stream_id", "stream", errors)
    equipment_ids = _unique_ids(equipment, "equipment_id", "equipment", errors)
    _unique_ids(utilities, "utility_id", "utility", errors)
    _unique_ids(controls, "loop_id", "control", errors)
    _unique_ids(hazards, "hazard_id", "hazard", errors)
    evidence_ids = _unique_ids(evidence, "evidence_id", "evidence", errors)
    _unique_ids(acceptance, "criterion_id", "acceptance", errors)

    evidence_status: dict[str, str] = {}
    for record in evidence:
        identifier = record.get("evidence_id")
        state = record.get("status")
        if isinstance(identifier, str):
            if state not in _EVIDENCE_STATES:
                errors.append(f"evidence {identifier} has invalid status")
            else:
                evidence_status[identifier] = state
        if not record.get("locator") or not record.get("applicability"):
            holds.append(f"evidence {identifier or '<unknown>'} lacks locator or applicability")
            reason_codes.add("INCOMPLETE_EVIDENCE_RECORD")

    component_names = tuple(sorted(components))
    component_index = {component: index for index, component in enumerate(component_names)}
    # Store one compact record per stream instead of four parallel dictionaries.
    # Layout: mass, enthalpy, component masses, source, destination.
    stream_data_by_id: dict[
        str, tuple[float, float, tuple[float, ...], str | None, str | None]
    ] = {}
    for stream in streams:
        identifier = stream.get("stream_id")
        source = stream.get("source")
        destination = stream.get("destination")
        for label, node in (("source", source), ("destination", destination)):
            if not isinstance(node, str) or not node.strip():
                errors.append(f"stream {identifier or '<unknown>'} has invalid {label}")
            elif node not in equipment_ids and node not in _BOUNDARY_NODES:
                errors.append(
                    f"stream {identifier or '<unknown>'} references unknown {label}: {node}"
                )
        if source == "BOUNDARY_OUT":
            errors.append(f"stream {identifier} cannot originate at BOUNDARY_OUT")
            reason_codes.add("INVALID_BOUNDARY_DIRECTION")
        if destination == "BOUNDARY_IN":
            errors.append(f"stream {identifier} cannot terminate at BOUNDARY_IN")
            reason_codes.add("INVALID_BOUNDARY_DIRECTION")
        if source == destination and source is not None:
            errors.append(f"stream {identifier} source and destination must differ")
        try:
            total_mass = _finite(stream.get("total_mass_kg_h"), f"stream {identifier} mass flow")
            enthalpy = _finite(stream.get("enthalpy_kW"), f"stream {identifier} enthalpy")
            if total_mass < 0:
                errors.append(f"stream {identifier} mass flow must be non-negative")
        except ValueError as exc:
            errors.append(str(exc))
            total_mass = 0.0
            enthalpy = 0.0
        composition = stream.get("composition")
        component_mass = [0.0] * len(component_names)
        if not isinstance(composition, dict) or not composition:
            errors.append(f"stream {identifier} composition must be a non-empty object")
        else:
            total_fraction = 0.0
            for component, fraction in composition.items():
                index = component_index.get(component)
                if index is None:
                    errors.append(f"stream {identifier} uses undeclared component: {component}")
                try:
                    value = _finite(fraction, f"stream {identifier} composition {component}")
                    if value < 0:
                        errors.append(
                            f"stream {identifier} composition {component} must be non-negative"
                        )
                    total_fraction += value
                    if index is not None:
                        component_mass[index] = total_mass * value
                except ValueError as exc:
                    errors.append(str(exc))
            if abs(total_fraction - 1.0) > composition_tol:
                errors.append(
                    f"stream {identifier} composition sum is {total_fraction:.12g}, expected 1"
                )
        if isinstance(identifier, str):
            stream_data_by_id[identifier] = (
                total_mass,
                enthalpy,
                tuple(component_mass),
                source if isinstance(source, str) else None,
                destination if isinstance(destination, str) else None,
            )
        refs = stream.get("evidence_ids", [])
        if not isinstance(refs, list) or not refs:
            holds.append(f"stream {identifier} has no evidence_ids")
            reason_codes.add("STREAM_EVIDENCE_MISSING")
        else:
            for ref in refs:
                if ref not in evidence_ids:
                    errors.append(f"stream {identifier} references unknown evidence: {ref}")

    max_mass_error = 0.0
    max_energy_error = 0.0
    max_component_error = 0.0
    component_balance_errors: dict[str, dict[str, float]] = {}
    failed_component_balances: set[str] = set()
    inlet_usage: dict[str, int] = {}
    outlet_usage: dict[str, int] = {}

    for item in equipment:
        identifier = item.get("equipment_id")
        if not isinstance(identifier, str):
            continue
        inlet_ids = item.get("inlet_stream_ids")
        outlet_ids = item.get("outlet_stream_ids")
        if not isinstance(inlet_ids, list) or not isinstance(outlet_ids, list):
            errors.append(f"equipment {identifier} inlet/outlet stream IDs must be lists")
            continue
        if not inlet_ids and not outlet_ids:
            errors.append(f"equipment {identifier} is isolated")
            reason_codes.add("ISOLATED_EQUIPMENT")
        if len(inlet_ids) != len(set(inlet_ids)) or len(outlet_ids) != len(set(outlet_ids)):
            errors.append(f"equipment {identifier} contains duplicate stream references")
            reason_codes.add("DUPLICATE_STREAM_REFERENCE")

        inlet_data: list[tuple[float, float, tuple[float, ...], str | None, str | None]] = []
        outlet_data: list[tuple[float, float, tuple[float, ...], str | None, str | None]] = []
        references_valid = True
        for ref in inlet_ids:
            inlet_usage[ref] = inlet_usage.get(ref, 0) + 1
            stream_data = stream_data_by_id.get(ref)
            if stream_data is None:
                errors.append(f"equipment {identifier} references unknown stream: {ref}")
                references_valid = False
                continue
            inlet_data.append(stream_data)
            if stream_data[4] != identifier:
                errors.append(
                    f"equipment {identifier} inlet {ref} destination is {stream_data[4]}, expected {identifier}"
                )
                reason_codes.add("STREAM_TOPOLOGY_MISMATCH")
        for ref in outlet_ids:
            outlet_usage[ref] = outlet_usage.get(ref, 0) + 1
            stream_data = stream_data_by_id.get(ref)
            if stream_data is None:
                errors.append(f"equipment {identifier} references unknown stream: {ref}")
                references_valid = False
                continue
            outlet_data.append(stream_data)
            if stream_data[3] != identifier:
                errors.append(
                    f"equipment {identifier} outlet {ref} source is {stream_data[3]}, expected {identifier}"
                )
                reason_codes.add("STREAM_TOPOLOGY_MISMATCH")
        if not references_valid:
            continue

        mass_in = sum(data[0] for data in inlet_data)
        mass_out = sum(data[0] for data in outlet_data)
        mass_scale = max(abs(mass_in), abs(mass_out), 1.0)
        mass_error = abs(mass_in - mass_out) / mass_scale
        if mass_error > max_mass_error:
            max_mass_error = mass_error
        if mass_error > mass_tol:
            errors.append(
                f"equipment {identifier} mass balance relative error {mass_error:.6g} exceeds {mass_tol:.6g}"
            )
            reason_codes.add("MASS_BALANCE_FAILURE")

        generation_raw = item.get("generation_kg_h", item.get("generation"))
        consumption_raw = item.get("consumption_kg_h", item.get("consumption"))
        generation = (
            {}
            if generation_raw is None
            else _nonnegative_component_map(
                generation_raw,
                label=f"equipment {identifier} generation",
                components=components,
                errors=errors,
            )
        )
        consumption = (
            {}
            if consumption_raw is None
            else _nonnegative_component_map(
                consumption_raw,
                label=f"equipment {identifier} consumption",
                components=components,
                errors=errors,
            )
        )
        declared_reaction = bool(generation or consumption or item.get("reaction_basis"))
        if declared_reaction:
            reaction_basis = item.get("reaction_basis")
            if not isinstance(reaction_basis, dict) or not reaction_basis:
                holds.append(f"equipment {identifier} reaction basis is incomplete")
                reason_codes.add("REACTION_BASIS_INCOMPLETE")
            elif not reaction_basis.get("stoichiometry") and not reaction_basis.get("description"):
                holds.append(
                    f"equipment {identifier} reaction basis lacks stoichiometry or description"
                )
                reason_codes.add("REACTION_BASIS_INCOMPLETE")

        per_component: dict[str, float] | None = None
        for component_position, component in enumerate(component_names):
            component_in = 0.0
            for data in inlet_data:
                component_in += data[2][component_position]
            component_out = 0.0
            for data in outlet_data:
                component_out += data[2][component_position]
            generated = generation.get(component, 0.0)
            consumed = consumption.get(component, 0.0)
            residual = component_in + generated - component_out - consumed
            scale = max(component_in + generated, component_out + consumed, 1.0)
            relative = abs(residual) / scale
            if relative > max_component_error:
                max_component_error = relative
            if relative != 0.0:
                if per_component is None:
                    per_component = {}
                per_component[component] = relative
            if relative > component_tol:
                failed_component_balances.add(f"{identifier}:{component}")
                if not declared_reaction:
                    errors.append(
                        f"equipment {identifier} changes component {component} without a declared reaction basis"
                    )
                    reason_codes.add("UNDECLARED_COMPONENT_CHANGE")
                else:
                    errors.append(
                        f"equipment {identifier} component {component} balance relative error {relative:.6g} exceeds {component_tol:.6g}"
                    )
                    reason_codes.add("COMPONENT_BALANCE_FAILURE")
        if per_component is not None:
            component_balance_errors[identifier] = per_component

        enthalpy_in = sum(data[1] for data in inlet_data)
        enthalpy_out = sum(data[1] for data in outlet_data)
        try:
            duty = _finite(item.get("duty_kW", 0.0), f"equipment {identifier} duty")
        except ValueError as exc:
            errors.append(str(exc))
            duty = 0.0
        energy_scale = max(abs(enthalpy_in) + abs(duty), abs(enthalpy_out), 1.0)
        energy_error = abs(enthalpy_in + duty - enthalpy_out) / energy_scale
        if energy_error > max_energy_error:
            max_energy_error = energy_error
        if energy_error > energy_tol:
            errors.append(
                f"equipment {identifier} energy balance relative error {energy_error:.6g} exceeds {energy_tol:.6g}"
            )
            reason_codes.add("ENERGY_BALANCE_FAILURE")
        if item.get("design_status") not in _ACCEPTANCE_STATES:
            holds.append(f"equipment {identifier} design_status is not evaluated")
            reason_codes.add("EQUIPMENT_STATUS_NOT_EVALUATED")

    for stream_id, stream_data in stream_data_by_id.items():
        source = stream_data[3]
        destination = stream_data[4]
        inlet_count = inlet_usage.get(stream_id, 0)
        outlet_count = outlet_usage.get(stream_id, 0)
        if destination in equipment_ids and inlet_count != 1:
            errors.append(
                f"stream {stream_id} must appear exactly once as an inlet; found {inlet_count}"
            )
            reason_codes.add("STREAM_REFERENCE_COUNT_MISMATCH")
        if source in equipment_ids and outlet_count != 1:
            errors.append(
                f"stream {stream_id} must appear exactly once as an outlet; found {outlet_count}"
            )
            reason_codes.add("STREAM_REFERENCE_COUNT_MISMATCH")
        if source not in equipment_ids and destination not in equipment_ids:
            errors.append(f"stream {stream_id} is not connected to equipment")
            reason_codes.add("ORPHAN_STREAM")
    for stream_id, count in inlet_usage.items():
        if count > 1:
            errors.append(f"stream {stream_id} is referenced by multiple equipment inlets")
            reason_codes.add("DUPLICATE_STREAM_REFERENCE")
    for stream_id, count in outlet_usage.items():
        if count > 1:
            errors.append(f"stream {stream_id} is referenced by multiple equipment outlets")
            reason_codes.add("DUPLICATE_STREAM_REFERENCE")

    for utility in utilities:
        identifier = utility.get("utility_id")
        try:
            if _finite(utility.get("consumption"), f"utility {identifier} consumption") < 0:
                errors.append(f"utility {identifier} consumption must be non-negative")
        except ValueError as exc:
            errors.append(str(exc))
        if not utility.get("unit"):
            errors.append(f"utility {identifier} unit is required")

    for loop in controls:
        identifier = loop.get("loop_id")
        for field in (
            "controlled_variable",
            "manipulated_variable",
            "measurement_tag",
            "final_element_tag",
        ):
            if not isinstance(loop.get(field), str) or not loop[field].strip():
                holds.append(f"control {identifier} lacks {field}")
                reason_codes.add("CONTROL_DEFINITION_INCOMPLETE")
        if loop.get("status") not in _ACCEPTANCE_STATES:
            holds.append(f"control {identifier} status is not evaluated")

    for hazard in hazards:
        identifier = hazard.get("hazard_id")
        safeguards = hazard.get("safeguards")
        if not isinstance(safeguards, list) or not safeguards:
            errors.append(f"hazard {identifier} has no safeguards")
            reason_codes.add("HAZARD_WITHOUT_SAFEGUARD")
        if hazard.get("status") != "PASS":
            holds.append(f"hazard {identifier} is not closed")
            reason_codes.add("HAZARD_NOT_CLOSED")

    if not acceptance:
        holds.append("package has no acceptance criteria")
        reason_codes.add("ACCEPTANCE_MISSING")
    for criterion in acceptance:
        identifier = criterion.get("criterion_id")
        state = criterion.get("status")
        if state not in _ACCEPTANCE_STATES:
            errors.append(f"acceptance {identifier} has invalid status")
            continue
        refs = criterion.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            holds.append(f"acceptance {identifier} has no evidence_ids")
        else:
            for ref in refs:
                if ref not in evidence_ids:
                    errors.append(f"acceptance {identifier} references unknown evidence: {ref}")
                elif state == "PASS" and evidence_status.get(ref) != "QUALIFIED":
                    errors.append(
                        f"acceptance {identifier} PASS uses non-qualified evidence: {ref}"
                    )
        if state == "PASS" and not criterion.get("approver"):
            errors.append(f"acceptance {identifier} PASS requires named approver")
        elif state != "PASS":
            holds.append(f"acceptance {identifier} is {state}")

    approvals = package.get("approvals")
    if not isinstance(approvals, dict):
        holds.append("package approvals are missing")
        reason_codes.add("PACKAGE_APPROVALS_MISSING")
    else:
        for role in ("package_approver", "process", "controls", "hse"):
            if not isinstance(approvals.get(role), str) or not approvals[role].strip():
                holds.append(f"package approval missing: {role}")
                reason_codes.add("PACKAGE_APPROVALS_MISSING")

    computed_status = "FAIL" if errors else "HOLD" if holds else "PASS"
    if declared_status == "PASS" and computed_status != "PASS":
        message = f"package declares PASS but computed audit status is {computed_status}"
        reason_codes.add("FALSE_PASS_DECLARATION")
        if computed_status == "FAIL":
            errors.append(message)
        else:
            holds.append(message)

    return {
        "status": computed_status,
        "declared_status": declared_status,
        "pass": computed_status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "reason_codes": sorted(reason_codes),
        "component_balance_errors": component_balance_errors,
        "failed_component_balances": sorted(failed_component_balances),
        "metrics": {
            "stream_count": len(streams),
            "equipment_count": len(equipment),
            "acceptance_count": len(acceptance),
            "max_mass_balance_relative_error": max_mass_error,
            "max_component_balance_relative_error": max_component_error,
            "max_energy_balance_relative_error": max_energy_error,
        },
    }


def normalized_package_copy(package: dict[str, Any]) -> dict[str, Any]:
    """Return a defensive copy for adapters without mutating caller-owned data."""
    if not isinstance(package, dict):
        raise ValueError("package must be an object")
    return deepcopy(package)
