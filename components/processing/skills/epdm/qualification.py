from __future__ import annotations

from typing import Any

from .kinetics import (
    EpdmKineticParameters,
    EpdmKineticState,
    active_site_fraction,
    architecture_metrics,
)
from .process import heat_removal_margin, recycle_poison_steady_state

_RECOGNIZED_DIENES = {"ENB", "DCPD", "VNB"}
_ALLOWED_CASE_KINDS = {"SYNTHETIC_REFERENCE_TEST", "PROJECT_CASE"}
_ALLOWED_PARAMETER_BASES = {
    "SYNTHETIC_REFERENCE_TEST",
    "LITERATURE_PRIOR",
    "LAB_FIT",
    "PILOT_FIT",
    "PLANT_FIT",
}
_ALLOWED_REACTOR_MODES = {"CONTINUOUS", "SEMIBATCH", "BATCH"}
_ALLOWED_ACTIVE_SITE_BASES = {
    "FIXED_CONCENTRATION_REFERENCE",
    "EXTENSIVE_SITE_BALANCE",
}
_SYNTHETIC_CASE_KIND = "SYNTHETIC_REFERENCE_TEST"


def _object_section(
    case: dict[str, Any],
    name: str,
    errors: list[str],
    *,
    required: bool = True,
) -> dict[str, Any] | None:
    value = case.get(name)
    if value is None and not required:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return None
    return value


