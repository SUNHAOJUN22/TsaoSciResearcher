from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/tsao-sci-researcher"


def load(path: Path) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> Any:
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=constant,
    )


def test_interoperability_contract_is_fail_closed() -> None:
    contract = load(SKILL / "references/interoperability-v1.json")
    assert contract["schema_version"] == "tsao-scientific-interoperability/v1"
    assert contract["scientific_quantity"]["boolean_is_numeric"] is False
    assert contract["scientific_quantity"]["unknown_is_zero"] is False
    assert contract["status_lattice"]["software_pass_implies_external_acceptance"] is False
    order = contract["status_lattice"]["severity_order"]
    assert order.index("FAIL") < order.index("HOLD") < order.index("PASS")


def test_interoperability_contract_stays_in_full_ci_without_a_status_workflow() -> None:
    assert (ROOT / ".github/workflows/ci.yml").is_file()
    assert not (ROOT / ".github/workflows/v19-skill-contract.yml").exists()


def test_static_routing_cases_are_complete_but_not_model_runs() -> None:
    evals = load(SKILL / "evals/evals.json")
    status = load(SKILL / "evals/MODEL_EVAL_STATUS.json")
    capture = load(SKILL / "evals/MODEL_CAPTURE_TEMPLATE.json")
    cases = evals["cases"]
    assert len(cases) == 6
    assert len({case["id"] for case in cases}) == 6
    assert {case["language"] for case in cases} == {"en", "zh"}
    assert {case["split"] for case in cases} == {"train", "validation"}
    assert {case["category"] for case in cases} == {
        "workflow",
        "boundary",
        "negative",
    }
    assert status["status"] == "NOT_RUN"
    assert capture["status"] == "NOT_RUN"
    assert all(item["selected_skills"] is None for item in capture["decisions"])


def test_nonfinite_or_boolean_quantities_are_invalid() -> None:
    for value in (True, False, float("nan"), float("inf"), -float("inf")):
        valid = not isinstance(value, bool) and isinstance(value, int | float) and math.isfinite(float(value))
        assert valid is False
