from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_research_manifest.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("release_research_manifest_coverage", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseResearchManifestCoverageTests(unittest.TestCase):
    validator: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()

    def base_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "project_id": "project-1",
            "research_question": "Is A a minimum?",
            "calculations": [
                {
                    "id": "calc-1",
                    "task_type": "minimum",
                    "status": "accepted",
                    "method": "wB97X-D",
                    "basis": "def2-SVP",
                    "charge": 0,
                    "multiplicity": 1,
                    "phase_or_solvent": "gas",
                    "temperature_K": 298.15,
                    "structure_sha256": "b" * 64,
                    "artifact_ids": ["art-1"],
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
                    "id": "art-1",
                    "calculation_id": "calc-1",
                    "kind": "gaussian_log",
                    "path": "calc-1.log",
                    "sha256": "a" * 64,
                    "source_type": "calculation",
                    "status": "accepted",
                }
            ],
            "claims": [
                {
                    "id": "claim-1",
                    "text": "A is a minimum.",
                    "scope": "specified model chemistry",
                    "evidence_grade": "A",
                    "artifact_ids": ["art-1"],
                    "limitations": ["static model"],
                    "falsification_condition": "a reproducible imaginary mode appears",
                    "paper_ready": True,
                    "is_mock": False,
                }
            ],
        }

    def assert_error(self, data: Any, fragment: str) -> None:
        errors, _ = self.validator.validate_manifest(data)
        self.assertTrue(any(fragment in error for error in errors), (fragment, errors))

    def assert_warning(self, data: Any, fragment: str) -> None:
        _, warnings = self.validator.validate_manifest(data)
        self.assertTrue(any(fragment in warning for warning in warnings), (fragment, warnings))

    def test_root_and_collection_contracts(self) -> None:
        self.assert_error([], "root must be an object")
        data: dict[str, Any] = {"calculations": {}, "artifacts": {}, "claims": {}}
        errors, warnings = self.validator.validate_manifest(data)
        self.assertTrue(any("project_id" in error for error in errors))
        self.assertTrue(any("research_question" in error for error in errors))
        self.assertTrue(any("calculations must be an array" in error for error in errors))
        self.assertTrue(any("artifacts must be an array" in error for error in errors))
        self.assertTrue(any("claims must be an array" in error for error in errors))
        self.assertIn("root: schema_version is missing", warnings)

    def test_calculation_scalar_and_identity_boundaries(self) -> None:
        data = self.base_manifest()
        data["calculations"] = ["bad"]
        self.assert_error(data, "calculations[0]: must be an object")

        cases: list[tuple[str, Any, str]] = [
            ("task_type", "unknown", "unknown task_type"),
            ("status", "unknown", "unknown status"),
            ("charge", 0.5, "charge must be an integer"),
            ("multiplicity", 0, "multiplicity must be a positive integer"),
            ("temperature_K", 0, "temperature_K must be positive"),
            ("structure_sha256", "ABC", "structure_sha256 must be 64 lowercase"),
        ]
        for field, value, fragment in cases:
            with self.subTest(field=field):
                item = self.base_manifest()
                item["calculations"][0][field] = value
                self.assert_error(item, fragment)

        missing_hash = self.base_manifest()
        missing_hash["calculations"][0].pop("structure_sha256")
        self.assert_warning(missing_hash, "structure_sha256 is not recorded")

        duplicate = self.base_manifest()
        duplicate["calculations"].append(copy.deepcopy(duplicate["calculations"][0]))
        self.assert_error(duplicate, "duplicate calculation id")

        single_point = self.base_manifest()
        single_point["calculations"][0]["task_type"] = "single_point"
        self.assert_error(single_point, "single_point requires parent_id")

        thermo = self.base_manifest()
        thermo["calculations"][0]["task_type"] = "thermochemistry"
        _, warnings = self.validator.validate_manifest(thermo)
        self.assertTrue(any("reference_state is missing" in warning for warning in warnings))
        self.assertTrue(any("standard_state is missing" in warning for warning in warnings))

    def test_accepted_calculation_validation_boundaries(self) -> None:
        invalid_object = self.base_manifest()
        invalid_object["calculations"][0]["validation"] = []
        errors, _ = self.validator.validate_manifest(invalid_object)
        self.assertTrue(any("requires validation object" in error for error in errors))
        self.assertTrue(any("normal_termination" in error for error in errors))
        self.assertTrue(any("scf_converged" in error for error in errors))

        cases: list[tuple[str, Any, str]] = [
            ("normal_termination", False, "normal_termination=true"),
            ("scf_converged", False, "scf_converged=true"),
            ("optimization_converged", False, "optimization_converged=true"),
            ("imaginary_frequency_count", 1, "zero imaginary frequencies"),
        ]
        for field, value, fragment in cases:
            with self.subTest(field=field):
                data = self.base_manifest()
                data["calculations"][0]["validation"][field] = value
                self.assert_error(data, fragment)

        no_artifacts = self.base_manifest()
        no_artifacts["calculations"][0]["artifact_ids"] = []
        self.assert_error(no_artifacts, "must link artifact_ids")

    def test_transition_state_and_open_shell_boundaries(self) -> None:
        data = self.base_manifest()
        calc = data["calculations"][0]
        calc["task_type"] = "transition_state"
        calc["multiplicity"] = 3
        calc["artifact_ids"] = ["forward", "reverse"]
        calc["validation"] = {
            "normal_termination": True,
            "scf_converged": True,
            "optimization_converged": True,
            "imaginary_frequency_count": 0,
            "mode_reviewed": False,
            "irc_forward_artifact_id": "forward",
            "irc_reverse_artifact_id": "forward",
            "irc_endpoints_confirmed": False,
            "wavefunction_stable": False,
            "s2_after": 5.0,
        }
        data["artifacts"] = [
            {
                "id": "forward",
                "calculation_id": "calc-1",
                "kind": "text",
                "path": "forward.log",
                "sha256": "c" * 64,
                "source_type": "calculation",
                "status": "raw",
            },
            {
                "id": "reverse",
                "calculation_id": "calc-1",
                "kind": "irc_reverse",
                "path": "reverse.log",
                "sha256": "d" * 64,
                "source_type": "calculation",
                "status": "validated",
            },
        ]
        data["claims"][0]["artifact_ids"] = ["forward"]
        errors, warnings = self.validator.validate_manifest(data)
        fragments = (
            "exactly one imaginary frequency",
            "mode_reviewed=true",
            "must be different",
            "irc_endpoints_confirmed=true",
            "wavefunction_stable=true",
            "incompatible kind",
        )
        for fragment in fragments:
            self.assertTrue(any(fragment in error for error in errors), (fragment, errors))
        self.assertTrue(any("spin contamination" in warning for warning in warnings))

        unvalidated = copy.deepcopy(data)
        unvalidated["calculations"][0]["validation"]["irc_reverse_artifact_id"] = "reverse"
        unvalidated["artifacts"][0]["kind"] = "irc_forward"
        self.assert_error(unvalidated, "is not validated")

        missing_irc = self.base_manifest()
        missing_irc["calculations"][0]["task_type"] = "transition_state"
        missing_irc["calculations"][0]["validation"] = {
            "normal_termination": True,
            "scf_converged": True,
            "optimization_converged": True,
            "imaginary_frequency_count": 1,
            "mode_reviewed": True,
            "irc_endpoints_confirmed": True,
        }
        self.assert_error(missing_irc, "requires forward and reverse IRC artifacts")

        no_s2 = self.base_manifest()
        no_s2["calculations"][0]["multiplicity"] = 2
        no_s2["calculations"][0]["validation"]["wavefunction_stable"] = True
        self.assert_warning(no_s2, "has no s2_after")

    def test_artifact_and_cross_reference_boundaries(self) -> None:
        non_object = self.base_manifest()
        non_object["artifacts"] = ["bad"]
        self.assert_error(non_object, "artifacts[0]: must be an object")

        cases: list[tuple[str, Any, str]] = [
            ("source_type", "bad", "source_type must be one of"),
            ("status", "bad", "invalid artifact status"),
            ("sha256", "bad", "sha256 must be 64 lowercase"),
            ("calculation_id", "missing", "requires a valid calculation_id"),
        ]
        for field, value, fragment in cases:
            with self.subTest(field=field):
                data = self.base_manifest()
                data["artifacts"][0][field] = value
                self.assert_error(data, fragment)

        duplicate = self.base_manifest()
        duplicate["artifacts"].append(copy.deepcopy(duplicate["artifacts"][0]))
        self.assert_error(duplicate, "duplicate artifact id")

        external = self.base_manifest()
        external["artifacts"][0]["source_type"] = "external"
        external["artifacts"][0]["calculation_id"] = "missing"
        self.assert_error(external, "calculation_id is not defined")

        experiment = self.base_manifest()
        experiment["artifacts"][0]["source_type"] = "experiment"
        experiment["artifacts"][0].pop("calculation_id")
        self.assert_warning(experiment, "lacks measurement_provenance")

        literature = self.base_manifest()
        literature["artifacts"][0]["source_type"] = "literature"
        literature["artifacts"][0].pop("calculation_id")
        self.assert_warning(literature, "lacks source_locator")

        parent = self.base_manifest()
        parent["calculations"][0]["parent_id"] = "missing"
        self.assert_error(parent, "parent_id missing does not exist")

        missing_artifact = self.base_manifest()
        missing_artifact["calculations"][0]["artifact_ids"] = ["missing"]
        self.assert_error(missing_artifact, "artifact missing does not exist")

        other_owner = self.base_manifest()
        other_owner["calculations"].append(
            {
                **copy.deepcopy(other_owner["calculations"][0]),
                "id": "calc-2",
                "artifact_ids": [],
                "status": "planned",
            }
        )
        other_owner["artifacts"][0]["calculation_id"] = "calc-2"
        self.assert_error(other_owner, "belongs to another calculation")

    def test_claim_grade_and_evidence_boundaries(self) -> None:
        non_object = self.base_manifest()
        non_object["claims"] = ["bad"]
        self.assert_error(non_object, "claims[0]: must be an object")

        invalid_grade = self.base_manifest()
        invalid_grade["claims"][0]["evidence_grade"] = "E"
        self.assert_error(invalid_grade, "evidence_grade must be A/B/C/D")

        missing_links = self.base_manifest()
        missing_links["claims"][0]["artifact_ids"] = []
        self.assert_error(missing_links, "at least one artifact must be linked")

        unknown_link = self.base_manifest()
        unknown_link["claims"][0]["artifact_ids"] = ["missing"]
        self.assert_error(unknown_link, "artifact missing does not exist")

        mock_a = self.base_manifest()
        mock_a["claims"][0]["is_mock"] = True
        self.assert_error(mock_a, "mock evidence cannot receive grade A or B")

        paper_d = self.base_manifest()
        paper_d["claims"][0]["evidence_grade"] = "D"
        self.assert_error(paper_d, "grade D evidence cannot be paper_ready")

        no_limits = self.base_manifest()
        no_limits["claims"][0].pop("limitations")
        no_limits["claims"][0].pop("falsification_condition")
        _, warnings = self.validator.validate_manifest(no_limits)
        self.assertTrue(any("limitations are not recorded" in warning for warning in warnings))
        self.assertTrue(any("falsification_condition is not recorded" in warning for warning in warnings))

        grade_a_bad_calc = self.base_manifest()
        grade_a_bad_calc["calculations"][0]["status"] = "validated"
        self.assert_error(grade_a_bad_calc, "not backed by an accepted calculation")

        grade_b = self.base_manifest()
        grade_b["claims"][0]["evidence_grade"] = "B"
        self.assert_error(grade_b, "requires at least one accepted experimental artifact")

        grade_c = self.base_manifest()
        grade_c["claims"][0]["evidence_grade"] = "C"
        self.assert_warning(grade_c, "usually links literature or external evidence")

    def test_load_self_test_and_cli_paths(self) -> None:
        self.assertEqual(self.validator._ideal_s2(3), 2.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            json_path = root / "manifest.json"
            yaml_path = root / "manifest.yaml"
            json_path.write_text(json.dumps(self.base_manifest()), encoding="utf-8")
            yaml_path.write_text("project_id: yaml\nresearch_question: question\n", encoding="utf-8")
            self.assertEqual(self.validator._load(json_path)["project_id"], "project-1")
            self.assertEqual(self.validator._load(yaml_path)["project_id"], "yaml")

            stdout = io.StringIO()
            with (
                patch.object(sys, "argv", ["validate_research_manifest.py", str(json_path), "--json"]),
                redirect_stdout(stdout),
            ):
                self.assertEqual(self.validator.main(), 0)
            self.assertTrue(json.loads(stdout.getvalue())["ok"])

            missing = root / "missing.json"
            with (
                patch.object(sys, "argv", ["validate_research_manifest.py", str(missing)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.validator.main(), 2)

            with (
                patch.object(sys, "argv", ["validate_research_manifest.py"]),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                self.validator.main()

        with (
            patch.object(sys, "argv", ["validate_research_manifest.py", "--self-test"]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.validator.main(), 0)


if __name__ == "__main__":
    unittest.main()
