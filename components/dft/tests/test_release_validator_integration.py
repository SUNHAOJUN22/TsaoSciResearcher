from __future__ import annotations

import hashlib
import importlib.util
import inspect
import io
import json
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = (
    "validate_agent_evals.py",
    "validate_ai_assets.py",
    "validate_capability_claims.py",
    "validate_constraints.py",
    "validate_dependencies.py",
    "validate_governance.py",
    "validate_ignore_markers.py",
    "validate_packaging_model.py",
    "validate_readme_links.py",
    "validate_readme_visuals.py",
    "validate_secrets.py",
)


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    module_name = f"release_validator_{name.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def invoke_validate(module: Any) -> Any:
    function = module.validate
    kwargs: dict[str, Any] = {}
    for name, parameter in inspect.signature(function).parameters.items():
        if parameter.default is not inspect.Parameter.empty:
            continue
        if name == "root":
            kwargs[name] = ROOT
        elif name == "strict":
            kwargs[name] = True
        else:
            raise RuntimeError(f"unsupported required validator parameter: {name}")
    return function(**kwargs)


class ReleaseValidatorIntegrationTests(unittest.TestCase):
    def test_all_permanent_pure_validators_pass_current_repository(self) -> None:
        for name in VALIDATORS:
            with self.subTest(validator=name):
                module = load_script(name)
                result = invoke_validate(module)
                if isinstance(result, tuple):
                    self.assertFalse(result[0], f"{name}: {result}")
                elif isinstance(result, dict):
                    self.assertTrue(result.get("ok", not result.get("failures")), f"{name}: {result}")
                else:
                    self.assertFalse(result, f"{name}: {result}")

        acceptance = load_script("build_release_acceptance.py")
        report = acceptance.build_report()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["software_acceptance"]["state"], acceptance.SOFTWARE_READY)
        self.assertEqual(report["software_acceptance"]["quality_gate_stage_count"], 29)
        self.assertTrue(report["software_acceptance"]["quality_gate_contract_complete"])
        self.assertTrue(report["software_acceptance"]["all_capabilities_at_least_l2"])
        self.assertEqual(report["external_execution"]["state"], acceptance.EXTERNAL_HOLD)
        self.assertFalse(report["external_execution"]["engine_invoked"])
        self.assertFalse(report["external_execution"]["performance_evaluated"])
        self.assertFalse(report["external_execution"]["performance_ratio_published"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(acceptance.schema_failures(report), [])
        for digest in report["artifacts"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_catalog_validator_cli_contract(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as exit_context:
            runpy.run_path(str(ROOT / "scripts/validate_catalog.py"), run_name="__main__")
        self.assertEqual(exit_context.exception.code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])

    def test_strict_repository_audit_main_json(self) -> None:
        module = load_script("validate_repo.py")
        with (
            patch.object(sys, "argv", ["validate_repo.py", "--strict", "--json"]),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(module.main(), 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], [])

    def test_validator_main_json_surfaces(self) -> None:
        for name in (
            "validate_agent_evals.py",
            "validate_capability_claims.py",
            "validate_constraints.py",
            "validate_dependencies.py",
            "validate_governance.py",
            "validate_ignore_markers.py",
            "validate_packaging_model.py",
            "validate_secrets.py",
        ):
            with self.subTest(validator=name):
                module = load_script(name)
                with (
                    patch.object(sys, "argv", [name, "--json"]),
                    redirect_stdout(io.StringIO()) as stdout,
                ):
                    self.assertEqual(module.main(), 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload["ok"])

        acceptance = load_script("build_release_acceptance.py")
        first = acceptance.build_report()
        second = acceptance.build_report()
        self.assertEqual(first, second)
        acceptance.write_report(None, first)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            output = root / "release-acceptance.json"
            with (
                patch.object(sys, "argv", ["build_release_acceptance.py", "--out", str(output), "--json"]),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(acceptance.main(), 0)
            self.assertEqual(json.loads(stdout.getvalue()), json.loads(output.read_text(encoding="utf-8")))

            duplicate = root / "duplicate.json"
            duplicate.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"a": NaN}', encoding="utf-8")
            wrong_root = root / "wrong-root.json"
            wrong_root.write_text("[]", encoding="utf-8")
            for path in (duplicate, nonfinite, wrong_root):
                with self.assertRaises(ValueError):
                    acceptance.load_json_mapping(path)
            payload_path = root / "payload.bin"
            payload_path.write_bytes(b"abc" * 500000)
            self.assertEqual(
                acceptance.sha256_file(payload_path),
                hashlib.sha256(payload_path.read_bytes()).hexdigest(),
            )

            missing_compute = root / "missing-compute.json"
            with patch.object(acceptance, "COMPUTE_EVIDENCE_PATH", missing_compute):
                generated, source = acceptance.load_compute_evidence([])
            self.assertTrue(generated["ok"])
            self.assertEqual(source, "generated-in-memory")
            with (
                patch.object(acceptance, "COMPUTE_EVIDENCE_PATH", missing_compute),
                patch.object(acceptance, "CAPTURE_EVIDENCE_PATH", root / "missing-capture.py"),
            ):
                errors: list[str] = []
                unavailable, source = acceptance.load_compute_evidence(errors)
            self.assertEqual(unavailable, {})
            self.assertEqual(source, "unavailable")
            self.assertTrue(errors)

            bad_compute = {
                "ok": False,
                "state": acceptance.UNQUALIFIED,
                "external_engine_invoked": True,
                "performance_ratio_published": True,
                "errors": ["fixture"],
            }
            files = acceptance.required_files()
            files["missing_fixture"] = root / "missing.md"
            with (
                patch.object(acceptance, "required_files", return_value=files),
                patch.object(acceptance, "load_compute_evidence", return_value=(bad_compute, "generated-file")),
            ):
                bad_report = acceptance.build_report()
            self.assertFalse(bad_report["ok"])
            self.assertEqual(bad_report["software_acceptance"]["state"], acceptance.UNQUALIFIED)
            rendered = " ".join(bad_report["errors"])
            for fragment in (
                "required acceptance file missing",
                "compute contract evidence is not valid",
                "does not preserve EXTERNAL_HOLD",
                "invoked an external engine",
                "published a performance ratio",
                "contains errors",
            ):
                self.assertIn(fragment, rendered)

            capability = root / "CAPABILITY_STATUS.yaml"
            capability.write_text(
                "schema_version: '1.0'\n"
                "release: wrong\n"
                "capabilities:\n"
                "  - id: broken\n"
                "    skill: tsao-dft-suite\n"
                "    status: draft\n"
                "    support_level: L1_HANDOFF\n"
                "    scripts: [missing.py]\n"
                "    external_requirements: bad\n",
                encoding="utf-8",
            )
            workflow = root / "ci.yml"
            workflow.write_text("jobs: {}\n", encoding="utf-8")
            schema = root / "schema.json"
            schema.write_text('{"type": "array"}\n', encoding="utf-8")
            with (
                patch.object(acceptance, "CAPABILITY_PATH", capability),
                patch.object(acceptance, "WORKFLOW_PATH", workflow),
                patch.object(acceptance, "SCHEMA_PATH", schema),
                patch.object(acceptance, "QUALITY_GATE_PATH", root / "missing-quality-gate.py"),
            ):
                drift_report = acceptance.build_report()
            self.assertFalse(drift_report["ok"])
            self.assertEqual(drift_report["software_acceptance"]["state"], acceptance.UNQUALIFIED)
            rendered = " ".join(drift_report["errors"])
            for fragment in (
                "CAPABILITY_STATUS release",
                "below repository-software acceptance level",
                "status is not implemented",
                "implementation script missing",
                "external_requirements",
                "quality gate contract unavailable",
                "permanent CI job set mismatch",
                "Python matrix mismatch",
                "real Windows runner",
                "release acceptance schema",
            ):
                self.assertIn(fragment, rendered)


if __name__ == "__main__":
    unittest.main()
