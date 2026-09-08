from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .contracts import (
    GateDecision,
    GateResult,
    ModelGeneration,
    ModelQualification,
    QualificationLayer,
    QualificationStatus,
)

_PRECEDENCE = {
    GateDecision.PASS: 0,
    GateDecision.NOT_EVALUATED: 1,
    GateDecision.HOLD: 2,
    GateDecision.FAIL: 3,
}


def aggregate_gate_results(gates: Iterable[GateResult]) -> QualificationStatus:
    applicable = [gate for gate in gates if gate.applicable and gate.mandatory]
    if not applicable:
        return QualificationStatus.NOT_EVALUATED
    decision = max((gate.decision for gate in applicable), key=_PRECEDENCE.__getitem__)
    return QualificationStatus(decision.value)


def derive_model_qualification(
    gate_results: Iterable[GateResult],
    *,
    model_generation: ModelGeneration = ModelGeneration.V2_TERMINAL_MOMENT,
) -> ModelQualification:
    gates = tuple(gate_results)
    by_layer: dict[QualificationLayer, list[GateResult]] = defaultdict(list)
    for gate in gates:
        by_layer[gate.layer].append(gate)
    return ModelQualification(
        software_status=aggregate_gate_results(by_layer[QualificationLayer.SOFTWARE]),
        thermodynamic_status=aggregate_gate_results(by_layer[QualificationLayer.THERMODYNAMIC]),
        kinetic_calibration_status=aggregate_gate_results(
            by_layer[QualificationLayer.KINETIC_CALIBRATION]
        ),
        independent_validation_status=aggregate_gate_results(
            by_layer[QualificationLayer.INDEPENDENT_VALIDATION]
        ),
        engineering_use_status=aggregate_gate_results(by_layer[QualificationLayer.ENGINEERING_USE]),
        gate_results=gates,
        model_generation=model_generation,
    )
