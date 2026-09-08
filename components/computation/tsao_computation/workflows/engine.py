from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts import CalculationContract
from ..orchestration import OrchestrationPlan, build_orchestration_plan
from ..registries import workflows
from ..routing import route_question


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    passed: bool
    evidence: str


class WorkflowEngine:
    def select(self, contract: CalculationContract) -> dict[str, Any]:
        slug = contract.workflow or route_question(contract.question).workflow
        for record in workflows():
            if record["slug"] == slug:
                return record
        raise KeyError(f"unknown workflow: {slug}")

    def plan(self, contract: CalculationContract) -> OrchestrationPlan:
        return build_orchestration_plan(contract)

    def initial_gates(self, contract: CalculationContract) -> tuple[GateResult, ...]:
        selected = self.select(contract)
        gaps = contract.specification_gaps()
        return (
            GateResult(
                "contract",
                bool(contract.question and contract.system and contract.target_observables),
                "core calculation-contract fields are present",
            ),
            GateResult(
                "method",
                bool(selected.get("capability_ids")),
                f"workflow={selected['slug']}; capabilities={len(selected.get('capability_ids', []))}",
            ),
            GateResult(
                "environment",
                False,
                "environment, license, data, hardware and invocation targets have not been probed",
            ),
            GateResult(
                "execution",
                False,
                "no authorized invocation record; command or function planning is not execution",
            ),
            GateResult(
                "acceptance",
                False,
                "completed != parsed != converged != validated != accepted; "
                f"preflight_gaps={list(gaps)}",
            ),
        )
