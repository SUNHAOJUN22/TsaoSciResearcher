from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "qualify_compute_campaign.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_compute_qualification.py"
BENCHMARK_VALIDATOR_PATH = ROOT / "scripts" / "validate_benchmark_contract.py"
SCHEMA_PATH = ROOT / "templates" / "benchmark-result.schema.json"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


qualification = load_module("tsao_compute_qualification_tests", MODULE_PATH)
validator = load_module("tsao_compute_qualification_validator_tests", VALIDATOR_PATH)
benchmark_validator = load_module("tsao_compute_qualification_benchmark_fixture", BENCHMARK_VALIDATOR_PATH)


def campaign() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "campaign_id": "CAMPAIGN-1",
        "benchmark_plan_id": "PLAN-1",
        "engine": "vasp",
        "reference_candidate_id": "CPU-REF",
        "candidate_ids": ["GPU-CANDIDATE"],
        "minimum_repeats": 3,
        "minimum_reference_over_candidate_ratio": 1.1,
        "numerical_tolerances": {
            "energy_ev": {"absolute": 1.0e-6, "relative": 1.0e-8},
            "forces_ev_per_angstrom": {"absolute": 1.0e-4, "relative": 1.0e-6},
        },
    }


def canonical_result(
    candidate_id: str,
    repeat: int,
    wall_time: float,
    *,
    gpu_uuids: tuple[str, ...] = (),
) -> dict[str, Any]:
    is_gpu = bool(gpu_uuids)
    return {
        "schema_version": "1.1",
        "benchmark_plan_id": "PLAN-1",
        "candidate_id": candidate_id,
        "role": "acceleration-candidate" if is_gpu else "scientific-reference",
        "repeat_index": repeat,
        "engine": {
            "name": "vasp",
            "version": "6.5.1",
            "executable": "vasp_std",
            "build_fingerprint_id": f"BUILD-{candidate_id}",
        },
        "software": {
            "compiler": "NVHPC 25.1",
            "mpi": "Open MPI 5.0.7",
            "openmp_runtime": "NVHPC OpenMP 25.1",
            "accelerator_runtime": ("cuda;toolkit=12.8;driver=600.1" if is_gpu else "none"),
        },
        "hardware": {
            "site_id": "SITE-1",
            "hardware_fingerprint_id": f"HW-{candidate_id}",
            "cpu_model": "fixture-cpu",
            "cpu_arch": "x86_64",
            "nodes": 1,
            "ranks_per_node": 1,
            "threads_per_rank": 8,
            "gpu_vendor": "nvidia" if is_gpu else "none",
            "gpu_model": "fixture-gpu" if is_gpu else None,
            "gpu_uuids": list(gpu_uuids),
            "gpu_memory_gb": 24.0 * len(gpu_uuids) if is_gpu else None,
            "driver_version": "600.1" if is_gpu else None,
            "gpu_binding": ",".join(gpu_uuids) if is_gpu else "none",
        },
        "execution": {
            "scheduler": "local",
            "job_id": f"JOB-{candidate_id}-{repeat}",
            "run_id": f"RUN-{candidate_id}-{repeat}",
            "site_id": "SITE-1",
            "filesystem": "local",
            "scratch_type": "local-ssd",
            "timestamp": f"2026-08-05T00:00:0{repeat}Z",
            "exit_status": 0,
        },
        "scientific": {
            "input_sha256": "e" * 64,
            "method_fingerprint_id": "METHOD-1",
            "model_identity": {
                "functional": "PBE",
                "basis_or_pseudopotential": "POTCAR-HASH-1",
                "corrections": "none",
            },
            "convergence_thresholds": {
                "ediff_ev": 1.0e-6,
                "force_ev_per_angstrom": 0.01,
            },
            "observable_set": ["energy", "forces"],
            "parser_accepted": True,
            "parser_status": "ACCEPTED",
            "results": {
                "energy_ev": -10.0,
                "forces_ev_per_angstrom": [0.001, -0.002, 0.003],
                "stress_gpa": None,
                "properties": {},
            },
        },
        "performance": {
            "wall_time_s": wall_time,
            "cpu_time_s": wall_time * 4,
            "scf_iterations": 12,
            "peak_host_memory_mb": 100.0,
            "peak_device_memory_mb": 200.0 if is_gpu else None,
            "cpu_utilization_percent": 80.0,
            "gpu_utilization_percent": 90.0 if is_gpu else None,
            "io_bytes": 1024,
            "energy_joules": None,
        },
        "artifacts": [
            {
                "path": f"outputs/{candidate_id}-{repeat}.out",
                "sha256": "f" * 64,
                "verification_status": "VERIFIED",
            }
        ],
        "evidence_source": {
            "kind": "real-engine",
            "source_id": f"SOURCE-{candidate_id}-{repeat}",
            "missing_fields": [],
        },
    }


