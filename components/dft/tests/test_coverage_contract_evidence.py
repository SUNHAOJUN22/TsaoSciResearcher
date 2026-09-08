from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_coverage.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = load_module("tsao_coverage_contract_evidence_tests", SCRIPT)


def valid_evidence() -> dict[str, object]:
    return {
        "ok": True,
        "state": "EXTERNAL_HOLD",
        "external_engine_invoked": False,
        "performance_ratio_published": False,
    }


class CoverageContractEvidenceTests(unittest.TestCase):
    def test_optional_evidence_is_absent_without_error(self) -> None:
        evidence, errors = runner.load_contract_evidence(None)
        self.assertIsNone(evidence)
        self.assertEqual(errors, [])

    def test_valid_evidence_loads_and_is_embeddable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(valid_evidence()), encoding="utf-8")
            evidence, errors = runner.load_contract_evidence(path)
        self.assertEqual(errors, [])
        self.assertEqual(evidence, valid_evidence())
        payload = runner._failure_payload(["fixture"], evidence)
        self.assertEqual(payload["contract_evidence"], valid_evidence())

    def test_missing_malformed_and_nonmapping_evidence_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, missing = runner.load_contract_evidence(root / "missing.json")
            self.assertTrue(any("could not be loaded" in error for error in missing))

            malformed = root / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            _, malformed_errors = runner.load_contract_evidence(malformed)
            self.assertTrue(any("could not be loaded" in error for error in malformed_errors))

            nonmapping = root / "nonmapping.json"
            nonmapping.write_text("[]", encoding="utf-8")
            _, nonmapping_errors = runner.load_contract_evidence(nonmapping)
            self.assertEqual(nonmapping_errors, ["compute contract evidence root must be a mapping"])

    def test_invalid_or_claiming_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            value = valid_evidence()
            value["ok"] = False
            value["external_engine_invoked"] = True
            value["performance_ratio_published"] = True
            path.write_text(json.dumps(value), encoding="utf-8")
            evidence, errors = runner.load_contract_evidence(path)
        self.assertIsNotNone(evidence)
        self.assertEqual(len(errors), 3)
        self.assertTrue(any("not valid" in error for error in errors))
        self.assertTrue(any("must not invoke" in error for error in errors))
        self.assertTrue(any("must not publish" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
