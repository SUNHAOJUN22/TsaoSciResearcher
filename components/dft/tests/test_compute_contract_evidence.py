from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_compute_contract_evidence.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


capture = load_module("tsao_compute_contract_evidence_tests", SCRIPT)


class ComputeContractEvidenceTests(unittest.TestCase):
    def test_current_repository_is_machine_readable_external_hold(self) -> None:
        report = capture.build_report()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["schema_version"], "1.5")
        self.assertEqual(report["state"], capture.EXTERNAL_HOLD)
        self.assertFalse(report["external_engine_invoked"])
        self.assertTrue(report["acceleration_registry"]["runtime_single_source"])
        benchmark = report["benchmark_contract"]
        self.assertEqual(benchmark["canonical_contract"], "nested-v1.1")
        self.assertTrue(benchmark["root_mirror_synchronized"])
        self.assertEqual(benchmark["native_semantic_schema_version"], "1.1")
        self.assertFalse(benchmark["compatibility_view_present"])
        self.assertEqual(benchmark["legacy_semantic_bypass"], "FAIL_CLOSED")
        self.assertEqual(
            benchmark["legacy_flat_qualification_impact"],
            capture.EXTERNAL_HOLD,
        )
        self.assertEqual(benchmark["unknown_or_mixed_input"], "FAIL_CLOSED")

        campaign = report["campaign_contract"]
        self.assertTrue(campaign["ok"])
        self.assertEqual(
            campaign["canonical_contract"],
            "canonical-compute-campaign-v1.1",
        )
        self.assertEqual(campaign["canonical_schema_version"], "1.1")
        self.assertTrue(campaign["root_mirror_synchronized"])
        self.assertEqual(campaign["template_migration"], "none")
        self.assertEqual(campaign["migration_qualification_impact"], "none")
        self.assertEqual(campaign["defaults_applied"], [])
        self.assertEqual(campaign["evidence_fields_added"], [])
        self.assertEqual(campaign["unknown_or_mixed_input"], "FAIL_CLOSED")
        self.assertTrue(campaign["immutable_mapping"])
        self.assertEqual(
            campaign["benchmark_result_boundary"],
            "campaign-policy-independent-from-benchmark-result-evidence",
        )

        self.assertEqual(
            report["engine_capabilities"]["repository_template_state"],
            capture.EXTERNAL_HOLD,
        )
        self.assertEqual(
            report["engine_capabilities"]["performance_qualification"],
            "NOT_ESTABLISHED",
        )
        qualification = report["compute_qualification"]
        self.assertEqual(qualification["repository_state"], capture.EXTERNAL_HOLD)
        self.assertEqual(
            qualification["benchmark_result_contract"],
            "canonical-nested-v1.1",
        )
        self.assertEqual(
            qualification["input_model"],
            "canonical-nested-v1.1-typed-accessor",
        )
        self.assertTrue(qualification["normalization_mandatory"])
        self.assertTrue(qualification["native_semantic_validation"])
        self.assertTrue(qualification["legacy_projection_retained"])
        self.assertFalse(qualification["legacy_projection_consumed"])
        self.assertEqual(
            qualification["legacy_projection_qualification_impact"],
            "NOT_ELIGIBLE",
        )
        self.assertEqual(len(qualification["identity_invariants"]), 7)
        self.assertFalse(qualification["performance_evaluated"])
        self.assertEqual(qualification["workers_bounded_by"], 8)

        architecture = report["implementation_architecture"]
        self.assertEqual(architecture["doctrine"], "python-control-plane-profile-first")
        self.assertTrue(architecture["python_control_plane"])
        self.assertEqual(architecture["whole_repo_cpp_rewrite"], "NOT_RECOMMENDED")
        self.assertTrue(architecture["neighbor_search"]["implemented"])
        self.assertEqual(
            architecture["neighbor_search"]["backends"],
            ["reference", "numpy", "cell-list"],
        )
        self.assertFalse(architecture["neighbor_search"]["implicit_gpu_selection"])
        self.assertEqual(
            architecture["neighbor_search"]["qualification_impact"],
            "NOT_PERFORMANCE_EVIDENCE",
        )
        self.assertTrue(architecture["parser_scan"]["implemented"])
        self.assertEqual(architecture["parser_scan"]["transport"], "read-only-mmap")
        self.assertEqual(architecture["parser_scan"]["nonfinite_numeric_input"], "FAIL_CLOSED")
        self.assertFalse(architecture["native_sidecar"]["implemented"])
        self.assertEqual(architecture["native_sidecar"]["status"], "PROFILE_AND_BUILD_GATED")
        self.assertFalse(architecture["cuda_kernels"]["implemented"])
        self.assertEqual(architecture["cuda_kernels"]["status"], "NOT_ESTABLISHED")
        self.assertEqual(architecture["external_engine_acceleration"], capture.EXTERNAL_HOLD)

        self.assertFalse(report["performance_ratio_published"])
        self.assertTrue(
            any(
                "Campaign v1.0 migration" in item and "creates no execution evidence" in item
                for item in report["non_claims"]
            )
        )
        self.assertTrue(any("No nested v1.0 semantic downgrade view" in item for item in report["non_claims"]))
        self.assertTrue(any("remains diagnostic" in item for item in report["non_claims"]))
        self.assertTrue(any("neighbor-list and mmap parser" in item for item in report["non_claims"]))
        self.assertTrue(any("No native sidecar or CUDA kernel" in item for item in report["non_claims"]))

    def test_capture_is_deterministic(self) -> None:
        first = capture.build_report()
        second = capture.build_report()
        self.assertEqual(first, second)

    def test_validator_failure_is_unqualified(self) -> None:
        broken = type("BrokenValidator", (), {"validate": staticmethod(lambda: {"ok": False})})()
        with patch.object(capture, "load_module", return_value=broken):
            report = capture.build_report()
        self.assertFalse(report["ok"])
        self.assertEqual(report["state"], capture.UNQUALIFIED)
        self.assertTrue(any("validator failed" in error for error in report["errors"]))

    def test_implementation_drift_is_unqualified(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            paths = dict(capture.IMPLEMENTATION_PATHS)
            paths["doctrine"] = root / "missing-doctrine.md"
            paths["neighbor_core"] = root / "broken-neighbor.py"
            paths["neighbor_core"].write_text("pass\n", encoding="utf-8")
            paths["structure_inspector"] = root / "broken-inspector.py"
            paths["structure_inspector"].write_text("pass\n", encoding="utf-8")
            paths["scan_core"] = root / "broken-scan.py"
            paths["scan_core"].write_text("pass\n", encoding="utf-8")
            paths["parser_contract"] = root / "broken-parser.py"
            paths["parser_contract"].write_text("pass\n", encoding="utf-8")
            with patch.object(capture, "IMPLEMENTATION_PATHS", paths):
                report = capture.build_report()
        self.assertFalse(report["ok"])
        self.assertEqual(report["state"], capture.UNQUALIFIED)
        rendered = " ".join(report["errors"])
        for expected in (
            "cannot read acceleration doctrine",
            "neighbor-search core",
            "structure inspector",
            "engine scan core",
            "do not all consume",
            "not fail-closed",
        ):
            self.assertIn(expected, rendered)

    def test_semantic_campaign_and_projection_contract_drift_is_unqualified(self) -> None:
        reports = {
            "acceleration_registry": {
                "ok": True,
                "validated_surfaces": ["runtime_single_source"],
            },
            "benchmark_contract": {
                "ok": True,
                "canonical_contract": "nested-v1.1",
                "root_mirror_synchronized": True,
                "native_semantic_schema_version": "1.0",
                "compatibility_view_present": True,
                "legacy_semantic_bypass": "OPEN",
                "legacy_flat_qualification_impact": capture.EXTERNAL_HOLD,
                "unknown_or_mixed_input": "FAIL_CLOSED",
                "external_engine_invoked": False,
            },
            "engine_capabilities": {
                "ok": True,
                "repository_template_state": capture.EXTERNAL_HOLD,
                "performance_qualification": "NOT_ESTABLISHED",
            },
            "compute_qualification": {
                "ok": True,
                "repository_state": capture.EXTERNAL_HOLD,
                "performance_evaluated": False,
                "workers_bounded_by": 8,
                "campaign_contract": "legacy-compute-campaign-v1.0",
                "campaign_schema_version": "1.0",
                "campaign_root_mirror_synchronized": False,
                "campaign_unknown_or_mixed_input": "OPEN",
                "campaign_migration_qualification_impact": "PROMOTES",
                "campaign_defaults_applied": ["minimum_repeats"],
                "campaign_evidence_fields_added": ["solver"],
                "campaign_document_immutable": False,
                "contract_boundary": "mixed",
                "input_model": "legacy-flat",
                "normalization_mandatory": False,
                "native_semantic_validation": False,
                "legacy_projection_retained": False,
                "legacy_projection_consumed": True,
                "legacy_projection_qualification_impact": "ELIGIBLE",
                "identity_invariants": [],
            },
        }

        def fake_load(name: str, _: Path) -> object:
            key = name.removeprefix("tsao_contract_evidence_")
            return type("Validator", (), {"validate": staticmethod(lambda: reports[key])})()

        with patch.object(capture, "load_module", side_effect=fake_load):
            report = capture.build_report()
        self.assertFalse(report["ok"])
        self.assertEqual(report["state"], capture.UNQUALIFIED)
        rendered = " ".join(report["errors"])
        for expected in (
            "not native",
            "compatibility view",
            "bypass",
            "campaign authority",
            "campaign schema version",
            "campaign schema mirror",
            "campaign input",
            "migration impact",
            "applied defaults",
            "fabricated evidence",
            "document is not immutable",
            "contract boundary",
            "input model",
            "central normalization",
            "native semantic validation",
            "projection retention",
            "still consumed",
            "qualification-ineligible",
            "identity invariants",
        ):
            self.assertIn(expected, rendered)

    def test_write_and_cli_outputs(self) -> None:
        capture.write_report(None, {"ok": True})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "evidence.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--out", str(output), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )
            stdout = json.loads(completed.stdout)
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout, written)
            self.assertEqual(written["schema_version"], "1.5")
            self.assertEqual(written["state"], capture.EXTERNAL_HOLD)


if __name__ == "__main__":
    unittest.main()
