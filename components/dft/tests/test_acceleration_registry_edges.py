from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_acceleration_registry.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module("tsao_acceleration_registry_edge_tests", VALIDATOR_PATH)


class AccelerationRegistryEdgeTests(unittest.TestCase):
    def test_loader_and_validate_fail_closed_when_import_is_unavailable(self) -> None:
        with (
            patch.object(importlib.util, "spec_from_file_location", return_value=None),
            self.assertRaisesRegex(RuntimeError, "cannot import"),
        ):
            validator.load_module("missing", Path("missing.py"))

        with patch.object(validator, "load_module", side_effect=OSError("blocked")):
            report = validator.validate()
        self.assertFalse(report["ok"])
        self.assertIn("registry import failed", report["errors"][0])

    def test_alias_drift_is_reported_for_both_public_surfaces(self) -> None:
        registry = SimpleNamespace(
            validate_registry=lambda: [],
            plan_libraries=lambda: {"cublas": {"vendor": "nvidia"}},
            optimizer_libraries=lambda: {"cublas": {"vendor": "nvidia"}},
            plan_aliases=lambda: {"cublas": "cublas"},
            optimizer_aliases=lambda: {"cublas": "cublas"},
            BACKEND_BY_VENDOR={"nvidia": "cuda"},
            BACKEND_VENDORS={"cuda": {"nvidia"}},
            registry_report=lambda: {"registry_version": "fixture"},
        )
        plan = SimpleNamespace(
            LIBRARIES={"cublas": {"vendor": "nvidia"}},
            ALIASES={"cublas": "cublas"},
            BACKEND_BY_VENDOR={"nvidia": "cuda"},
            BACKEND_VENDORS={"cuda": {"nvidia"}},
            normalize_library=lambda _value: "wrong",
        )
        contract = SimpleNamespace(
            LIBRARIES={"cublas": {"vendor": "nvidia"}},
            ALIASES={"cublas": "cublas"},
            BACKEND_VENDORS={"cuda": {"nvidia"}},
            normalize_library=lambda _value: "wrong",
        )
        with patch.object(validator, "load_module", side_effect=[registry, plan, contract]):
            report = validator.validate()
        self.assertFalse(report["ok"])
        self.assertTrue(any("plan_acceleration alias" in error for error in report["errors"]))
        self.assertTrue(any("hardware optimizer alias" in error for error in report["errors"]))

    def test_text_cli_reports_structured_failure(self) -> None:
        with (
            patch.object(validator, "validate", return_value={"ok": False, "errors": ["fixture drift"]}),
            patch.object(sys, "argv", [str(VALIDATOR_PATH)]),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            returncode = validator.main()
        self.assertEqual(returncode, 1)
        self.assertIn("FAIL: fixture drift", output.getvalue())
        self.assertIn("Acceleration registry validation: FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
