from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_agent_evals.py"
    spec = importlib.util.spec_from_file_location("tsao_agent_eval_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentEvalContractTests(unittest.TestCase):
    def setUp(self):
        self.validator = load_validator()
        self.source = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8"))

    def validate_fixture(self, data: dict) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cases.yaml"
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            return self.validator.validate(path)

    def test_current_eval_contract(self):
        self.assertEqual(self.validator.validate(), [])

    def test_duplicate_identifier_fails(self):
        data = dict(self.source)
        data["cases"] = [dict(case) for case in self.source["cases"]]
        data["cases"][1]["id"] = data["cases"][0]["id"]
        failures = self.validate_fixture(data)
        self.assertTrue(any("duplicate eval id" in item for item in failures), failures)

    def test_missing_category_fails(self):
        data = dict(self.source)
        data["cases"] = [case for case in self.source["cases"] if case["category"] != "prompt_injection"]
        failures = self.validate_fixture(data)
        self.assertTrue(any("prompt_injection" in item for item in failures), failures)

    def test_live_model_execution_cannot_be_claimed_without_traces(self):
        data = dict(self.source)
        data["live_model_execution"] = "PASS"
        failures = self.validate_fixture(data)
        self.assertTrue(any("NOT_VERIFIED" in item for item in failures), failures)

    def test_destructive_eval_requires_ownership(self):
        data = dict(self.source)
        data["cases"] = [dict(case) for case in self.source["cases"]]
        for case in data["cases"]:
            if case["category"] == "destructive_action":
                case["expected_behavior"] = ["refuse unsafe behavior"]
                case["forbidden_behavior"] = ["delete files"]
                case["failure_evidence"] = "record deletion"
                case["grader"] = {"type": "policy_assertions", "require": ["refusal"], "forbid": ["delete"]}
        failures = self.validate_fixture(data)
        self.assertIn("destructive_action eval must require ownership evidence", failures)


if __name__ == "__main__":
    unittest.main()
