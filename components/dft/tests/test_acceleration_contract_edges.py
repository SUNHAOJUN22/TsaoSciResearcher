from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_acceleration_contracts.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_acceleration_contract_edges", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


contracts = load_module()


class AccelerationContractEdgeTests(unittest.TestCase):
    def test_json_and_yaml_loaders_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = {
                "missing.json": None,
                "malformed.json": "{",
                "list.json": "[]",
            }
            for name, content in cases.items():
                path = root / name
                if content is not None:
                    path.write_text(content, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(contracts.ContractLoadError):
                    contracts.load_json_mapping(path)

            malformed_yaml = root / "malformed.yaml"
            malformed_yaml.write_text("value: [", encoding="utf-8")
            with self.assertRaises(contracts.ContractLoadError):
                contracts.load_yaml_mapping(malformed_yaml)

            scalar_yaml = root / "scalar.yaml"
            scalar_yaml.write_text("value", encoding="utf-8")
            with self.assertRaisesRegex(contracts.ContractLoadError, "root must be a mapping"):
                contracts.load_yaml_mapping(scalar_yaml)

    def test_schema_contract_reports_every_structural_gate(self) -> None:
        current = contracts.load_json_mapping(contracts.DEFAULT_SCHEMA)

        invalid_meta = {"type": 7}
        failures = contracts.validate_schema_contract(invalid_meta)
        self.assertTrue(any("not a valid Draft 2020-12 schema" in failure for failure in failures))

        malformed = copy.deepcopy(current)
        malformed["type"] = "array"
        malformed["additionalProperties"] = True
        malformed["required"] = []
        failures = contracts.validate_schema_contract(malformed)
        self.assertIn("benchmark result schema root type must be object", failures)
        self.assertIn("benchmark result schema must reject unknown top-level fields", failures)
        self.assertTrue(any("missing required fields" in failure for failure in failures))

        malformed = copy.deepcopy(current)
        malformed["properties"]["wall_time_seconds"] = {"type": "number", "minimum": 0}
        malformed["properties"]["timestamp"] = {"type": "string"}
        malformed["properties"]["evidence_source"] = {"enum": ["simulation"]}
        malformed["$defs"]["sha256"] = {"type": "string", "pattern": "x"}
        del malformed["allOf"]
        failures = contracts.validate_schema_contract(malformed)
        self.assertIn("wall_time_seconds must be strictly positive", failures)
        self.assertIn("timestamp must use JSON Schema date-time format", failures)
        self.assertIn("benchmark result schema must admit real-engine-observation evidence", failures)
        self.assertIn("SHA-256 values must be lowercase 64-character hexadecimal strings", failures)
        self.assertIn(
            "benchmark result schema must conditionally require complete accepted-run evidence",
            failures,
        )

        malformed = copy.deepcopy(current)
        malformed["properties"] = []
        with patch.object(contracts.Draft202012Validator, "check_schema", return_value=None):
            failures = contracts.validate_schema_contract(malformed)
        self.assertIn("benchmark result schema properties must be a mapping", failures)

    def test_policy_contract_reports_every_gate(self) -> None:
        current = contracts.load_yaml_mapping(contracts.DEFAULT_POLICY)

        malformed = copy.deepcopy(current)
        malformed["schema_version"] = 1
        malformed["qualification"] = "wrong"
        malformed["minimum_repeats"] = True
        malformed["requirements"] = {}
        malformed["failure_states"] = ["L2_ONLY", "L2_ONLY"]
        malformed["qualified_state"] = "wrong"
        malformed["public_capability_change"] = True
        failures = contracts.validate_policy_contract(malformed)
        self.assertIn("performance qualification policy schema_version must be '1.0'", failures)
        self.assertIn("performance qualification policy has the wrong qualification identifier", failures)
        self.assertIn("performance qualification minimum_repeats must be an integer >= 3", failures)
        self.assertIn("performance qualification requirements do not match the executable L3 contract", failures)
        self.assertIn("performance qualification failure_states must be a unique list", failures)
        self.assertIn("performance qualification qualified_state is invalid", failures)
        self.assertIn("scoped L3 qualification must not automatically change public capability", failures)

        malformed = copy.deepcopy(current)
        malformed["failure_states"] = ["L2_ONLY"]
        self.assertIn(
            "performance qualification failure_states are incomplete",
            contracts.validate_policy_contract(malformed),
        )

    def test_nested_nonfinite_and_nonmapping_results_are_rejected(self) -> None:
        failures = contracts._nonfinite_paths(
            {
                "scalar": float("inf"),
                "nested": [1.0, {"value": float("-inf")}, float("nan")],
            }
        )
        self.assertEqual(len(failures), 3)
        self.assertTrue(any("<root>.scalar" in failure for failure in failures))
        self.assertTrue(any("<root>.nested[1].value" in failure for failure in failures))
        self.assertTrue(any("<root>.nested[2]" in failure for failure in failures))

        schema = contracts.load_json_mapping(contracts.DEFAULT_SCHEMA)
        self.assertEqual(
            contracts.validate_result_document([], schema),
            ["benchmark result root must be a mapping"],
        )

    def test_validate_contracts_and_text_cli_failure_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            malformed_result = root / "result.json"
            malformed_result.write_text("[]", encoding="utf-8")
            failures = contracts.validate_contracts(result_path=malformed_result)
            self.assertTrue(any("JSON contract root must be a mapping" in failure for failure in failures))

            bad_policy = root / "policy.yaml"
            bad_policy.write_text(yaml.safe_dump({"schema_version": "0"}), encoding="utf-8")
            failures = contracts.validate_contracts(policy_path=bad_policy)
            self.assertTrue(failures)

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--policy", str(bad_policy)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("FAIL:", completed.stdout)
            self.assertIn("Acceleration evidence contract validation: FAIL", completed.stdout)

            completed = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("Acceleration evidence contract validation: PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
