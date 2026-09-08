from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_core():
    path = ROOT / "scripts/performance_evidence.py"
    spec = importlib.util.spec_from_file_location("tsao_performance_evidence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PerformanceEvidenceTests(unittest.TestCase):
    core: Any
    policy: dict[str, Any]

    @classmethod
    def setUpClass(cls):
        cls.core = load_core()
        cls.policy = yaml.safe_load(
            (ROOT / "templates/performance-qualification-policy.yaml").read_text(encoding="utf-8")
        )

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.artifact_root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def record(
        self,
        candidate: str,
        role: str,
        repeat: int,
        wall: float,
        *,
        gpus: int = 0,
        energy: float = -10.0,
        forces: list[float] | None = None,
        stress: list[float] | None = None,
        parser: bool = True,
        exit_status: int = 0,
        source: str = "real-engine",
        build: str = "BUILD-001",
        hardware_id: str = "HW-CPU-001",
        input_sha: str = "1" * 64,
        method: str = "MF-001",
        artifact_digest: str | None = None,
        energy_joules: float | None = None,
    ) -> dict:
        run_id = f"{candidate}-run-{repeat}"
        artifact = self.artifact_root / f"{run_id}.out"
        artifact.write_text(f"{candidate}:{repeat}:{wall}\n", encoding="utf-8")
        digest = artifact_digest or self.core.sha256_file(artifact)
        gpu_uuids = [f"GPU-{index}" for index in range(gpus)]
        return {
            "schema_version": "1.0",
            "benchmark_plan_id": "PLAN-001",
            "candidate_id": candidate,
            "role": role,
            "repeat_index": repeat,
            "engine": {
                "name": "vasp",
                "version": "6.5.1",
                "executable": "vasp_std",
                "build_fingerprint_id": build,
            },
            "software": {
                "compiler": "nvhpc-26.1",
                "mpi": "openmpi-5.0",
                "openmp_runtime": "llvm-openmp",
                "accelerator_runtime": "cuda-13.0" if gpus else "none",
            },
            "hardware": {
                "site_id": "SITE-A",
                "hardware_fingerprint_id": hardware_id if gpus == 0 else "HW-H100-001",
                "cpu_model": "EPYC",
                "cpu_arch": "x86_64",
                "nodes": 1,
                "ranks_per_node": max(1, gpus),
                "threads_per_rank": 8,
                "gpu_vendor": "nvidia" if gpus else "none",
                "gpu_model": "H100" if gpus else None,
                "gpu_uuids": gpu_uuids,
                "gpu_memory_gb": 80 if gpus else None,
                "driver_version": "590.1" if gpus else None,
                "gpu_binding": "closest" if gpus else "none",
            },
            "execution": {
                "scheduler": "slurm",
                "job_id": f"JOB-{candidate}-{repeat}",
                "run_id": run_id,
                "site_id": "SITE-A",
                "filesystem": "lustre",
                "scratch_type": "node-local-nvme",
                "timestamp": f"2026-07-2{repeat}T00:00:00Z",
                "exit_status": exit_status,
            },
            "scientific": {
                "input_sha256": input_sha,
                "method_fingerprint_id": method,
                "model_identity": {
                    "functional": "PBE",
                    "basis_or_pseudopotential": "POTCAR-HASH-001",
                    "corrections": "none",
                },
                "convergence_thresholds": {"ediff_ev": 1.0e-6, "force_ev_per_angstrom": 0.01},
                "observable_set": ["energy", "forces"],
                "parser_accepted": parser,
                "parser_status": "ACCEPTED" if parser else "REJECTED",
                "results": {
                    "energy_ev": energy,
                    "forces_ev_per_angstrom": forces if forces is not None else [0.0, 0.0, 0.0],
                    "stress_gpa": stress,
                    "properties": {"band_gap_ev": 1.2},
                },
            },
            "performance": {
                "wall_time_s": wall,
                "cpu_time_s": wall * 4,
                "scf_iterations": 12,
                "peak_host_memory_mb": 4096,
                "peak_device_memory_mb": 2048 if gpus else None,
                "cpu_utilization_percent": 90,
                "gpu_utilization_percent": 80 if gpus else None,
                "io_bytes": 1024,
                "energy_joules": energy_joules,
            },
            "artifacts": [
                {
                    "path": artifact.name,
                    "sha256": digest,
                    "verification_status": "NOT_CHECKED",
                }
            ],
            "evidence_source": {"kind": source, "source_id": run_id, "missing_fields": []},
        }

    def validated(self, records: list[dict]) -> list[dict]:
        result = []
        for record in records:
            normalized, errors, _ = self.core.validate_result(record, self.artifact_root)
            self.assertEqual(errors, [])
            result.append(normalized)
        return result

    def reference_records(self) -> list[dict]:
        return [
            self.record("cpu-reference", "scientific-reference", index, wall)
            for index, wall in enumerate((100.0, 102.0, 98.0), start=1)
        ]

    def gpu_records(self, candidate: str = "gpu-1", gpus: int = 1, walls=(50.0, 51.0, 49.0)) -> list[dict]:
        return [
            self.record(candidate, "acceleration-candidate", index, wall, gpus=gpus)
            for index, wall in enumerate(walls, start=1)
        ]

    def approved_review(self) -> dict:
        return {"status": "approved", "reviewer": "independent-reviewer", "reviewed_at": "2026-07-29T00:00:00Z"}

    def test_valid_cpu_reference(self):
        normalized, errors, warnings = self.core.validate_result(self.reference_records()[0], self.artifact_root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(normalized["schema_version"], "1.1")
        self.assertTrue(self.core.all_artifacts_verified(normalized))

    def test_valid_single_gpu_result(self):
        normalized, errors, _ = self.core.validate_result(self.gpu_records()[0], self.artifact_root)
        self.assertEqual(errors, [])
        self.assertEqual(normalized["hardware"]["gpu_uuids"], ["GPU-0"])

    def test_valid_multi_gpu_result(self):
        normalized, errors, _ = self.core.validate_result(self.gpu_records("gpu-4", 4)[0], self.artifact_root)
        self.assertEqual(errors, [])
        self.assertEqual(len(normalized["hardware"]["gpu_uuids"]), 4)

    def test_three_repeat_statistics_use_median(self):
        records = self.validated([*self.reference_records(), *self.gpu_records()])
        summary = self.core.compare_evidence(records, self.policy)
        self.assertEqual(summary["candidates"]["gpu-1"]["wall_time_s"]["median"], 50.0)
        self.assertEqual(summary["candidates"]["gpu-1"]["eligible_successful_runs"], 3)

    def test_insufficient_repeats_status(self):
        records = self.validated([*self.reference_records(), *self.gpu_records(walls=(50.0, 51.0))])
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "INSUFFICIENT_REPEATS")

    def test_method_fingerprint_mismatch_blocks_numerical_gate(self):
        candidates = self.gpu_records()
        candidates[0]["scientific"]["method_fingerprint_id"] = "MF-DIFFERENT"
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        self.assertEqual(summary["candidates"]["gpu-1"]["numerical_equivalence"]["status"], "FAIL")

    def test_input_hash_mismatch_blocks_numerical_gate(self):
        candidates = self.gpu_records()
        candidates[1]["scientific"]["input_sha256"] = "2" * 64
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        self.assertEqual(summary["candidates"]["gpu-1"]["cpu_to_candidate_speedup"], None)

    def test_missing_build_identity_status(self):
        candidates = self.gpu_records()
        for record in candidates:
            record["engine"]["build_fingerprint_id"] = ""
        normalized = [self.core.validate_result(record, self.artifact_root)[0] for record in candidates]
        records = self.validated(self.reference_records()) + normalized
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "BUILD_IDENTITY_MISSING")

    def test_gpu_identity_conflict_status(self):
        candidates = self.gpu_records()
        candidates[2]["hardware"]["gpu_uuids"] = ["GPU-DIFFERENT"]
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "HARDWARE_IDENTITY_MISSING")

    def test_energy_mismatch_blocks_speedup(self):
        candidates = self.gpu_records()
        for record in candidates:
            record["scientific"]["results"]["energy_ev"] = -9.0
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        candidate = summary["candidates"]["gpu-1"]
        self.assertEqual(candidate["numerical_equivalence"]["status"], "FAIL")
        self.assertIsNone(candidate["cpu_to_candidate_speedup"])

    def test_force_mismatch_blocks_speedup(self):
        candidates = self.gpu_records()
        for record in candidates:
            record["scientific"]["results"]["forces_ev_per_angstrom"] = [0.1, 0.0, 0.0]
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        self.assertEqual(summary["candidates"]["gpu-1"]["numerical_equivalence"]["status"], "FAIL")

    def test_parser_rejection_status(self):
        candidates = [
            self.record("gpu-1", "acceleration-candidate", index, 50.0 + index, gpus=1, parser=False)
            for index in range(1, 4)
        ]
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "PARSER_NOT_ACCEPTED")

    def test_artifact_hash_mismatch_status(self):
        candidates = self.gpu_records()
        candidates[0]["artifacts"][0]["sha256"] = "0" * 64
        normalized = [self.core.validate_result(record, self.artifact_root)[0] for record in candidates]
        records = self.validated(self.reference_records()) + normalized
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "ARTIFACT_HASH_MISMATCH")

    def test_speedup_not_improved_status(self):
        records = self.validated([*self.reference_records(), *self.gpu_records(walls=(110.0, 111.0, 109.0))])
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "PERFORMANCE_NOT_IMPROVED")

    def test_multi_gpu_scaling_efficiency(self):
        records = self.validated(
            [*self.reference_records(), *self.gpu_records(), *self.gpu_records("gpu-4", 4, (20.0, 21.0, 19.0))]
        )
        summary = self.core.compare_evidence(records, self.policy)
        multi = summary["candidates"]["gpu-4"]
        self.assertAlmostEqual(multi["single_gpu_to_candidate_speedup"], 2.5)
        self.assertAlmostEqual(multi["strong_scaling_efficiency"], 0.625)

    def test_failed_runs_are_retained(self):
        failed = self.record("gpu-1", "acceleration-candidate", 4, 40.0, gpus=1, exit_status=1, parser=False)
        records = self.validated([*self.reference_records(), *self.gpu_records(), failed])
        summary = self.core.compare_evidence(records, self.policy)
        self.assertEqual(summary["candidates"]["gpu-1"]["failed_runs"], 1)
        with tempfile.TemporaryDirectory() as out:
            bundle = self.core.write_evidence_bundle(Path(out), records, summary, self.policy, self.approved_review())
            manifest = json.loads((Path(out) / "performance-evidence-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["failed_attempts_retained"], 1)
            self.assertTrue(bundle["ok"])

    def test_missing_optional_energy_field_is_allowed(self):
        record = self.reference_records()[0]
        record["performance"]["energy_joules"] = None
        _, errors, _ = self.core.validate_result(record, self.artifact_root)
        self.assertEqual(errors, [])

    def test_nvidia_smi_not_available_is_explicit(self):
        with patch.object(self.core.shutil, "which", return_value=None):
            availability = self.core.tool_availability()
        self.assertEqual(availability["nvidia-smi"], "NOT_AVAILABLE")

    def test_result_order_does_not_change_summary(self):
        records = self.validated([*self.reference_records(), *self.gpu_records()])
        forward = self.core.compare_evidence(records, self.policy)
        reverse = self.core.compare_evidence(list(reversed(records)), self.policy)
        self.assertEqual(forward, reverse)

    def test_fabricated_l3_label_is_rejected_by_contract(self):
        record = self.gpu_records()[0]
        record["support_level"] = "L3_EXECUTION_TESTED"
        normalized, errors, _ = self.core.validate_result(record, self.artifact_root)
        self.assertFalse(normalized["validation"]["ok"])
        self.assertTrue(any("Additional properties" in error or "support_level" in error for error in errors))

    def test_non_real_canonical_evidence_remains_l2_only(self):
        candidates = self.gpu_records()
        for record in candidates:
            record["evidence_source"]["kind"] = "test-fixture"
        records = self.validated([*self.reference_records(), *candidates])
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "L2_ONLY")

    def test_real_reviewed_evidence_can_be_scoped_qualified(self):
        records = self.validated([*self.reference_records(), *self.gpu_records()])
        summary = self.core.compare_evidence(records, self.policy)
        report = self.core.qualify_evidence(summary, self.policy, self.approved_review(), "a" * 64)
        self.assertEqual(
            report["candidates"]["gpu-1"]["status"],
            "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE",
        )
        self.assertFalse(report["public_capability_level_changed"])

    def test_pending_review_remains_l2_only(self):
        records = self.validated([*self.reference_records(), *self.gpu_records()])
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"],
            summary["reference_status"],
            self.policy,
            {"status": "pending"},
        )
        self.assertEqual(status, "L2_ONLY")

    def test_reference_missing_status(self):
        records = self.validated(self.gpu_records())
        summary = self.core.compare_evidence(records, self.policy)
        status, _ = self.core.candidate_qualification_status(
            summary["candidates"]["gpu-1"], summary["reference_status"], self.policy, self.approved_review()
        )
        self.assertEqual(status, "REFERENCE_MISSING")

    def test_yaml_json_jsonl_import(self):
        record = self.reference_records()[0]
        paths = []
        yaml_path = self.artifact_root / "record.yaml"
        yaml_path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        paths.append(yaml_path)
        json_path = self.artifact_root / "record.json"
        second = self.reference_records()[1]
        json_path.write_text(json.dumps(second), encoding="utf-8")
        paths.append(json_path)
        jsonl_path = self.artifact_root / "record.jsonl"
        third = self.reference_records()[2]
        jsonl_path.write_text(json.dumps(third) + "\n", encoding="utf-8")
        paths.append(jsonl_path)
        records, report = self.core.import_evidence(paths, self.artifact_root)
        self.assertTrue(report["ok"])
        self.assertEqual(len(records), 3)
        self.assertTrue(all(record["schema_version"] == "1.1" for record in records))

    def test_csv_dotted_field_import(self):
        path = self.artifact_root / "record.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["schema_version", "benchmark_plan_id", "candidate_id", "repeat_index"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "schema_version": "1.0",
                    "benchmark_plan_id": "PLAN-CSV",
                    "candidate_id": "candidate",
                    "repeat_index": "1",
                }
            )
        records = self.core.load_records(path)
        self.assertEqual(records[0]["repeat_index"], 1)

    def test_duplicate_run_identity_is_rejected(self):
        record = self.reference_records()[0]
        path = self.artifact_root / "duplicate.json"
        path.write_text(json.dumps([record, record]), encoding="utf-8")
        _, report = self.core.import_evidence([path], self.artifact_root)
        self.assertFalse(report["ok"])
        self.assertTrue(any("duplicate" in error for failure in report["failures"] for error in failure["errors"]))

    def test_bundle_contains_all_required_files_and_checksums(self):
        records = self.validated([*self.reference_records(), *self.gpu_records()])
        summary = self.core.compare_evidence(records, self.policy)
        with tempfile.TemporaryDirectory() as out:
            bundle = self.core.write_evidence_bundle(Path(out), records, summary, self.policy, self.approved_review())
            names = {Path(path).name for path in bundle["files"]}
            self.assertEqual(
                names,
                {
                    "benchmark-summary.json",
                    "benchmark-summary.md",
                    "performance-evidence-manifest.json",
                    "artifact-checksums.sha256",
                    "qualification-report.json",
                },
            )
            self.assertRegex(bundle["evidence_bundle_sha256"], r"^[0-9a-f]{64}$")

    def test_sacct_adapter(self):
        parsed = self.core.parse_optional_metric(
            "sacct",
            "JobID|State|ElapsedRaw|TotalCPU|MaxRSS\n123|COMPLETED|50|00:03:00|4096K\n",
        )
        self.assertEqual(parsed["status"], "AVAILABLE")
        self.assertEqual(parsed["wall_time_s"], 50.0)

    def test_time_v_adapter(self):
        parsed = self.core.parse_optional_metric(
            "time-v",
            "User time (seconds): 4\nSystem time (seconds): 1\nMaximum resident set size (kbytes): 2048\n",
        )
        self.assertEqual(parsed["cpu_time_s"], 5.0)
        self.assertEqual(parsed["status"], "AVAILABLE")

    def test_nvidia_smi_adapter(self):
        parsed = self.core.parse_optional_metric(
            "nvidia-smi",
            "NVIDIA H100, GPU-0, 00000000:01:00.0, 590.1, 81920 MiB, 85 %\n",
        )
        self.assertEqual(parsed["gpus"][0]["uuid"], "GPU-0")

    def test_invalid_profiler_summary_is_not_available(self):
        parsed = self.core.parse_optional_metric("nsight", "not-json")
        self.assertEqual(parsed["status"], "NOT_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
