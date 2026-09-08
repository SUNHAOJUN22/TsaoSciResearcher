from __future__ import annotations

import math
import re
from typing import Any

_ALLOWED_PROPERTY_METHODS = {"PC-SAFT", "SRK", "REFPROP", "STEAMNBS", "CUSTOM"}
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _range(
    value: object, *, low_limit: float | None = None, high_limit: float | None = None
) -> bool:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_finite_number(item) for item in value)
    ):
        return False
    low, high = value
    if low > high:
        return False
    if low_limit is not None and low < low_limit:
        return False
    return high_limit is None or high <= high_limit


def qualify_property_method(
    record: dict[str, Any], query: dict[str, Any] | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    holds: list[str] = []
    if not isinstance(record, dict):
        return {
            "status": "FAIL",
            "pass": False,
            "errors": ["property method record must be an object"],
            "holds": [],
            "scientific_approval": "NOT_EVALUATED",
        }
    method = str(record.get("method", "")).upper()
    if method not in _ALLOWED_PROPERTY_METHODS:
        errors.append(f"unsupported property method: {method or '<missing>'}")
    required = (
        "selection_basis",
        "components",
        "parameter_sources",
        "temperature_K",
        "pressure_Pa",
        "composition_domain",
        "polymer_mass_fraction",
        "benchmarks",
        "error_metrics",
        "unit_system",
        "extrapolation_status",
    )
    for field in required:
        if field not in record:
            holds.append(f"missing property qualification field: {field}")
    if record.get("unit_system") not in (None, "SI"):
        errors.append("property method unit_system must be SI")
    components = record.get("components")
    if not isinstance(components, list) or not components:
        holds.append("components must be a non-empty list")
        components = []
    elif any(not isinstance(item, str) or not item.strip() for item in components):
        errors.append("components must contain non-empty strings")
    elif len(components) != len(set(components)):
        errors.append("components must be unique")
    range_contracts = {
        "temperature_K": (0.0, None),
        "pressure_Pa": (0.0, None),
        "polymer_mass_fraction": (0.0, 1.0),
    }
    for name, (lower, upper) in range_contracts.items():
        bounds = record.get(name)
        if bounds is not None and not _range(bounds, low_limit=lower, high_limit=upper):
            errors.append(f"{name} must be an ordered finite range inside its physical limits")
    composition_domain = record.get("composition_domain")
    if composition_domain is not None:
        if not isinstance(composition_domain, dict) or not composition_domain:
            errors.append("composition_domain must be a non-empty object")
        else:
            unknown = set(composition_domain) - set(components)
            if unknown:
                errors.append(f"composition_domain contains unknown components: {sorted(unknown)}")
            for component, bounds in composition_domain.items():
                if not _range(bounds, low_limit=0.0, high_limit=1.0):
                    errors.append(f"composition_domain.{component} must be an ordered 0-1 range")
    sources = record.get("parameter_sources")
    if not isinstance(sources, list) or not sources:
        holds.append("parameter sources are required")
    elif any(not isinstance(item, str) or not item.strip() for item in sources):
        errors.append("parameter_sources must contain non-empty strings")
    benchmarks = record.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        holds.append("at least one benchmark is required")
    else:
        for index, benchmark in enumerate(benchmarks, start=1):
            if not isinstance(benchmark, dict):
                errors.append(f"benchmark {index} must be an object")
                continue
            points = benchmark.get("points")
            if (
                not benchmark.get("property")
                or not benchmark.get("source")
                or isinstance(points, bool)
                or not isinstance(points, int)
                or points <= 0
            ):
                errors.append(f"benchmark {index} requires property, source and positive points")
    metrics = record.get("error_metrics")
    if not isinstance(metrics, dict) or not metrics:
        holds.append("error_metrics must be a non-empty object")
    elif any(not _finite_number(value) or value < 0 for value in metrics.values()):
        errors.append("error_metrics values must be finite and non-negative")
    extrapolation = record.get("extrapolation_status")
    if extrapolation not in (None, "NONE", "DECLARED_HOLD"):
        errors.append("invalid extrapolation_status")
    elif extrapolation == "DECLARED_HOLD":
        holds.append("property method is explicitly marked for extrapolation HOLD")
    if method == "STEAMNBS" and any(
        str(component).casefold() not in {"water", "steam"} for component in components
    ):
        holds.append("STEAMNBS is restricted to water/steam duties")
    if method == "SRK":
        bounds = record.get("polymer_mass_fraction")
        if (
            isinstance(bounds, list)
            and len(bounds) == 2
            and _finite_number(bounds[1])
            and bounds[1] > 0
        ):
            holds.append("SRK polymer-rich use requires an independently qualified correction")
    if method == "CUSTOM":
        equations = record.get("custom_equations")
        if (
            not isinstance(equations, list)
            or not equations
            or any(not isinstance(item, str) or not item.strip() for item in equations)
        ):
            holds.append("CUSTOM method requires equations and coefficient provenance")
    if query is not None:
        if not isinstance(query, dict):
            errors.append("property query must be an object")
        elif not errors:
            for name in ("temperature_K", "pressure_Pa", "polymer_mass_fraction"):
                if name not in query:
                    continue
                value = query[name]
                bounds = record.get(name)
                if not _finite_number(value):
                    errors.append(f"query {name} must be finite")
                elif (
                    isinstance(bounds, list)
                    and len(bounds) == 2
                    and not bounds[0] <= value <= bounds[1]
                ):
                    holds.append(f"query {name} is outside the qualified range")
            qcomp = query.get("components", [])
            if qcomp:
                if not isinstance(qcomp, list) or any(not isinstance(item, str) for item in qcomp):
                    errors.append("query components must be a string list")
                elif not set(qcomp).issubset(set(components)):
                    holds.append("query contains components outside the qualified set")
    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return {
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "scientific_approval": "NOT_EVALUATED",
    }


def validate_process_case(case: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    holds: list[str] = []
    if not isinstance(case, dict):
        return {
            "status": "FAIL",
            "pass": False,
            "errors": ["process case must be an object"],
            "holds": [],
            "engineering_approval": "NOT_EVALUATED",
        }
    mode = case.get("mode")
    if mode not in {"steady", "dynamic"}:
        errors.append("mode must be steady or dynamic")
    components = case.get("components")
    if (
        not isinstance(components, list)
        or not components
        or any(not isinstance(item, str) or not item.strip() for item in components)
        or len(set(components)) != len(components)
    ):
        errors.append("components must be a unique non-empty string list")
        components = []
    equipment = case.get("equipment")
    if not isinstance(equipment, list) or not equipment:
        errors.append("equipment must be non-empty")
        equipment = []
    equipment_ids: set[str] = set()
    for index, item in enumerate(equipment, start=1):
        if not isinstance(item, dict):
            errors.append(f"equipment entry {index} must be an object")
            continue
        equipment_id = item.get("equipment_id")
        if not isinstance(equipment_id, str) or not equipment_id.strip():
            errors.append(f"equipment entry {index} needs a non-empty equipment_id")
        elif equipment_id in equipment_ids:
            errors.append(f"duplicate equipment_id: {equipment_id}")
        else:
            equipment_ids.add(equipment_id)
        if not isinstance(item.get("type"), str) or not item["type"].strip():
            errors.append(f"equipment {equipment_id or index} needs a type")
    streams = case.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("streams must be non-empty")
        streams = []
    seen_streams: set[str] = set()
    external_feed = external_product = declared_loss = 0.0
    for index, item in enumerate(streams, start=1):
        if not isinstance(item, dict):
            errors.append(f"stream entry {index} must be an object")
            continue
        sid = item.get("stream_id")
        if not isinstance(sid, str) or not sid.strip() or sid in seen_streams:
            errors.append(f"stream_id must be non-empty and unique: {sid}")
        else:
            seen_streams.add(sid)
        source = item.get("from")
        target = item.get("to")
        if source not in equipment_ids | {"EXTERNAL"}:
            errors.append(f"stream {sid} has unknown source {source}")
        if target not in equipment_ids | {"EXTERNAL", "EMISSION", "LOSS"}:
            errors.append(f"stream {sid} has unknown destination {target}")
        flow = item.get("flow_kg_h")
        if not _finite_number(flow) or flow < 0:
            errors.append(f"stream {sid} has invalid flow_kg_h")
            continue
        composition = item.get("composition")
        if not isinstance(composition, dict) or not composition:
            errors.append(f"stream {sid} composition must be a non-empty object")
        else:
            unknown = set(composition) - set(components)
            if unknown:
                errors.append(f"stream {sid} has invalid composition components {sorted(unknown)}")
            values = list(composition.values())
            if any(not _finite_number(value) or value < 0 or value > 1 for value in values):
                errors.append(f"stream {sid} composition values must be finite fractions")
            elif abs(sum(values) - 1.0) > 1e-6:
                errors.append(f"stream {sid} composition does not sum to one")
        if item.get("is_recycle") and item.get("closed") is not True:
            holds.append(f"recycle stream {sid} is not closed")
        if source == "EXTERNAL":
            external_feed += float(flow)
        if target == "EXTERNAL":
            external_product += float(flow)
        if target in {"EMISSION", "LOSS"}:
            declared_loss += float(flow)
    tolerance = case.get("mass_balance_tolerance_fraction", 0.001)
    if not _finite_number(tolerance) or tolerance < 0 or tolerance > 0.1:
        errors.append("mass_balance_tolerance_fraction must be finite and between 0 and 0.1")
        tolerance = 0.001
    residual = None
    if external_feed > 0:
        residual = abs(external_feed - external_product - declared_loss) / external_feed
        if residual > tolerance:
            holds.append(f"mass balance residual {residual:.6g} exceeds {tolerance:.6g}")
    else:
        holds.append("no positive external feed was declared")
    property_result = qualify_property_method(
        case.get("property_method", {}), case.get("property_query")
    )
    if property_result["status"] == "FAIL":
        errors.extend(f"property method: {item}" for item in property_result["errors"])
    elif property_result["status"] != "PASS":
        holds.extend(f"property method: {item}" for item in property_result["holds"])
    if case.get("convergence") is not True:
        holds.append("model convergence is not demonstrated")
    dynamic_claim = mode == "dynamic" or (
        isinstance(case.get("claims"), dict) and case["claims"].get("dynamic_validated")
    )
    if dynamic_claim:
        dynamic_assets = case.get("dynamic_assets")
        if not isinstance(dynamic_assets, list) or not dynamic_assets:
            holds.append("dynamic claim has no dynamic asset identity")
        for field in ("controllers", "valves", "volumes", "disturbances"):
            value = case.get(field)
            if not isinstance(value, list) or not value:
                holds.append(f"dynamic case missing {field}")
        if not isinstance(case.get("initial_conditions"), dict) or not case["initial_conditions"]:
            holds.append("dynamic case missing initial_conditions")
    hashes = case.get("source_asset_sha256")
    if (
        not isinstance(hashes, list)
        or not hashes
        or len(hashes) != len(set(hashes))
        or any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in hashes)
    ):
        holds.append("source asset SHA-256 identities are missing, duplicate or invalid")
    criteria = case.get("acceptance_criteria")
    if (
        not isinstance(criteria, list)
        or not criteria
        or any(not isinstance(item, str) or not item.strip() for item in criteria)
    ):
        holds.append("acceptance criteria are missing")
    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return {
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "metrics": {
            "external_feed_kg_h": external_feed,
            "external_product_kg_h": external_product,
            "declared_loss_kg_h": declared_loss,
            "mass_balance_residual_fraction": residual,
        },
        "engineering_approval": "NOT_EVALUATED",
    }