def _valid_evidence_ids(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return False
        normalized.append(item.strip())
    return len(normalized) == len(set(normalized))


def _require_evidence(payload: dict[str, Any], field: str, message: str, holds: list[str]) -> None:
    if not _valid_evidence_ids(payload.get(field)):
        holds.append(message)


def _validate_case_kind(case: dict[str, Any], errors: list[str], holds: list[str]) -> None:
    case_kind = case.get("case_kind")
    if case_kind is None:
        holds.append(
            "case_kind is missing; software-fixture and project evidence boundaries are unresolved"
        )
    elif not isinstance(case_kind, str) or case_kind not in _ALLOWED_CASE_KINDS:
        errors.append("case_kind must be SYNTHETIC_REFERENCE_TEST or PROJECT_CASE")


def _validate_parameter_provenance(
    case: dict[str, Any], kinetic: dict[str, Any], holds: list[str]
) -> None:
    basis = kinetic.get("parameter_basis")
    if not isinstance(basis, str) or basis not in _ALLOWED_PARAMETER_BASES:
        holds.append("kinetic parameter basis is missing or outside the recognized reference set")
    elif basis == "SYNTHETIC_REFERENCE_TEST" and case.get("case_kind") != _SYNTHETIC_CASE_KIND:
        holds.append(
            "synthetic reference parameters are only valid for a declared software fixture"
        )
    if not _valid_evidence_ids(kinetic.get("parameter_evidence_ids")):
        holds.append("kinetic parameters are not anchored to evidence")


def _validate_semibatch_basis(reactor: dict[str, Any], holds: list[str]) -> None:
    mode = reactor.get("mode")
    if mode is None:
        holds.append("reactor.mode is missing")
        return
    if mode not in _ALLOWED_REACTOR_MODES or mode != "SEMIBATCH":
        return
    basis = reactor.get("active_site_basis")
    if basis not in _ALLOWED_ACTIVE_SITE_BASES:
        holds.append("semibatch active-site basis is missing or unrecognized")
    elif basis == "FIXED_CONCENTRATION_REFERENCE":
        holds.append(
            "semibatch fixed active-site concentration is a V1 reference assumption, "
            "not an extensive site balance"
        )
    elif not _valid_evidence_ids(reactor.get("active_site_balance_evidence_ids")):
        holds.append("semibatch extensive active-site balance is not anchored to evidence")


def _base_result(
    *,
    status: str,
    errors: list[str],
    holds: list[str],
    metrics: dict[str, Any],
    internal_error: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "pass": status == "PASS",
        "errors": sorted(set(errors)),
        "holds": sorted(set(holds)),
        "metrics": metrics,
        "internal_error": internal_error,
        "evidence_resolution": "DECLARED_ONLY_CASE_LEVEL",
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
        "customer_qualification": "NOT_EVALUATED",
    }


def _validate_epdm_case(case: object) -> dict[str, Any]:
    errors: list[str] = []
    holds: list[str] = []
    metrics: dict[str, Any] = {}
    if not isinstance(case, dict):
        return _base_result(
            status="FAIL",
            errors=["EPDM case root must be an object"],
            holds=[],
            metrics={},
        )

    _validate_case_kind(case, errors, holds)
    catalyst = _object_section(case, "catalyst", errors)
    monomers = _object_section(case, "monomers", errors)
    kinetic = _object_section(case, "kinetics", errors)
    reactor = _object_section(case, "reactor", errors)
    recovery = _object_section(case, "recovery", errors)
    product_bridge = _object_section(case, "product_bridge", errors)
    impurities = _object_section(case, "impurities", errors, required=False)

    if catalyst is not None:
        family = catalyst.get("family")
        if not isinstance(family, str) or not family.strip():
            errors.append("catalyst.family is required")
        benchmark = catalyst.get("vanadium_benchmark")
        retirement = catalyst.get("benchmark_retirement")
        if benchmark is True:
            _require_evidence(
                catalyst,
                "vanadium_benchmark_evidence_ids",
                "vanadium benchmark declaration is not anchored to evidence",
                holds,
            )
        elif not (
            isinstance(retirement, dict)
            and retirement.get("status") == "APPROVED"
            and isinstance(retirement.get("approver"), str)
            and retirement.get("approver", "").strip()
            and _valid_evidence_ids(retirement.get("evidence_ids"))
        ):
            holds.append("vanadium industrial benchmark is missing or not formally retired")
        try:
            metrics["active_site_fraction"] = active_site_fraction(
                catalyst.get("total_metal_mol"), catalyst.get("active_site_mol")
            )
        except ValueError as exc:
            errors.append(str(exc))
        _require_evidence(
            catalyst,
            "active_site_evidence_ids",
            "active-site concentration is not anchored to evidence",
            holds,
        )

    if monomers is not None:
        diene = monomers.get("diene")
        if diene not in _RECOGNIZED_DIENES:
            holds.append("diene identity is outside the qualified ENB/DCPD/VNB reference set")
        for field in ("ethylene_mol_L", "propylene_mol_L", "diene_mol_L"):
            value = monomers.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                errors.append(f"monomers.{field} must be non-negative numeric")
        if monomers.get("diene_topology_measured") is not True:
            holds.append("diene topology or retained-unsaturation measurement is missing")
        else:
            _require_evidence(
                monomers,
                "diene_topology_evidence_ids",
                "diene topology measurement is not anchored to evidence",
                holds,
            )

    reactor_volume: float | None = None
    if reactor is not None:
        mode = reactor.get("mode")
        if mode is not None and mode not in _ALLOWED_REACTOR_MODES:
            errors.append("reactor.mode must be CONTINUOUS, SEMIBATCH, or BATCH")
        _validate_semibatch_basis(reactor, holds)
        volume = reactor.get("volume_L")
        if isinstance(volume, bool) or not isinstance(volume, (int, float)) or volume <= 0:
            errors.append("reactor.volume_L must be positive numeric")
        else:
            reactor_volume = float(volume)
        try:
            margin = heat_removal_margin(
                reactor.get("heat_generation_kW"), reactor.get("heat_removal_capacity_kW")
            )
            metrics["heat_removal_margin"] = margin
            if margin < 0:
                errors.append("reactor heat removal capacity is below heat generation")
            elif margin < 0.15:
                holds.append("reactor heat-removal margin is below the 15% reference Gate")
        except ValueError as exc:
            errors.append(str(exc))
        if reactor.get("phase_stable") is not True:
            holds.append("polymer-solution phase stability is not demonstrated")
        else:
            _require_evidence(
                reactor,
                "phase_stability_evidence_ids",
                "phase-stability declaration is not anchored to evidence",
                holds,
            )
        if reactor.get("mixing_qualified") is not True:
            holds.append("high-viscosity mixing is not qualified")
        else:
            _require_evidence(
                reactor,
                "mixing_evidence_ids",
                "mixing qualification is not anchored to evidence",
                holds,
            )

    if kinetic is not None:
        _validate_parameter_provenance(case, kinetic, holds)
        parameters_payload = kinetic.get("parameters")
        if not isinstance(parameters_payload, dict):
            errors.append("kinetics.parameters must be an object")
        elif (
            catalyst is not None
            and monomers is not None
            and impurities is not None
            and reactor_volume is not None
        ):
            try:
                state = EpdmKineticState(
                    monomers["ethylene_mol_L"],
                    monomers["propylene_mol_L"],
                    monomers["diene_mol_L"],
                    catalyst["active_site_mol"] / reactor_volume,
                    float(impurities.get("poison_mol_L", 0.0)),
                )
                parameters = EpdmKineticParameters(**parameters_payload)
                metrics["architecture"] = architecture_metrics(
                    state,
                    parameters,
                    secondary_diene_insertion_probability=kinetic.get(
                        "secondary_diene_insertion_probability", 0.0
                    ),
                    branch_efficiency=kinetic.get("branch_efficiency", 0.0),
                    gel_critical_branch_index=kinetic.get("gel_critical_branch_index", 1.0),
                )
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"invalid kinetic/architecture case: {exc}")

    if recovery is not None:
        try:
            poison = recycle_poison_steady_state(
                recovery.get("fresh_poison_mol_h"),
                recovery.get("recycle_fraction"),
                recovery.get("purge_fraction"),
                recovery.get("guard_removal_fraction"),
            )
            metrics["steady_poison_mol_h"] = poison
            maximum = recovery.get("max_poison_mol_h")
            if isinstance(maximum, bool) or not isinstance(maximum, (int, float)) or maximum < 0:
                errors.append("recovery.max_poison_mol_h must be non-negative numeric")
            elif poison > float(maximum):
                errors.append("recycle poison steady state exceeds the declared limit")
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid recovery/poison case: {exc}")
        if recovery.get("non_equilibrium_devolatilization") is not True:
            holds.append(
                "devolatilization is represented without a qualified non-equilibrium basis"
            )
        else:
            _require_evidence(
                recovery,
                "devolatilization_evidence_ids",
                "non-equilibrium devolatilization declaration is not anchored to evidence",
                holds,
            )

    if product_bridge is not None:
        stages = (
            "raw_polymer",
            "fixed_compound",
            "cure",
            "part_durability",
            "customer_line",
        )
        for stage in stages:
            record = product_bridge.get(stage)
            if (
                not isinstance(record, dict)
                or record.get("status") != "PASS"
                or not _valid_evidence_ids(record.get("evidence_ids"))
            ):
                holds.append(f"product bridge stage is not qualified: {stage}")

    status = "FAIL" if errors else "HOLD" if holds else "PASS"
    return _base_result(status=status, errors=errors, holds=holds, metrics=metrics)


def validate_epdm_case(case: object) -> dict[str, Any]:
    """Fail closed for malformed EPDM payloads without leaking internal exceptions."""
    try:
        return _validate_epdm_case(case)
    except Exception as exc:  # defensive boundary; expected malformed paths are tested
        return _base_result(
            status="FAIL",
            errors=[f"unexpected EPDM validation failure: {type(exc).__name__}"],
            holds=[],
            metrics={},
            internal_error=True,
        )
