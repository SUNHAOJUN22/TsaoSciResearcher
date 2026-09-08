from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> Any:
    path = ROOT / "scripts" / "validate_capability_claims.py"
    spec = importlib.util.spec_from_file_location("tsao_validate_capability_claims", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


class CapabilityClaimTests(unittest.TestCase):
    def test_current_repository_claim_contract(self) -> None:
        self.assertEqual(validator.validate(ROOT), [])

    def make_fixture(
        self,
        root: Path,
        *,
        level: str = "L2_VALIDATED_ADAPTER",
        phrase: str = "",
        capability_id: str = "fixture",
    ) -> None:
        (root / "docs").mkdir()
        (root / "skills" / "fixture" / "scripts").mkdir(parents=True)
        (root / "skills" / "fixture" / "scripts" / "run.py").write_text("pass\n", encoding="utf-8")
        (root / "skills" / "fixture" / "SKILL.md").write_text(f"fixture {phrase}\n", encoding="utf-8")
        (root / "VERSION").write_text("0.4.0-alpha.1\n", encoding="utf-8")
        policy = {
            "schema_version": "1.0",
            "release": "0.4.0-alpha.1",
            "support_levels": [
                "L0_REFERENCE",
                "L1_HANDOFF",
                "L2_VALIDATED_ADAPTER",
                "L3_EXECUTION_TESTED",
            ],
            "l3_required_evidence": ["engine", "version", "site", "run_id", "artifact_sha256"],
            "acceleration_l3_required_evidence": sorted(validator.ACCELERATION_L3_REQUIRED),
            "required_boundaries": [
                "signed review attestation must bind policy plan candidates and evidence root",
                "content addressed evidence root must verify every formal bundle file",
                "scoped L3 performance eligibility does not automatically change the public capability level",
            ],
            "forbidden_claim_phrases": [
                "DFT proves catalyst performance",
                "parser tests prove real engine execution",
                "AI-generated computational result",
                "scheduler success proves the mechanism",
                "high R2 proves causality",
            ],
        }
        capability = {
            "schema_version": "1.0",
            "release": "0.4.0-alpha.1",
            "capabilities": [
                {
                    "id": capability_id,
                    "skill": "fixture",
                    "status": "implemented",
                    "support_level": level,
                    "scripts": ["run.py"],
                    "external_requirements": [],
                }
            ],
        }
        (root / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml").write_text(
            yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
        )
        (root / "docs" / "CAPABILITY_STATUS.yaml").write_text(
            yaml.safe_dump(capability, sort_keys=False), encoding="utf-8"
        )
        for name in ("README.md", "README_EN.md"):
            (root / name).write_text(
                "L2_VALIDATED_ADAPTER and L3_EXECUTION_TESTED are distinct.\n",
                encoding="utf-8",
            )

    def load_fixture(self, root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        policy = yaml.safe_load((root / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml").read_text(encoding="utf-8"))
        capability = yaml.safe_load((root / "docs" / "CAPABILITY_STATUS.yaml").read_text(encoding="utf-8"))
        return policy, capability

    def save_fixture(self, root: Path, policy: dict[str, Any], capability: dict[str, Any]) -> None:
        (root / "docs" / "SCIENTIFIC_CLAIM_POLICY.yaml").write_text(
            yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
        )
        (root / "docs" / "CAPABILITY_STATUS.yaml").write_text(
            yaml.safe_dump(capability, sort_keys=False), encoding="utf-8"
        )

    def valid_generic_evidence(self) -> dict[str, Any]:
        return {
            "engine": "vasp",
            "version": "6.5",
            "site": "site-a",
            "run_id": "run-a",
            "artifact_sha256": "a" * 64,
        }

    def valid_acceleration_evidence(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {field: "recorded" for field in validator.ACCELERATION_L3_REQUIRED}
        evidence.update(
            {
                "artifact_sha256": "b" * 64,
                "evidence_bundle_sha256": "c" * 64,
                "evidence_root_sha256": "d" * 64,
                "run_ids": ["run-a", "run-b", "run-c"],
                "minimum_repeats": 3,
                "numerical_equivalence_pass": True,
                "parser_acceptance_pass": True,
                "performance_policy_pass": True,
                "review_signature_verified": True,
                "independent_review_approved": True,
            }
        )
        return evidence

    def test_l3_requires_immutable_execution_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, level="L3_EXECUTION_TESTED")
            failures = validator.validate(root)
            self.assertTrue(any("lacks execution_evidence" in item for item in failures), failures)

    def test_incomplete_acceleration_policy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            policy, capability = self.load_fixture(root)
            policy["acceleration_l3_required_evidence"].remove("review_signature_verified")
            self.save_fixture(root, policy, capability)
            failures = validator.validate(root)
            self.assertTrue(any("incomplete signed acceleration L3" in item for item in failures), failures)

    def test_hpc_l3_requires_signed_acceleration_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, level="L3_EXECUTION_TESTED", capability_id="hpc")
            policy, capability = self.load_fixture(root)
            capability["capabilities"][0]["execution_evidence"] = self.valid_generic_evidence()
            self.save_fixture(root, policy, capability)
            failures = validator.validate(root)
            self.assertTrue(any("lacks acceleration_execution_evidence" in item for item in failures), failures)

            capability["capabilities"][0]["acceleration_execution_evidence"] = self.valid_acceleration_evidence()
            self.save_fixture(root, policy, capability)
            self.assertEqual(validator.validate(root), [])

    def test_invalid_acceleration_review_and_digest_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, level="L3_EXECUTION_TESTED", capability_id="hpc")
            policy, capability = self.load_fixture(root)
            capability["capabilities"][0]["execution_evidence"] = self.valid_generic_evidence()
            evidence = self.valid_acceleration_evidence()
            evidence["evidence_root_sha256"] = "bad"
            evidence["review_signature_verified"] = False
            evidence["independent_review_approved"] = False
            capability["capabilities"][0]["acceleration_execution_evidence"] = evidence
            self.save_fixture(root, policy, capability)
            failures = validator.validate(root)
            self.assertTrue(any("evidence_root_sha256" in item for item in failures), failures)
            self.assertTrue(any("review_signature_verified must be true" in item for item in failures), failures)
            self.assertTrue(any("independent_review_approved must be true" in item for item in failures), failures)

    def test_l2_cannot_carry_acceleration_execution_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, capability_id="hpc")
            policy, capability = self.load_fixture(root)
            capability["capabilities"][0]["acceleration_execution_evidence"] = self.valid_acceleration_evidence()
            self.save_fixture(root, policy, capability)
            failures = validator.validate(root)
            self.assertTrue(any("non-L3 capability must not carry acceleration" in item for item in failures), failures)

    def test_forbidden_public_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, phrase="DFT proves catalyst performance")
            failures = validator.validate(root)
            self.assertTrue(any("forbidden unsupported claim" in item for item in failures), failures)


if __name__ == "__main__":
    unittest.main()
