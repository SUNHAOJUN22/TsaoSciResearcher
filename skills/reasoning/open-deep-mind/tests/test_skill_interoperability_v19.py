from __future__ import annotations

import json
import math
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".agents/skills/open-deep-mind"
EVALS = ROOT / "open-deep-mind/evals"


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


class SkillInteroperabilityV19Tests(unittest.TestCase):
    def test_interoperability_contract_is_fail_closed(self) -> None:
        contract = load(SKILL / "references/interoperability-v1.json")
        self.assertEqual(
            contract["schema_version"],
            "tsao-scientific-interoperability/v1",
        )
        self.assertFalse(contract["scientific_quantity"]["boolean_is_numeric"])
        self.assertFalse(contract["scientific_quantity"]["unknown_is_zero"])
        self.assertFalse(
            contract["status_lattice"]["software_pass_implies_external_acceptance"]
        )

    def test_authored_benchmark_is_not_a_published_model_score(self) -> None:
        document = load(EVALS / "evals.json")
        status = load(EVALS / "MODEL_EVAL_STATUS.json")
        cases = document["evals"]
        self.assertEqual(len(cases), 60)
        self.assertEqual(len({case["id"] for case in cases}), 60)
        self.assertEqual(
            Counter(case["split"] for case in cases),
            Counter({"train": 36, "validation": 12, "holdout": 12}),
        )
        self.assertEqual(status["status"], "NOT_RUN")
        self.assertIsNone(status["published_score"])

    def test_nonfinite_or_boolean_quantities_are_invalid(self) -> None:
        for value in (True, False, float("nan"), float("inf"), -float("inf")):
            valid = (
                not isinstance(value, bool)
                and isinstance(value, int | float)
                and math.isfinite(float(value))
            )
            self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()
