import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_research_manifest import (  # noqa: E402 -- test import follows explicit scripts path setup
    validate_manifest,
)


class ResearchManifestTests(unittest.TestCase):
    def base_manifest(self):
        return {
            "schema_version": "1.0",
            "project_id": "p1",
            "research_question": "Is A a minimum?",
            "calculations": [
                {
                    "id": "c1",
                    "task_type": "minimum",
                    "status": "accepted",
                    "method": "wB97X-D",
                    "basis": "def2-SVP",
                    "charge": 0,
                    "multiplicity": 1,
                    "phase_or_solvent": "gas",
                    "temperature_K": 298.15,
                    "structure_sha256": "b" * 64,
                    "artifact_ids": ["a1"],
                    "validation": {
                        "normal_termination": True,
                        "scf_converged": True,
                        "optimization_converged": True,
                        "imaginary_frequency_count": 0,
                    },
                }
            ],
            "artifacts": [
                {
                    "id": "a1",
                    "calculation_id": "c1",
                    "kind": "gaussian_log",
                    "path": "c1.log",
                    "sha256": "a" * 64,
                    "source_type": "calculation",
                    "status": "accepted",
                }
            ],
            "claims": [
                {
                    "id": "cl1",
                    "text": "A is a minimum.",
                    "scope": "model",
                    "evidence_grade": "A",
                    "artifact_ids": ["a1"],
                    "limitations": ["static"],
                    "falsification_condition": "imaginary mode",
                    "paper_ready": True,
                    "is_mock": False,
                }
            ],
        }

    def test_valid_grade_a(self):
        errors, _ = validate_manifest(self.base_manifest())
        self.assertEqual(errors, [])

    def test_grade_a_requires_accepted_artifact(self):
        data = self.base_manifest()
        data["artifacts"][0]["status"] = "validated"
        errors, _ = validate_manifest(data)
        self.assertTrue(any("grade A" in error for error in errors))

    def test_ts_requires_distinct_validated_irc(self):
        data = self.base_manifest()
        data["calculations"][0].update(
            {
                "task_type": "transition_state",
                "validation": {
                    "normal_termination": True,
                    "scf_converged": True,
                    "optimization_converged": True,
                    "imaginary_frequency_count": 1,
                    "mode_reviewed": True,
                    "irc_forward_artifact_id": "a1",
                    "irc_reverse_artifact_id": "a1",
                    "irc_endpoints_confirmed": True,
                },
            }
        )
        errors, _ = validate_manifest(data)
        self.assertTrue(any("must be different" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
