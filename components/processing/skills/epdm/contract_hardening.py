from __future__ import annotations

import math
import types
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import StrEnum
from functools import wraps
from typing import Any, Union, get_args, get_origin, get_type_hints

from . import _contracts_core as _c


def _fail(message: str) -> None:
    raise _c.ContractValidationError(message)


def _is_union(origin: object) -> bool:
    return origin in {Union, types.UnionType}


def _coerce(value: object, annotation: object, label: str) -> object:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if _is_union(origin):
        if value is None and type(None) in args:
            return None
        candidates = tuple(item for item in args if item is not type(None))
        errors: list[Exception] = []
        for candidate in candidates:
            try:
                return _coerce(value, candidate, label)
            except _c.ContractValidationError as exc:
                errors.append(exc)
        if errors:
            raise errors[-1]
        return value

    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        try:
            return annotation(value)
        except (TypeError, ValueError) as exc:
            allowed = [item.value for item in annotation]
            raise _c.ContractValidationError(f"{label} must be one of {allowed}") from exc

    if annotation is bool:
        if type(value) is not bool:
            _fail(f"{label} must be boolean")
        return value
    if annotation is int:
        if isinstance(value, bool) or not isinstance(value, int):
            _fail(f"{label} must be integer")
        return value
    if annotation is float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            _fail(f"{label} must be finite numeric")
        return float(value)
    if annotation is str:
        if not isinstance(value, str):
            _fail(f"{label} must be string")
        return value

    if origin is tuple:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            _fail(f"{label} must be a sequence")
        item_type = args[0] if args else object
        normalized = tuple(_coerce(item, item_type, label) for item in value)
        return normalized

    if origin in {dict, Mapping} or origin is Mapping:
        if not isinstance(value, Mapping):
            _fail(f"{label} must be a mapping")
        key_type, value_type = args if len(args) == 2 else (object, object)
        return {
            _coerce(key, key_type, f"{label} key"): _coerce(item, value_type, f"{label} value")
            for key, item in value.items()
        }

    if annotation is Any or annotation is object:
        return value
    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, annotation):
            _fail(f"{label} must be {annotation.__name__}")
        return value
    return value


def _prevalidate(instance: object) -> None:
    hints = get_type_hints(type(instance))
    for item in fields(instance):
        annotation = hints.get(item.name)
        if annotation is None:
            continue
        normalized = _coerce(getattr(instance, item.name), annotation, item.name)
        if normalized is not getattr(instance, item.name):
            object.__setattr__(instance, item.name, normalized)


