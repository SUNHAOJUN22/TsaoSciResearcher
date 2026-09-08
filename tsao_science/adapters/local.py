"""Adapters call retained source implementations; they do not reimplement solvers."""
from __future__ import annotations
import dataclasses
import importlib.util
import sys
from pathlib import Path
from typing import Any
from ..core.jsonio import finite_real
from ..core.quantities import convert
from ..workspace import root, component_paths


def _module(name: str, relative: str) -> Any:
    path = root() / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("fixed adapter module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _vector(value: Any, label: str, *, maximum: int = 10_000) -> list[float]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{label} must be a nonempty bounded array")
    return [finite_real(item, label) for item in value]


def invoke(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    paths = component_paths()
    for name in ("research", "computation"):
        sys.path.insert(0, str(paths[name]))
    sys.path.insert(0, str(paths["aspen"] / "src"))
    if capability == "research.route":
        from tsao_researcher.router import route
        return route(_question(payload))
    if capability == "computation.route":
        from tsao_computation.routing.router import route_question
        return dataclasses.asdict(route_question(_question(payload)))
    if capability in {"processing.first_order", "processing.fit_first_order"}:
        model = _module("tsao_fusion_poe_estimation", "components/processing/skills/poe/estimation.py")
        unit = payload.get("time_unit")
        if not isinstance(unit, str):
            raise ValueError("time_unit must be explicit")
        times = [convert({"value": value, "unit": unit}, "s", kind="time")
                 for value in _vector(payload.get("times"), "times")]
        if capability == "processing.first_order":
            rate = convert(payload.get("rate_constant"), "1/s", kind="inverse_time")
            values = model.first_order_conversion(times, rate).tolist()
            return {"times_s": times, "conversion": values, "conversion_unit": "1",
                    "rate_constant_s": rate, "model": "first-order-reference",
                    "status": "CALCULATED_REFERENCE_ONLY"}
        conversion = _vector(payload.get("conversion"), "conversion")
        upper = convert(payload.get("upper_rate"), "1/s", kind="inverse_time")
        return model.fit_first_order_rate(times, conversion, upper_s=upper)
    if capability == "dft.neighbors":
        model = _module("tsao_fusion_neighbors", "components/dft/skills/tsao-structure-prep/scripts/neighbor_list.py")
        coords = payload.get("coordinates")
        if not isinstance(coords, list) or len(coords) > 200:
            raise ValueError("the local geometry adapter allows at most 200 atoms")
        length_unit = payload.get("length_unit")
        if not isinstance(length_unit, str):
            raise ValueError("length_unit must be explicit")
        points = []
        for row in coords:
            if not isinstance(row, list) or len(row) != 3:
                raise ValueError("each coordinate row requires three components")
            points.append([convert({"value": x, "unit": length_unit}, "angstrom", kind="length") for x in row])
        cutoff = convert(payload.get("cutoff"), "angstrom", kind="length")
        result = model.reference_pairs(points, cutoff)
        return {"pairs": [dataclasses.asdict(pair) for pair in result.pairs],
                "evaluated_pairs": result.evaluated_pairs, "neighbor_pairs": len(result.pairs), "backend": result.backend,
                "external_solver_executed": False}
    if capability == "aspen.classify":
        from aspenops_nexus.convergence import classify_convergence, IdleObservation, ConvergenceState
        messages = payload.get("messages")
        if not isinstance(messages, list) or any(not isinstance(x, str) for x in messages):
            raise ValueError("messages must be strings")
        idle = payload.get("engine_idle")
        returned = payload.get("engine_returned")
        if type(idle) is not bool or type(returned) is not bool:
            raise ValueError("engine observations must be explicit booleans")
        evidence = classify_convergence(engine_returned=returned,
            idle=IdleObservation(ConvergenceState.UNKNOWN, idle, 0.0, 1),
            status_nodes=[], messages=messages, source="supplied-text-classification")
        return {**evidence.to_dict(), "external_solver_executed": False,
                "scope": "classifies supplied status text; does not execute or certify Aspen"}
    if capability == "reasoning.validate":
        module = _module("tsao_fusion_ledger", "skills/reasoning/open-deep-mind/scripts/validate_ledger.py")
        ledger = payload.get("ledger")
        if not isinstance(ledger, dict):
            raise ValueError("ledger must be an object")
        errors = module.validate(ledger)
        return {"valid_structure": not errors, "errors": errors,
                "scope": "ledger structure, not truth of premises or scientific approval"}
    if capability == "materials.observation":
        observation = payload.get("observation")
        if not isinstance(observation, dict):
            raise ValueError("observation must be an object")
        required = ("sample_id", "property", "source", "conditions", "quantity", "evidence_kind")
        if any(key not in observation for key in required):
            raise ValueError("observation requires sample, property, source, conditions, quantity and evidence kind")
        if observation["evidence_kind"] not in {"measured", "simulation", "reference", "hypothesis"}:
            raise ValueError("unrecognized evidence kind")
        for key in ("sample_id", "property", "source"):
            if not isinstance(observation[key], str) or not observation[key].strip():
                raise ValueError(f"observation {key} must be nonempty")
        quantity = observation["quantity"]
        if not isinstance(quantity, dict):
            raise ValueError("quantity must be an object")
        convert(quantity, quantity.get("unit"))
        return {"observation": observation, "verified_source": False,
                "scope": "validated supplied metadata; measurement authenticity not inferred"}
    raise ValueError("capability has no authorized local implementation")


def _question(payload: dict[str, Any]) -> str:
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 20_000:
        raise ValueError("question must be a nonempty string of at most 20000 characters")
    return question
