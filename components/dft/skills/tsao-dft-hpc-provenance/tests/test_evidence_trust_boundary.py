from __future__ import annotations

import base64
import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hypothesis import given
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"trust_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidenceTrustBoundaryTests(unittest.TestCase):
    trust: Any
    shell: Any
    performance: Any
    result_schema: dict[str, Any]
    policy_schema: dict[str, Any]
    policy: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.trust = load_script("trust_boundary.py")
        cls.shell = load_script("shell_contract.py")
        cls.performance = load_script("performance_evidence.py")
        cls.result_schema = json.loads((ROOT / "templates/benchmark-result.schema.json").read_text(encoding="utf-8"))
        cls.policy_schema = json.loads(
            (ROOT / "templates/performance-qualification-policy.schema.json").read_text(encoding="utf-8")
        )
        cls.policy = yaml.safe_load(
            (ROOT / "templates/performance-qualification-policy.yaml").read_text(encoding="utf-8")
        )

    def record(self, plan: str = "PLAN-A", candidate: str = "gpu-1", repeat: int = 1) -> dict[str, Any]:
        return {
            "schema_version": "1.1",
            "benchmark_plan_id": plan,
            "candidate_id": candidate,
            "role": "acceleration-candidate",
            "repeat_index": repeat,
            "engine": {"name": "vasp", "version": "6.5.1", "executable": "vasp_std", "build_fingerprint_id": "BUILD-A"},
            "software": {"compiler": "nvhpc", "mpi": "openmpi", "openmp_runtime": "omp", "accelerator_runtime": "cuda"},
            "hardware": {
                "site_id": "SITE-A",
                "hardware_fingerprint_id": "HW-A",
                "cpu_model": "EPYC",
                "cpu_arch": "x86_64",
                "nodes": 1,
                "ranks_per_node": 1,
                "threads_per_rank": 8,
                "gpu_vendor": "nvidia",
                "gpu_model": "H100",
                "gpu_uuids": ["GPU-A"],
                "gpu_memory_gb": 80,
                "driver_version": "590",
                "gpu_binding": "closest",
            },
            "execution": {
                "scheduler": "slurm",
                "job_id": "JOB-1",
                "run_id": f"RUN-{repeat}",
                "site_id": "SITE-A",
                "filesystem": "lustre",
                "scratch_type": "nvme",
                "timestamp": "2026-07-29T00:00:00Z",
                "exit_status": 0,
            },
            "scientific": {
                "input_sha256": "1" * 64,
                "method_fingerprint_id": "MF-A",
                "model_identity": {
                    "functional": "PBE",
                    "basis_or_pseudopotential": "POTCAR-HASH",
                    "corrections": "none",
                },
                "convergence_thresholds": {"ediff": 1e-6},
                "observable_set": ["energy", "forces"],
                "parser_accepted": True,
                "parser_status": "ACCEPTED",
                "results": {
                    "energy_ev": -10.0,
                    "forces_ev_per_angstrom": [0.0, 0.0, 0.0],
                    "stress_gpa": None,
                    "properties": {},
                },
            },
            "performance": {
                "wall_time_s": 50.0,
                "cpu_time_s": 10.0,
                "scf_iterations": 10,
                "peak_host_memory_mb": 1000.0,
                "peak_device_memory_mb": 2000.0,
                "cpu_utilization_percent": 50.0,
                "gpu_utilization_percent": 80.0,
                "io_bytes": 100,
                "energy_joules": None,
            },
            "artifacts": [{"path": "OUTCAR", "sha256": "2" * 64}],
            "evidence_source": {"kind": "real-engine", "source_id": f"RUN-{repeat}", "missing_fields": []},
        }

    def test_schema_rejects_float_integer_and_bad_timestamp(self):
        record = self.record()
        record["repeat_index"] = 1.5
        record["execution"]["timestamp"] = "not-a-date"
        errors = self.trust.validate_record_schema(record, self.result_schema)
        self.assertTrue(any("repeat_index" in error for error in errors))
        self.assertTrue(any("timestamp" in error for error in errors))

    def test_schema_rejects_unknown_engine_and_duplicate_observable(self):
        record = self.record()
        record["engine"]["name"] = "made-up"
        record["scientific"]["observable_set"] = ["energy", "energy"]
        errors = self.trust.validate_record_schema(record, self.result_schema)
        self.assertTrue(any("engine" in error for error in errors))
        self.assertTrue(any("non-unique" in error for error in errors))

    def test_multi_plan_is_rejected(self):
        plan, errors = self.trust.isolate_benchmark_plan([self.record("A"), self.record("B")])
        self.assertIsNone(plan)
        self.assertTrue(errors)

    def test_cross_topology_candidate_is_rejected(self):
        first = self.record()
        second = self.record(repeat=2)
        second["hardware"]["driver_version"] = "different"
        _, errors = self.trust.isolate_benchmark_plan([first, second])
        self.assertTrue(any("mixes" in error for error in errors))

    def test_policy_schema_and_supported_fields(self):
        self.assertEqual(self.trust.validate_policy(self.policy, self.policy_schema), [])
        policy = dict(self.policy)
        policy["ignored_switch"] = True
        self.assertTrue(self.trust.validate_policy(policy, self.policy_schema))

    def test_strong_scaling_policy_is_executable(self):
        candidate = {
            "build_identity_consistent": True,
            "hardware_identity_consistent": True,
            "parser_accepted_runs": 3,
            "total_runs": 3,
            "all_artifacts_verified": True,
            "minimum_repeats_pass": True,
            "numerical_equivalence": {"status": "PASS"},
            "cpu_to_candidate_speedup": 2.0,
            "strong_scaling_efficiency": 0.5,
            "resources": {"gpus_total": 4},
            "all_sources_real_engine": True,
        }
        policy = copy.deepcopy(self.policy)
        policy["performance"]["minimum_strong_scaling_efficiency"] = 0.8
        status, _ = self.trust.enforce_policy(candidate, "PASS", policy, [])
        self.assertEqual(status, "PERFORMANCE_POLICY_FAILED")

    def signed_review(self, root_digest: str, candidate_ids: list[str]) -> tuple[dict[str, Any], bytes]:
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        now = datetime.now(timezone.utc)
        review = {
            "schema_version": "1.0",
            "attestation_id": "REVIEW-1",
            "identity": "reviewer@example.org",
            "decision": "approved",
            "scope": "scoped-performance-evidence",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "binding": {
                "policy_id": self.policy["policy_id"],
                "benchmark_plan_id": "PLAN-A",
                "candidate_ids": candidate_ids,
                "evidence_root_sha256": root_digest,
            },
            "signature_algorithm": "ed25519",
            "key_fingerprint": self.shell.public_key_fingerprint(public),
        }
        review["signature"] = base64.b64encode(private.sign(self.shell.canonical_json(review).encode())).decode()
        return review, public

    def test_signed_review_is_bound_and_forgery_rejected(self):
        review, public = self.signed_review("a" * 64, ["gpu-1"])
        self.assertEqual(
            self.trust.verify_review(review, public, "a" * 64, self.policy["policy_id"], "PLAN-A", ["gpu-1"]), []
        )
        review["binding"]["candidate_ids"] = ["gpu-2"]
        self.assertTrue(
            self.trust.verify_review(review, public, "a" * 64, self.policy["policy_id"], "PLAN-A", ["gpu-1"])
        )

    def test_empty_reviewer_expired_and_wrong_digest_are_rejected(self):
        review, public = self.signed_review("a" * 64, ["gpu-1"])
        review["identity"] = ""
        review["binding"]["evidence_root_sha256"] = "b" * 64
        review["expires_at"] = "2000-01-01T00:00:00+00:00"
        self.assertTrue(
            self.trust.verify_review(review, public, "a" * 64, self.policy["policy_id"], "PLAN-A", ["gpu-1"])
        )

    def test_content_addressed_bundle_detects_all_tampering(self):
        review, _ = self.signed_review("a" * 64, ["gpu-1"])
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            bundle = self.trust.publish_content_addressed_bundle(
                parent, [self.record()], {"benchmark_plan_id": "PLAN-A"}, self.policy, review, {"ok": True}
            )
            path = Path(bundle["out_dir"])
            self.assertTrue(self.trust.verify_content_addressed_bundle(path)["ok"])
            (path / "qualification-report.json").write_text("{}\n", encoding="utf-8")
            self.assertFalse(self.trust.verify_content_addressed_bundle(path)["ok"])

    def test_nonempty_content_address_collision_is_rejected(self):
        review, _ = self.signed_review("a" * 64, ["gpu-1"])
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            bundle = self.trust.publish_content_addressed_bundle(parent, [self.record()], {}, self.policy, review, {})
            path = Path(bundle["out_dir"])
            (path / "records.json").write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.trust.publish_content_addressed_bundle(parent, [self.record()], {}, self.policy, review, {})

    @given(st.lists(st.text(max_size=8), min_size=0, max_size=5))
    def test_schema_fuzz_never_crashes(self, values: list[str]) -> None:
        record = self.record()
        record["scientific"]["observable_set"] = values
        errors = self.trust.validate_record_schema(record, self.result_schema)
        self.assertIsInstance(errors, list)


if __name__ == "__main__":
    unittest.main()
