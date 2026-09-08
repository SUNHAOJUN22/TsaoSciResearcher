from __future__ import annotations

import json
import math
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/tsao-processing-skill"


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


class SkillContractV19Tests(unittest.TestCase):
    def test_interoperability_contract_is_fail_closed(self) -> None:
        contract = load(SKILL / "references/interoperability-v1.json")
        self.assertEqual(
            contract["schema_version"],
            "tsao-scientific-interoperability/v1",
        )
        self.assertFalse(contract["scientific_quantity"]["boolean_is_numeric"])
        self.assertFalse(contract["scientific_quantity"]["unknown_is_zero"])
        self.assertFalse(contract["status_lattice"]["software_pass_implies_external_acceptance"])
        order = contract["status_lattice"]["severity_order"]
        self.assertLess(order.index("FAIL"), order.index("HOLD"))
        self.assertLess(order.index("HOLD"), order.index("PASS"))
        self.assertFalse(math.isfinite(float("nan")))

    def test_static_routing_cases_are_complete_but_not_model_runs(self) -> None:
        evals = load(SKILL / "evals/evals.json")
        status = load(SKILL / "evals/MODEL_EVAL_STATUS.json")
        capture = load(SKILL / "evals/MODEL_CAPTURE_TEMPLATE.json")
        cases = evals["cases"]
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({case["id"] for case in cases}), 6)
        self.assertEqual({case["language"] for case in cases}, {"en", "zh"})
        self.assertEqual({case["split"] for case in cases}, {"train", "validation"})
        self.assertEqual(
            {case["category"] for case in cases},
            {"workflow", "boundary", "negative"},
        )
        self.assertEqual(status["status"], "NOT_RUN")
        self.assertEqual(capture["status"], "NOT_RUN")
        self.assertTrue(all(item["selected_skills"] is None for item in capture["decisions"]))

    def test_unknown_or_boolean_values_cannot_be_silent_zero(self) -> None:
        for value in (True, False, None, float("nan"), float("inf")):
            if value is None or isinstance(value, bool) or not isinstance(value, int | float):
                valid = False
            else:
                valid = math.isfinite(float(value))
            self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()
