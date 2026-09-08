from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_PATH = ROOT / "tests" / "test_compute_qualification.py"
MODULE_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "qualify_compute_campaign.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_compute_qualification.py"
BENCHMARK_VALIDATOR_PATH = ROOT / "scripts" / "validate_benchmark_contract.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


support = load_module("tsao_compute_qualification_edge_support", SUPPORT_PATH)
qualification = load_module("tsao_compute_qualification_native_edges", MODULE_PATH)
validator = load_module("tsao_compute_qualification_validator_edges", VALIDATOR_PATH)
benchmark_validator = load_module("tsao_compute_projection_benchmark_fixture", BENCHMARK_VALIDATOR_PATH)


class ComputeQualificationNativeEdgeTests(unittest.TestCase):
    def test_projection_is_not_consumed_and_legacy_export_is_normalization_bounded(self) -> None:
        raw = support.complete_raw()
        with patch.object(
            qualification.contract,
            "compute_qualification_view",
            side_effect=AssertionError("projection must not be consumed"),
        ):
            report = qualification.qualify(support.campaign(), raw)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["state"], qualification.QUALIFIED_FOR_REVIEW)
        self.assertFalse(report["legacy_projection_consumed"])

        canonical = support.canonical_result("CPU-REF", 1, 10.0)
        document = qualification.prepare_document(canonical)
        projection = qualification.contract.compute_qualification_view(canonical)
        self.assertEqual(projection["candidate_id"], document.candidate_id)
        self.assertEqual(projection["wall_time_seconds"], document.wall_time_s)
        self.assertEqual(projection["input_sha256"], document.input_sha256)
        self.assertEqual(projection["_canonical_schema_version"], "1.1")

        nested_v10 = copy.deepcopy(canonical)
        nested_v10["schema_version"] = "1.0"
        migrated_projection = qualification.contract.compute_qualification_view(nested_v10)
        self.assertEqual(migrated_projection["_canonical_schema_version"], "1.1")

        with self.assertRaisesRegex(qualification.contract.BenchmarkContractError, "explicit"):
            qualification.contract.compute_qualification_view(benchmark_validator.legacy_flat_fixture())
        unknown = copy.deepcopy(canonical)
        unknown["schema_version"] = "9.9"
        with self.assertRaisesRegex(qualification.contract.BenchmarkContractError, "unsupported nested"):
            qualification.contract.compute_qualification_view(unknown)

    def test_projection_collision_is_rejected_by_native_accessor(self) -> None:
        collision = support.canonical_result("CPU-REF", 1, 10.0)
        collision["scientific"]["results"]["properties"]["energy_ev"] = 123.0
        projected = qualification.contract.compute_qualification_view(collision)
        self.assertEqual(projected["scientific_results"]["energy_ev"], 123.0)
        with self.assertRaisesRegex(qualification.QualificationLoadError, "collide"):
            qualification.prepare_document(collision)

    def test_identity_drift_table_fails_closed(self) -> None:
        cases: list[tuple[str, Any, str]] = [
            (
                "duplicate run",
                lambda rows: rows[-1]["execution"].__setitem__("run_id", rows[0]["execution"]["run_id"]),
                "globally unique",
            ),
            (
                "build drift",
                lambda rows: rows[-1]["engine"].__setitem__("build_fingerprint_id", "BUILD-DRIFT"),
                "build, software, hardware or GPU topology identity",
            ),
            (
                "hardware drift",
                lambda rows: rows[-1]["hardware"].__setitem__("hardware_fingerprint_id", "HW-DRIFT"),
                "hardware_fingerprint_id",
            ),
            (
                "site drift",
                lambda rows: (
                    rows[-1]["hardware"].__setitem__("site_id", "SITE-2"),
                    rows[-1]["execution"].__setitem__("site_id", "SITE-2"),
                ),
                "execution.site_id differs",
            ),
            (
                "multi gpu drift",
                lambda rows: rows[-1]["hardware"].__setitem__("gpu_uuids", ["GPU-A", "GPU-C"]),
                "multi-GPU UUID set",
            ),
            (
                "role mismatch",
                lambda rows: rows[0].__setitem__("role", "acceleration-candidate"),
                "canonical role does not match",
            ),
            (
                "input drift",
                lambda rows: rows[-1]["scientific"].__setitem__("input_sha256", "a" * 64),
                "input_sha256 differs",
            ),
            (
                "method drift",
                lambda rows: rows[-1]["scientific"].__setitem__("method_fingerprint_id", "METHOD-2"),
                "method_fingerprint_id differs",
            ),
            (
                "engine version drift",
                lambda rows: rows[-1]["engine"].__setitem__("version", "6.5.2"),
                "scientific identity differs",
            ),
        ]
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                rows = support.complete_raw()
                mutate(rows)
                report = qualification.qualify(support.campaign(), rows)
                self.assertFalse(report["ok"], report)
                self.assertTrue(any(expected in error for error in report["errors"]), report["errors"])
                self.assertFalse(report["performance"]["evaluated"])

    def test_provenance_and_artifact_hold_table(self) -> None:
        cases: list[tuple[str, Any, str]] = [
            (
                "imported provenance",
                lambda row: row["evidence_source"].update(
                    kind="imported-unverified",
                    missing_fields=["real execution unavailable"],
                ),
                "missing_fields",
            ),
            (
                "unchecked artifact",
                lambda row: row["artifacts"][0].__setitem__("verification_status", "NOT_CHECKED"),
                "not fully VERIFIED",
            ),
            (
                "missing build",
                lambda row: row["engine"].__setitem__("build_fingerprint_id", "MISSING"),
                "build fingerprint is missing",
            ),
            (
                "missing hardware",
                lambda row: row["hardware"].__setitem__("hardware_fingerprint_id", "MISSING"),
                "hardware fingerprint is missing",
            ),
            (
                "missing site",
                lambda row: (
                    row["hardware"].__setitem__("site_id", "MISSING"),
                    row["execution"].__setitem__("site_id", "MISSING"),
                ),
                "site identity is missing",
            ),
        ]
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                rows = support.complete_raw()
                mutate(rows[-1])
                report = qualification.qualify(support.campaign(), rows)
                self.assertEqual(report["state"], qualification.EXTERNAL_HOLD)
                self.assertFalse(report["performance"]["evaluated"])
                self.assertTrue(any(expected in hold for hold in report["holds"]), report["holds"])

    def test_contradictory_site_and_acceleration_identity_fail_closed(self) -> None:
        site_mismatch = support.canonical_result("CPU-REF", 1, 10.0)
        site_mismatch["execution"]["site_id"] = "SITE-OTHER"
        with self.assertRaisesRegex(qualification.QualificationLoadError, "site_id"):
            qualification.prepare_document(site_mismatch)

        missing_gpu = support.complete_raw()
        candidate = missing_gpu[-1]
        candidate["software"]["accelerator_runtime"] = "none"
        candidate["hardware"].update(
            gpu_vendor="none",
            gpu_model=None,
            gpu_uuids=[],
            gpu_memory_gb=None,
            driver_version=None,
            gpu_binding="none",
        )
        report = qualification.qualify(support.campaign(), missing_gpu)
        self.assertFalse(report["ok"])
        self.assertTrue(any("acceleration role requires" in error for error in report["errors"]))

    def test_nonfinite_values_are_rejected_before_comparison_table(self) -> None:
        cases: list[tuple[str, Any]] = [
            ("wall", lambda row: row["performance"].__setitem__("wall_time_s", float("inf"))),
            ("energy", lambda row: row["scientific"]["results"].__setitem__("energy_ev", float("nan"))),
            (
                "threshold",
                lambda row: row["scientific"]["convergence_thresholds"].__setitem__("ediff_ev", float("inf")),
            ),
        ]
        for name, mutate in cases:
            with self.subTest(name=name):
                rows = support.complete_raw()
                mutate(rows[-1])
                report = qualification.qualify(support.campaign(), rows)
                self.assertFalse(report["ok"])
                self.assertFalse(report["performance"]["evaluated"])
                self.assertTrue(any("non-finite" in error for error in report["errors"]), report["errors"])

    def test_validator_error_branches_are_structured(self) -> None:
        with patch.object(validator, "load_module", side_effect=RuntimeError("missing module")):
            report = validator.validate()
        self.assertFalse(report["ok"])
        self.assertTrue(any("missing module" in error for error in report["errors"]))

        class FakeModule:
            EXTERNAL_HOLD = "EXTERNAL_HOLD"
            MAX_WORKERS = 8
            PROJECTION_STATUS = "WRONG"

            @staticmethod
            def load_campaign(_: Path) -> dict[str, Any]:
                return support.campaign()

            @staticmethod
            def validate_campaign(_: dict[str, Any]) -> list[str]:
                return ["campaign-invalid"]

            @staticmethod
            def qualify(_: dict[str, Any], __: list[Any]) -> dict[str, Any]:
                return {
                    "state": "UNQUALIFIED",
                    "performance": {"evaluated": True},
                    "workers_bounded_by": 7,
                    "benchmark_result_contract": "legacy-flat-v1.0",
                    "input_model": "flat",
                    "normalization_mandatory": False,
                    "native_semantic_validation": False,
                    "legacy_projection_consumed": True,
                    "legacy_projection_status": "WRONG",
                    "identity_invariants": [],
                    "errors": [],
                }

            @staticmethod
            def normalized_workers(_: int, __: int) -> int:
                return 7

            @staticmethod
            def load_results(_: list[Path], __: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
                return [{}], []

        with patch.object(validator, "load_module", return_value=FakeModule()):
            drift = validator.validate()
        self.assertFalse(drift["ok"])
        rendered = " ".join(drift["errors"])
        for expected in (
            "campaign-invalid",
            "EXTERNAL_HOLD",
            "must not evaluate",
            "worker bound",
            "canonical nested",
            "typed-accessor",
            "normalization",
            "native semantic",
            "legacy flat projection",
            "custom schema",
            "identity invariants",
        ):
            self.assertIn(expected, rendered)


if __name__ == "__main__":
    unittest.main()
