from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"catalysis_fail_closed_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CatalysisValidationFailClosedTests(unittest.TestCase):
    claim: Any
    profile_validator: Any
    claim_data: dict[str, Any]
    profile: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.claim = load_script("validate_claim_scope.py")
        cls.profile_validator = load_script("validate_profile.py")
        cls.claim_data = yaml.safe_load((ROOT / "templates/claim-scope.yaml").read_text(encoding="utf-8"))
        cls.profile = yaml.safe_load((ROOT / "templates/profile.yaml").read_text(encoding="utf-8"))

    def test_valid_templates_and_root_paths(self) -> None:
        self.assertEqual(self.claim.validate(copy.deepcopy(self.claim_data))[0], [])
        self.assertEqual(self.profile_validator.validate(copy.deepcopy(self.profile))[0], [])
        self.assertIn("root must be a mapping", " ".join(self.claim.validate([])[0]))
        self.assertIn("root must be a mapping", " ".join(self.profile_validator.validate([])[0]))

    def test_claim_rejects_collection_types_and_strong_accepted_claims(self) -> None:
        data = copy.deepcopy(self.claim_data)
        data["claim_id"] = ""
        data["text"] = []
        data["system_scope"] = None
        data["evidence"] = {"accepted_dft": True}
        data["limitations"] = "none"
        data["claim_level"] = "industrial_performance"
        data["status"] = "accepted"
        errors, warnings = self.claim.validate(data)
        rendered = " ".join(errors)
        self.assertIn("claim_id must be a non-empty string", rendered)
        self.assertIn("text must be a non-empty string", rendered)
        self.assertIn("system_scope must be a non-empty string", rendered)
        self.assertIn("evidence must be a list", rendered)
        self.assertIn("limitations must be a list", rendered)
        self.assertIn("industrial_performance missing evidence", rendered)
        self.assertIn("accepted claim", rendered)
        self.assertTrue(warnings)

    def test_profile_rejects_wrong_lists_dependencies_and_status(self) -> None:
        data = copy.deepcopy(self.profile)
        data["profile_id"] = ""
        data["scope"] = []
        data["allowed_systems"] = "bad"
        data["activation_terms"] = []
        data["forbidden_default_claims"] = [""]
        data["requires"] = ["tsao-dft-suite"]
        data["dft_center"] = 1
        data["status"] = "accepted"
        errors, warnings = self.profile_validator.validate(data)
        rendered = " ".join(errors)
        self.assertIn("profile_id must be a non-empty string", rendered)
        self.assertIn("scope must be a non-empty string", rendered)
        self.assertIn("allowed_systems must be a list", rendered)
        self.assertIn("activation_terms must not be empty", rendered)
        self.assertIn("forbidden_default_claims must contain non-empty strings", rendered)
        self.assertIn("required Skill missing", rendered)
        self.assertIn("dft_center", rendered)
        self.assertIn("accepted profile", rendered)
        self.assertTrue(warnings)

    def test_malformed_yaml_is_structured_failure(self) -> None:
        scripts = ("validate_claim_scope.py", "validate_profile.py")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.yaml"
            path.write_text("evidence: [\n", encoding="utf-8")
            for script in scripts:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / script), str(path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertFalse(report["ok"])
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
