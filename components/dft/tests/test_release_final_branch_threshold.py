from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(relative: str, name: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseFinalBranchThresholdTests(unittest.TestCase):
    packaging: Any
    fingerprint: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.packaging = load_script("scripts/validate_packaging_model.py", "release_final_packaging")
        cls.fingerprint = load_script(
            "skills/tsao-dft-suite/scripts/validate_method_fingerprint.py",
            "release_final_fingerprint",
        )

    def test_packaging_model_success_failure_and_cli_branches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertTrue(self.packaging.validate(root))

            (root / "docs").mkdir()
            (root / "scripts").mkdir()
            (root / "docs" / "PACKAGING_MODEL.md").write_text("model\n", encoding="utf-8")
            (root / "scripts" / "install.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                '[tool.tsao-dft]\npackaging-model = "repository-skill-suite"\n',
                encoding="utf-8",
            )
            self.assertEqual(self.packaging.validate(root), [])

            (root / "pyproject.toml").write_text(
                '[build-system]\nrequires = []\n[tool.tsao-dft]\npackaging-model = "wheel"\n',
                encoding="utf-8",
            )
            failures = self.packaging.validate(root)
            self.assertTrue(any("build-system" in item for item in failures))
            self.assertTrue(any("repository-skill-suite" in item for item in failures))

        with (
            patch.object(sys, "argv", ["validate_packaging_model.py", "--json"]),
            patch.object(self.packaging, "validate", return_value=[]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.packaging.main(), 0)
        with (
            patch.object(sys, "argv", ["validate_packaging_model.py"]),
            patch.object(self.packaging, "validate", return_value=["bad"]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.packaging.main(), 1)

    def molecular_fingerprint(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "method_fingerprint_id": "MF-1",
            "domain": "molecular",
            "engine": "gaussian",
            "engine_version": "16",
            "model_chemistry": {
                "method": "PBE0",
                "basis_or_pseudopotential": "def2-SVP",
                "solvent_or_electrostatics": "gas",
            },
            "numerics": {},
            "spin_charge": {"charge": 0, "multiplicity_or_magnetism": 1},
            "standard_state": {"temperature_K": 298.15},
            "provenance": {"source": "fixture"},
            "status": "draft",
        }

    def test_method_fingerprint_domain_temperature_acceptance_and_cli_branches(self) -> None:
        errors, _ = self.fingerprint.validate({})
        self.assertGreaterEqual(len(errors), 13)

        clean = self.molecular_fingerprint()
        self.assertEqual(self.fingerprint.validate(clean), ([], []))

        molecular = self.molecular_fingerprint()
        molecular["model_chemistry"] = {}
        molecular["spin_charge"] = {}
        molecular["standard_state"] = {"temperature_K": 0}
        molecular["status"] = "accepted"
        errors, warnings = self.fingerprint.validate(molecular)
        self.assertTrue(any("charge" in item for item in errors))
        self.assertTrue(any("multiplicity" in item for item in errors))
        self.assertTrue(any("positive" in item for item in errors))
        self.assertTrue(any("accepted fingerprint" in item for item in errors))
        self.assertEqual(len(warnings), 3)

        periodic = self.molecular_fingerprint()
        periodic["domain"] = "periodic"
        periodic["engine"] = "vasp"
        periodic["model_chemistry"] = {}
        periodic["numerics"] = {}
        periodic["standard_state"] = {"temperature_K": "bad"}
        _, warnings = self.fingerprint.validate(periodic)
        self.assertEqual(len(warnings), 6)

        invalid = self.molecular_fingerprint()
        invalid.update({"domain": "bad", "engine": "bad", "status": "bad"})
        errors, _ = self.fingerprint.validate(invalid)
        self.assertTrue(any("invalid domain" in item for item in errors))
        self.assertTrue(any("unsupported engine" in item for item in errors))
        self.assertTrue(any("invalid status" in item for item in errors))

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fingerprint.yaml"
            path.write_text(yaml.safe_dump(clean), encoding="utf-8")
            with (
                patch.object(sys, "argv", ["validate_method_fingerprint.py", str(path), "--json"]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.fingerprint.main(), 0)
            path.write_text("{}\n", encoding="utf-8")
            with (
                patch.object(sys, "argv", ["validate_method_fingerprint.py", str(path)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.fingerprint.main(), 1)
