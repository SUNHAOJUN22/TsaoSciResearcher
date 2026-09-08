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
from unittest.mock import patch

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"release_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseShellTrustCoverageTests(unittest.TestCase):
    shell: Any
    trust: Any
    policy: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = load_script("shell_contract.py")
        cls.trust = load_script("trust_boundary.py")
        cls.policy = yaml.safe_load(
            (ROOT / "templates/performance-qualification-policy.yaml").read_text(encoding="utf-8")
        )

    def base_manifest(self) -> dict[str, Any]:
        return yaml.safe_load((ROOT / "templates/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def signed_attestation(self, binding: dict[str, Any], scope: str) -> tuple[dict[str, Any], bytes]:
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        now = datetime.now(timezone.utc)
        attestation: dict[str, Any] = {
            "schema_version": "1.0",
            "attestation_id": "A-1",
            "identity": "reviewer@example.org",
            "decision": "approved",
            "scope": scope,
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "binding": binding,
            "signature_algorithm": "ed25519",
            "key_fingerprint": self.shell.public_key_fingerprint(public),
        }
        attestation["signature"] = base64.b64encode(
            private.sign(self.shell.canonical_json(attestation).encode("utf-8"))
        ).decode()
        return attestation, public

    def record(
        self,
        plan: str = "PLAN",
        candidate: str = "gpu",
        role: str = "acceleration-candidate",
    ) -> dict[str, Any]:
        return {
            "benchmark_plan_id": plan,
            "candidate_id": candidate,
            "role": role,
            "engine": {"name": "vasp", "version": "6.5", "build_fingerprint_id": "B"},
            "hardware": {
                "hardware_fingerprint_id": "H",
                "cpu_model": "CPU",
                "cpu_arch": "x86_64",
                "nodes": 1,
                "ranks_per_node": 1,
                "threads_per_rank": 8,
                "gpu_vendor": "nvidia",
                "gpu_model": "GPU",
                "gpu_uuids": ["G"],
                "driver_version": "D",
                "gpu_binding": "closest",
            },
            "scientific": {
                "input_sha256": "1" * 64,
                "method_fingerprint_id": "M",
                "model_identity": {"functional": "PBE"},
                "convergence_thresholds": {"e": 1e-6},
                "observable_set": ["forces", "energy"],
            },
        }

    def policy_candidate(self) -> dict[str, Any]:
        return {
            "build_identity_consistent": True,
            "hardware_identity_consistent": True,
            "parser_accepted_runs": 3,
            "total_runs": 3,
            "all_artifacts_verified": True,
            "minimum_repeats_pass": True,
            "numerical_equivalence": {"status": "PASS", "reasons": []},
            "cpu_to_candidate_speedup": 2.0,
            "strong_scaling_efficiency": 0.9,
            "resources": {"gpus_total": 4},
            "all_sources_real_engine": True,
        }

    def test_scalar_path_environment_and_argv_contracts(self) -> None:
        errors: list[str] = []
        self.assertEqual(self.shell.safe_scalar("JOB-1", "job", errors, job_name=True), "JOB-1")
        for value in ("", 7, "bad\nvalue", "bad value"):
            self.shell.safe_scalar(value, "scalar", errors)
        self.assertGreaterEqual(len(errors), 4)

        errors = []
        self.assertEqual(self.shell.safe_relative_path("run/input.dat", "path", errors), "run/input.dat")
        for value in ("", 2, "/absolute", "../escape", "bad\x00name"):
            self.shell.safe_relative_path(value, "path", errors)
        self.shell.safe_relative_path(".", "path", errors, allow_dot=False)
        self.assertGreaterEqual(len(errors), 5)

        errors = []
        self.assertEqual(self.shell.safe_env_name("OMP_NUM_THREADS", "env", errors), "OMP_NUM_THREADS")
        self.shell.safe_env_name("BAD-NAME", "env", errors)
        self.shell.safe_env_name(None, "env", errors)
        self.assertEqual(len(errors), 2)

        errors = []
        self.assertEqual(self.shell.validate_argv(["python", "a b.py"], "argv", errors), ["python", "a b.py"])
        for argv_value in (None, [], ["python", ""], ["python", 1], ["bad\narg"]):
            self.shell.validate_argv(argv_value, "argv", errors)
        self.assertGreaterEqual(len(errors), 5)
        self.assertEqual(self.shell.render_argv(["python", "a b.py"]), "python 'a b.py'")
        with self.assertRaises(ValueError):
            self.shell.render_argv([])

        errors = []
        self.assertEqual(self.shell.validate_module_or_source("cuda/13", "module", errors), "cuda/13")
        for value in ("", 1, "cuda;touch pwned", "bad\nmodule"):
            self.shell.validate_module_or_source(value, "module", errors)
        self.assertGreaterEqual(len(errors), 4)

    def test_hash_key_timestamp_and_attestation_edges(self) -> None:
        manifest = self.base_manifest()
        self.assertEqual(self.shell.manifest_binding_payload(manifest)["job_id"], manifest["job_id"])
        self.assertRegex(self.shell.manifest_sha256(manifest), r"^[0-9a-f]{64}$")
        self.assertRegex(self.shell.sha256_object({"b": 2, "a": 1}), r"^[0-9a-f]{64}$")

        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.assertRegex(self.shell.public_key_fingerprint(public), r"^[0-9a-f]{64}$")
        rsa_public = (
            generate_private_key(public_exponent=65537, key_size=2048)
            .public_key()
            .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        )
        with self.assertRaises(ValueError):
            self.shell.public_key_fingerprint(rsa_public)

        errors: list[str] = []
        self.assertIsNone(self.shell.parse_timestamp(None, "time", errors))
        self.assertIsNone(self.shell.parse_timestamp("not-time", "time", errors))
        self.assertIsNone(self.shell.parse_timestamp("2026-01-01T00:00:00", "time", errors))
        self.assertEqual(
            self.shell.parse_timestamp("2026-01-01T00:00:00Z", "time", errors),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertGreaterEqual(len(errors), 3)

        expected = {"manifest_sha256": "a" * 64}
        valid, public = self.signed_attestation(expected, "execute-reviewed-manifest")
        now = datetime.now(timezone.utc)
        self.assertEqual(self.shell.verify_signed_attestation(valid, public, expected, now=now), [])
        self.assertTrue(self.shell.verify_signed_attestation({}, public, expected, now=now))

        cases: list[dict[str, Any]] = []
        for key, value in (
            ("schema_version", "2.0"),
            ("signature_algorithm", "rsa"),
            ("identity", ""),
            ("key_fingerprint", "0" * 64),
            ("signature", 4),
            ("signature", "not-base64***"),
        ):
            case = copy.deepcopy(valid)
            case[key] = value
            cases.append(case)
        future = copy.deepcopy(valid)
        future["issued_at"] = (now + timedelta(days=1)).isoformat()
        cases.append(future)
        expired = copy.deepcopy(valid)
        expired["expires_at"] = (now - timedelta(days=1)).isoformat()
        cases.append(expired)
        nonmapping = copy.deepcopy(valid)
        nonmapping["binding"] = []
        cases.append(nonmapping)
        mismatch = copy.deepcopy(valid)
        mismatch["binding"]["manifest_sha256"] = "b" * 64
        cases.append(mismatch)
        for case in cases:
            self.assertTrue(self.shell.verify_signed_attestation(case, public, expected, now=now))

        self.assertTrue(self.shell.verify_signed_attestation(valid, b"not-a-key", expected, now=now))
        other = (
            Ed25519PrivateKey.generate()
            .public_key()
            .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        )
        self.assertTrue(self.shell.verify_signed_attestation(valid, other, expected, now=now))

    def test_schema_policy_identity_and_plan_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            json_path = root / "x.json"
            yaml_path = root / "x.yaml"
            json_path.write_text('{"a": 1}', encoding="utf-8")
            yaml_path.write_text("a: 1\n", encoding="utf-8")
            self.assertEqual(self.trust.load_json(json_path), {"a": 1})
            self.assertEqual(self.trust.load_yaml(yaml_path), {"a": 1})
            json_path.write_text("[]", encoding="utf-8")
            yaml_path.write_text("- x\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.trust.load_json(json_path)
            with self.assertRaises(ValueError):
                self.trust.load_yaml(yaml_path)

        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
        self.assertEqual(self.trust.schema_errors({"a": 1}, schema), [])
        self.assertTrue(self.trust.schema_errors({"a": "x"}, schema))
        self.assertEqual(self.trust.validate_record_schema({}, {"type": "object"}), [])

        policy_schema = json.loads(
            (ROOT / "templates/performance-qualification-policy.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.trust.validate_policy(self.policy, policy_schema), [])
        modified = copy.deepcopy(self.policy)
        modified["unknown"] = True
        modified["acceleration_l3_required_evidence"] = ["engine"]
        policy_errors = self.trust.validate_policy(modified, policy_schema)
        self.assertTrue(any("unsupported" in error for error in policy_errors))
        self.assertTrue(any("executable contract" in error for error in policy_errors))

        first = self.record()
        self.assertRegex(self.trust.scientific_identity_digest(first), r"^[0-9a-f]{64}$")
        self.assertRegex(self.trust.topology_digest(first), r"^[0-9a-f]{64}$")
        self.assertTrue(self.trust.isolate_benchmark_plan([])[1])
        self.assertTrue(self.trust.isolate_benchmark_plan([self.record("A"), self.record("B")])[1])

        changed = self.record()
        changed["hardware"]["driver_version"] = "other"
        plan, isolation_errors = self.trust.isolate_benchmark_plan([first, changed])
        self.assertEqual(plan, "PLAN")
        self.assertTrue(isolation_errors)

        reference = self.record(candidate="cpu", role="scientific-reference")
        self.assertTrue(self.trust.isolate_benchmark_plan([reference])[1])
        reference["hardware"]["gpu_uuids"] = []
        self.assertEqual(self.trust.isolate_benchmark_plan([reference]), ("PLAN", []))

        summary = {
            "benchmark_plan_id": "PLAN",
            "candidates": {
                "cpu": {"role": "scientific-reference"},
                "gpu": {"role": "acceleration-candidate"},
            },
        }
        payload = self.trust.prequalification_payload([reference], summary, self.policy)
        self.assertEqual(payload["candidate_ids"], ["gpu"])
        self.assertEqual(set(self.trust.build_root_manifest({"a": b"one", "b": b"two"})["files"]), {"a", "b"})

    def test_policy_status_paths(self) -> None:
        policy = copy.deepcopy(self.policy)
        candidate = self.policy_candidate()
        self.assertEqual(self.trust.enforce_policy(candidate, "FAIL", policy, [])[0], "REFERENCE_MISSING")
        for field, value, expected in (
            ("build_identity_consistent", False, "BUILD_IDENTITY_MISSING"),
            ("hardware_identity_consistent", False, "HARDWARE_IDENTITY_MISSING"),
            ("all_artifacts_verified", False, "ARTIFACT_HASH_MISMATCH"),
            ("minimum_repeats_pass", False, "INSUFFICIENT_REPEATS"),
        ):
            case = self.policy_candidate()
            case[field] = value
            self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], expected)

        case = self.policy_candidate()
        case["parser_accepted_runs"] = 1
        self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], "PARSER_NOT_ACCEPTED")
        case = self.policy_candidate()
        case["total_runs"] = 1
        case["parser_accepted_runs"] = 1
        case["minimum_repeats_pass"] = False
        self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], "INSUFFICIENT_REPEATS")
        case = self.policy_candidate()
        case["numerical_equivalence"] = {"status": "FAIL", "reasons": ["bad"]}
        self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], "NUMERICAL_MISMATCH")
        case = self.policy_candidate()
        case["cpu_to_candidate_speedup"] = 1.0
        self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], "PERFORMANCE_NOT_IMPROVED")
        case = self.policy_candidate()
        case["strong_scaling_efficiency"] = 0.1
        policy["performance"]["minimum_strong_scaling_efficiency"] = 0.5
        self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], "PERFORMANCE_POLICY_FAILED")

        policy = copy.deepcopy(self.policy)
        case = self.policy_candidate()
        case["all_sources_real_engine"] = False
        self.assertEqual(self.trust.enforce_policy(case, "PASS", policy, [])[0], "L2_ONLY")
        self.assertEqual(self.trust.enforce_policy(self.policy_candidate(), "PASS", policy, ["bad"])[0], "L2_ONLY")
        self.assertEqual(
            self.trust.enforce_policy(self.policy_candidate(), "PASS", policy, [])[0],
            "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE",
        )

        policy["require_verified_artifacts"] = False
        policy["require_performance_improvement"] = False
        policy["require_real_engine_source"] = False
        policy["require_independent_review"] = False
        case = self.policy_candidate()
        case["all_artifacts_verified"] = False
        case["cpu_to_candidate_speedup"] = None
        case["all_sources_real_engine"] = False
        self.assertEqual(
            self.trust.enforce_policy(case, "PASS", policy, ["ignored"])[0],
            "QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE",
        )

    def test_review_and_bundle_error_paths(self) -> None:
        root_digest = "a" * 64
        binding = {
            "policy_id": self.policy["policy_id"],
            "benchmark_plan_id": "PLAN",
            "candidate_ids": ["gpu"],
            "evidence_root_sha256": root_digest,
        }
        review, public = self.signed_attestation(binding, "scoped-performance-evidence")
        self.assertEqual(
            self.trust.verify_review(
                review,
                public,
                root_digest,
                self.policy["policy_id"],
                "PLAN",
                ["gpu"],
            ),
            [],
        )
        wrong = copy.deepcopy(review)
        wrong["decision"] = "rejected"
        wrong["scope"] = "other"
        errors = self.trust.verify_review(
            wrong,
            public,
            root_digest,
            self.policy["policy_id"],
            "PLAN",
            ["gpu"],
        )
        self.assertTrue(any("decision" in error for error in errors))
        self.assertTrue(any("scope" in error for error in errors))

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            result = self.trust.publish_content_addressed_bundle(
                parent,
                [self.record()],
                {},
                self.policy,
                review,
                {},
            )
            bundle = Path(result["out_dir"])
            reused = self.trust.publish_content_addressed_bundle(
                parent,
                [self.record()],
                {},
                self.policy,
                review,
                {},
            )
            self.assertTrue(reused["reused"])

            missing = parent / "evidence-missing"
            missing.mkdir()
            self.assertFalse(self.trust.verify_content_addressed_bundle(missing)["ok"])

            bad_json = parent / "evidence-bad"
            bad_json.mkdir()
            (bad_json / "evidence-root.json").write_text("{", encoding="utf-8")
            self.assertFalse(self.trust.verify_content_addressed_bundle(bad_json)["ok"])

            renamed = parent / "renamed"
            bundle.rename(renamed)
            self.assertFalse(self.trust.verify_content_addressed_bundle(renamed)["ok"])
            renamed.rename(bundle)

            root_path = bundle / "evidence-root.json"
            root_doc = json.loads(root_path.read_text(encoding="utf-8"))
            original = copy.deepcopy(root_doc)
            root_doc["files"] = []
            root_path.write_text(json.dumps(root_doc), encoding="utf-8")
            self.assertFalse(self.trust.verify_content_addressed_bundle(bundle)["ok"])
            root_path.write_text(json.dumps(original, sort_keys=True, indent=2) + "\n", encoding="utf-8")

            extra = bundle / "extra.txt"
            extra.write_text("extra", encoding="utf-8")
            self.assertFalse(self.trust.verify_content_addressed_bundle(bundle)["ok"])
            extra.unlink()

            records_path = bundle / "records.json"
            content = records_path.read_bytes()
            records_path.write_bytes(content + b"x")
            self.assertFalse(self.trust.verify_content_addressed_bundle(bundle)["ok"])
            records_path.write_bytes(content)

            original["files"]["records.json"]["size_bytes"] += 1
            root_path.write_text(json.dumps(original, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            self.assertFalse(self.trust.verify_content_addressed_bundle(bundle)["ok"])

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with (
                patch.object(self.trust.os, "replace", side_effect=OSError("replace failed")),
                self.assertRaises(OSError),
            ):
                self.trust.publish_content_addressed_bundle(
                    parent,
                    [self.record()],
                    {},
                    self.policy,
                    review,
                    {},
                )
            self.assertFalse(any(parent.iterdir()))


if __name__ == "__main__":
    unittest.main()