def _custom(instance: object) -> None:
    if isinstance(instance, _c.QuantityValue):
        if instance.basis is not None and not instance.basis.strip():
            _fail("basis must be a non-empty string")
        if instance.standard_uncertainty is not None and instance.uncertainty_unit is not None:
            if (
                _c.SI_UNIT_DIMENSIONS[instance.uncertainty_unit]
                != _c.SI_UNIT_DIMENSIONS[instance.unit]
            ):
                _fail("uncertainty_unit must have the same dimension as unit")

    elif isinstance(instance, _c.KineticParameter):
        if instance.confidence_interval_95 is not None:
            low, high = instance.confidence_interval_95
            if not low <= instance.value <= high:
                _fail("confidence_interval_95 must contain parameter value")

    elif isinstance(instance, _c.ApplicabilityDomain):
        if instance.hydrogen_ratio[0] < 0:
            _fail("hydrogen_ratio bounds must be non-negative")
        if len(instance.reactor_types) != len(set(instance.reactor_types)):
            _fail("reactor_types must contain unique values")

    elif isinstance(instance, _c.ThermoPassport):
        if instance.simulator_version is not None and not instance.simulator_version.strip():
            _fail("simulator_version must be a non-empty string")

    elif isinstance(instance, _c.KineticDataset):
        for target in instance.targets:
            if target.dataset_id != instance.dataset_id:
                _fail("target dataset_id must match parent dataset")
            if target.use != instance.role:
                _fail("target use must match dataset role")

    elif isinstance(instance, _c.CalibrationPlan):
        for binding in instance.parameter_bindings:
            if (
                binding.scope == _c.ParameterScope.GRADE_CORRECTION
                and not instance.allow_grade_specific_parameters
            ):
                _fail("grade-specific binding is disabled by the calibration plan")
            if (
                binding.scope == _c.ParameterScope.REACTOR_CORRECTION
                and not instance.allow_reactor_specific_parameters
            ):
                _fail("reactor-specific binding is disabled by the calibration plan")

    elif isinstance(instance, _c.GateResult):
        if instance.applicable and instance.decision == _c.GateDecision.NOT_APPLICABLE:
            _fail("applicable gate cannot be NOT_APPLICABLE")
        if not instance.applicable and instance.decision != _c.GateDecision.NOT_APPLICABLE:
            _fail("non-applicable gate must be NOT_APPLICABLE")
        if not instance.applicable and instance.mandatory:
            _fail("non-applicable gate cannot be mandatory")
        if (
            instance.decision == _c.GateDecision.PASS
            and instance.reason_code != _c.GateReasonCode.NONE
        ):
            _fail("PASS gate must use reason code NONE")
        if (
            instance.decision in {_c.GateDecision.HOLD, _c.GateDecision.FAIL}
            and instance.reason_code == _c.GateReasonCode.NONE
        ):
            _fail("HOLD/FAIL gate requires a reason code")
        if (
            instance.decision in {_c.GateDecision.NOT_EVALUATED, _c.GateDecision.NOT_APPLICABLE}
            and instance.reason_code != _c.GateReasonCode.NONE
        ):
            _fail(f"{instance.decision.value} gate must use reason code NONE")

    elif isinstance(instance, _c.ModelQualification):
        gate_ids = [gate.gate_id for gate in instance.gate_results]
        if len(gate_ids) != len(set(gate_ids)):
            _fail("gate_results must use unique gate IDs")
        status_fields = (
            ("software_status", _c.QualificationLayer.SOFTWARE),
            ("thermodynamic_status", _c.QualificationLayer.THERMODYNAMIC),
            ("kinetic_calibration_status", _c.QualificationLayer.KINETIC_CALIBRATION),
            ("independent_validation_status", _c.QualificationLayer.INDEPENDENT_VALIDATION),
            ("engineering_use_status", _c.QualificationLayer.ENGINEERING_USE),
        )
        precedence = {
            _c.GateDecision.PASS: 0,
            _c.GateDecision.NOT_EVALUATED: 1,
            _c.GateDecision.HOLD: 2,
            _c.GateDecision.FAIL: 3,
        }
        for field_name, layer in status_fields:
            gates = [
                gate
                for gate in instance.gate_results
                if gate.layer == layer and gate.applicable and gate.mandatory
            ]
            expected = _c.QualificationStatus.NOT_EVALUATED
            if gates:
                decision = max((gate.decision for gate in gates), key=precedence.__getitem__)
                expected = _c.QualificationStatus(decision.value)
            actual = getattr(instance, field_name)
            if actual != expected:
                _fail(
                    f"{field_name} must match mandatory applicable gate results: "
                    f"expected {expected.value}, got {actual.value}"
                )
        ordered = [getattr(instance, name) for name, _ in status_fields]
        for index, status in enumerate(ordered):
            if status == _c.QualificationStatus.PASS and any(
                upstream != _c.QualificationStatus.PASS for upstream in ordered[:index]
            ):
                _fail("downstream PASS requires every upstream qualification layer to PASS")


def harden_contracts(module: object = _c) -> None:
    if module is not _c:
        raise RuntimeError("contract hardening must target the EPDM contract core")
    for value in vars(_c).values():
        if not isinstance(value, type) or not is_dataclass(value):
            continue
        original = getattr(value, "__post_init__", None)
        if original is None:
            original_init = value.__init__
            if getattr(original_init, "__tsao_hardened__", False):
                continue

            @wraps(original_init)
            def hardened_init(
                self: object, *args: Any, _original: Any = original_init, **kwargs: Any
            ) -> None:
                _original(self, *args, **kwargs)
                _prevalidate(self)
                _custom(self)

            hardened_init.__tsao_hardened__ = True  # type: ignore[attr-defined]
            value.__init__ = hardened_init
            continue
        if getattr(original, "__tsao_hardened__", False):
            continue

        @wraps(original)
        def hardened(self: object, _original: Any = original) -> None:
            _prevalidate(self)
            try:
                _original(self)
            except _c.ContractValidationError:
                raise
            except (AttributeError, TypeError, ValueError) as exc:
                raise _c.ContractValidationError(
                    f"{type(self).__name__} contract input is invalid: {exc}"
                ) from exc
            _custom(self)

        hardened.__tsao_hardened__ = True  # type: ignore[attr-defined]
        value.__post_init__ = hardened