def complete_raw(candidate_wall: float = 5.0) -> list[dict[str, Any]]:
    documents = [canonical_result("CPU-REF", repeat, 10.0) for repeat in range(1, 4)]
    documents.extend(
        canonical_result(
            "GPU-CANDIDATE",
            repeat,
            candidate_wall,
            gpu_uuids=("GPU-A", "GPU-B"),
        )
        for repeat in range(1, 4)
    )
    return documents


def complete_documents(candidate_wall: float = 5.0) -> list[Any]:
    return [qualification.prepare_document(document) for document in complete_raw(candidate_wall)]


def role_hints() -> dict[str, str]:
    return {
        "CPU-REF": "scientific-reference",
        "GPU-CANDIDATE": "acceleration-candidate",
    }


class ComputeQualificationTests(unittest.TestCase):
    def test_repository_workflow_is_bounded_and_external_hold(self) -> None:
        report = validator.validate()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["repository_state"], qualification.EXTERNAL_HOLD)
        self.assertFalse(report["performance_evaluated"])
        self.assertEqual(report["benchmark_result_contract"], "canonical-nested-v1.1")
        self.assertEqual(report["input_model"], "canonical-nested-v1.1-typed-accessor")
        self.assertTrue(report["normalization_mandatory"])
        self.assertTrue(report["native_semantic_validation"])
        self.assertTrue(report["legacy_projection_retained"])
        self.assertFalse(report["legacy_projection_consumed"])
        self.assertEqual(report["legacy_projection_qualification_impact"], "NOT_ELIGIBLE")
        self.assertEqual(report["workers_bounded_by"], 8)

    def test_real_repeated_equivalent_campaign_qualifies_for_review_only(self) -> None:
        report = qualification.qualify(campaign(), complete_documents())
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["state"], qualification.QUALIFIED_FOR_REVIEW)
        self.assertTrue(report["performance"]["evaluated"])
        candidate = report["performance"]["candidates"]["GPU-CANDIDATE"]
        self.assertEqual(candidate["reference_over_candidate_ratio"], 2.0)
        self.assertTrue(candidate["passes"])
        self.assertFalse(report["legacy_projection_consumed"])
        self.assertEqual(len(report["identity_invariants"]), 7)
        self.assertIn("not signed L3", report["non_claims"][0])

    def test_non_real_and_unverified_evidence_force_hold_without_ratio(self) -> None:
        documents = complete_raw()
        documents[-1]["evidence_source"]["kind"] = "test-fixture"
        documents[-2]["artifacts"][0]["verification_status"] = "NOT_CHECKED"
        report = qualification.qualify(campaign(), documents)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["state"], qualification.EXTERNAL_HOLD)
        self.assertFalse(report["performance"]["evaluated"])
        self.assertTrue(any("not real-engine" in hold for hold in report["holds"]))
        self.assertTrue(any("not fully VERIFIED" in hold for hold in report["holds"]))

    def test_numerical_and_performance_failures_are_unqualified(self) -> None:
        numerical = complete_raw()
        numerical[-1]["scientific"]["results"]["energy_ev"] = -9.0
        report = qualification.qualify(campaign(), numerical)
        self.assertFalse(report["ok"])
        self.assertEqual(report["state"], qualification.UNQUALIFIED)
        self.assertTrue(any("numerical mismatch" in error for error in report["errors"]))

        slow = qualification.qualify(campaign(), complete_documents(candidate_wall=10.0))
        self.assertFalse(slow["ok"])
        self.assertEqual(slow["state"], qualification.UNQUALIFIED)
        self.assertTrue(slow["performance"]["evaluated"])
        self.assertTrue(any("threshold was not met" in error for error in slow["errors"]))

    def test_worker_and_campaign_contracts_fail_closed(self) -> None:
        self.assertEqual(qualification.normalized_workers(1000, 1000), 8)
        with self.assertRaisesRegex(ValueError, "workers must be non-negative"):
            qualification.normalized_workers(-1, 2)
        mutated = copy.deepcopy(campaign())
        mutated["minimum_repeats"] = 2
        self.assertIn("minimum_repeats must be an integer >= 3", qualification.validate_campaign(mutated))

    def test_parallel_loader_is_deterministic_and_native_canonical(self) -> None:
        schema = qualification.load_json(SCHEMA_PATH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / "z.json", root / "a.json"]
            paths[0].write_text(
                json.dumps(canonical_result("GPU-CANDIDATE", 1, 5.0, gpu_uuids=("GPU-A", "GPU-B"))),
                encoding="utf-8",
            )
            paths[1].write_text(json.dumps(canonical_result("CPU-REF", 1, 10.0)), encoding="utf-8")
            documents, errors = qualification.load_results(
                paths,
                schema,
                workers=100,
                role_hints=role_hints(),
            )
        self.assertEqual(errors, [])
        self.assertEqual([document.candidate_id for document in documents], ["CPU-REF", "GPU-CANDIDATE"])
        self.assertTrue(all(document.schema_version == "1.1" for document in documents))
        self.assertTrue(all(document.migration["migration"] == "none" for document in documents))

    def test_legacy_nested_is_centrally_migrated_before_typed_access(self) -> None:
        legacy = canonical_result("CPU-REF", 1, 10.0)
        legacy["schema_version"] = "1.0"
        document = qualification.prepare_document(legacy)
        self.assertEqual(document.schema_version, "1.1")
        self.assertEqual(document.migration["source_contract"], "legacy-nested-v1.0")
        self.assertEqual(document.migration["qualification_impact"], "none")

    def test_legacy_flat_loader_requires_explicit_roles_and_remains_hold(self) -> None:
        schema = qualification.load_json(SCHEMA_PATH)
        legacy = benchmark_validator.legacy_flat_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            documents, errors = qualification.load_results([path], schema)
            held_documents, held_errors = qualification.load_results(
                [path],
                schema,
                role_hints={legacy["candidate_id"]: "scientific-reference"},
            )
        self.assertEqual(documents, [])
        self.assertTrue(any("explicit" in error for error in errors))
        self.assertEqual(held_errors, [])
        report = qualification.qualify(
            {
                **campaign(),
                "reference_candidate_id": legacy["candidate_id"],
                "candidate_ids": ["GPU-CANDIDATE"],
            },
            held_documents,
        )
        self.assertEqual(report["state"], qualification.EXTERNAL_HOLD)
        self.assertFalse(report["performance"]["evaluated"])
        self.assertTrue(any("source migration forces" in hold for hold in report["holds"]))

    def test_custom_schema_and_nonfinite_json_are_rejected(self) -> None:
        custom_documents, custom_errors = qualification.load_results(
            [],
            {"properties": {"schema_version": {"const": "2.0"}}},
        )
        self.assertEqual(custom_documents, [])
        self.assertTrue(any("authoritative nested v1.1" in error for error in custom_errors))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overflow.json"
            path.write_text('{"performance": {"wall_time_s": 1e999}}', encoding="utf-8")
            with self.assertRaisesRegex(
                qualification.QualificationLoadError,
                "non-finite JSON number is forbidden",
            ):
                qualification.load_json(path)


if __name__ == "__main__":
    unittest.main()
