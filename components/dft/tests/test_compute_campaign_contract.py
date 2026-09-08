from __future__ import annotations

import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts"
CONTRACT_PATH = SCRIPT_DIR / "compute_campaign_contract.py"
QUALIFICATION_PATH = SCRIPT_DIR / "qualify_compute_campaign.py"
TEMPLATE_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "templates" / "compute-qualification-campaign.yaml"
SUPPORT_PATH = ROOT / "tests" / "test_compute_qualification.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


policy = load_module("tsao_compute_campaign_contract_tests", CONTRACT_PATH)
qualification = load_module("tsao_compute_campaign_contract_qualification", QUALIFICATION_PATH)
support = load_module("tsao_compute_campaign_contract_support", SUPPORT_PATH)


def canonical_campaign() -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "campaign_id": "CAMPAIGN-1",
        "benchmark_plan_id": "PLAN-1",
        "engine": "vasp",
        "participants": [
            {"candidate_id": "CPU-REF", "role": "scientific-reference"},
            {"candidate_id": "GPU-CANDIDATE", "role": "acceleration-candidate"},
        ],
        "minimum_repeats": 3,
        "minimum_reference_over_candidate_ratio": 1.1,
        "numerical_tolerances": {
            "energy_ev": {"absolute": 1.0e-6, "relative": 1.0e-8},
            "forces_ev_per_angstrom": {"absolute": 1.0e-4, "relative": 1.0e-6},
        },
    }


def legacy_campaign() -> dict[str, Any]:
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


class ComputeCampaignContractTests(unittest.TestCase):
    def test_contract_report_schema_authority_and_template(self) -> None:
        report = policy.contract_report()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["canonical_contract"], "canonical-compute-campaign-v1.1")
        self.assertEqual(report["canonical_schema_version"], "1.1")
        self.assertTrue(report["root_mirror_synchronized"])
        self.assertEqual(report["legacy_contract"], "legacy-compute-campaign-v1.0")
        self.assertEqual(report["migration_qualification_impact"], "NO_EVIDENCE_PROMOTION")
        self.assertEqual(report["defaults_applied"], [])
        self.assertEqual(
            report["benchmark_result_contract_boundary"],
            "independent-canonical-nested-v1.1",
        )
        loaded = policy.load_campaign(TEMPLATE_PATH)
        self.assertEqual(loaded.schema_version, "1.1")
        self.assertEqual(loaded.migration["migration"], "none")

    def test_canonical_and_legacy_positive_paths_are_typed_and_nonpromoting(self) -> None:
        canonical = policy.prepare_campaign(canonical_campaign())
        self.assertEqual(canonical.reference_candidate_id, "CPU-REF")
        self.assertEqual(canonical.candidate_ids, ("GPU-CANDIDATE",))
        self.assertEqual(canonical.expected_roles["CPU-REF"], "scientific-reference")
        self.assertEqual(canonical.migration["source_contract"], policy.CANONICAL_CONTRACT)

        legacy = policy.prepare_campaign(legacy_campaign())
        self.assertEqual(legacy.to_dict(), canonical.to_dict())
        self.assertEqual(legacy.migration["source_contract"], policy.LEGACY_CONTRACT)
        self.assertEqual(
            legacy.migration["migration"],
            "reference-and-candidate-fields-to-explicit-participants",
        )
        self.assertEqual(legacy.migration["qualification_impact"], "NO_EVIDENCE_PROMOTION")
        self.assertEqual(legacy.migration["defaults_applied"], ())
        self.assertEqual(legacy.migration["evidence_fields_added"], ())

        report = qualification.qualify(legacy_campaign(), [])
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["state"], qualification.EXTERNAL_HOLD)
        self.assertFalse(report["performance"]["evaluated"])
        self.assertEqual(
            report["campaign_source_contract"],
            "legacy-compute-campaign-v1.0",
        )
        self.assertEqual(
            report["campaign_migration_qualification_impact"],
            "NO_EVIDENCE_PROMOTION",
        )
        self.assertEqual(report["campaign_defaults_applied"], [])
        self.assertEqual(report["campaign_evidence_fields_added"], [])

    def test_invalid_campaign_table_fails_closed_before_evidence_processing(self) -> None:
        cases: list[tuple[str, Any]] = []

        def add(name: str, mutate: Any) -> None:
            value = canonical_campaign()
            mutate(value)
            cases.append((name, value))

        add("unknown version", lambda value: value.__setitem__("schema_version", "9.9"))
        add("numeric version", lambda value: value.__setitem__("schema_version", 1.1))
        add("mixed role fields", lambda value: value.__setitem__("candidate_ids", ["GPU-CANDIDATE"]))
        add("extra root field", lambda value: value.__setitem__("unexpected", True))
        add("unknown engine", lambda value: value.__setitem__("engine", "unknown"))
        add("boolean repeats", lambda value: value.__setitem__("minimum_repeats", True))
        add("float repeats", lambda value: value.__setitem__("minimum_repeats", 3.0))
        add("too few repeats", lambda value: value.__setitem__("minimum_repeats", 2))
        add(
            "boolean ratio",
            lambda value: value.__setitem__("minimum_reference_over_candidate_ratio", True),
        )
        add(
            "unit ratio",
            lambda value: value.__setitem__("minimum_reference_over_candidate_ratio", 1.0),
        )
        add(
            "infinite ratio",
            lambda value: value.__setitem__(
                "minimum_reference_over_candidate_ratio",
                math.inf,
            ),
        )
        add(
            "participants mapping",
            lambda value: value.__setitem__("participants", {}),
        )
        add(
            "duplicate candidate same role",
            lambda value: value["participants"].append(
                {"candidate_id": "GPU-CANDIDATE", "role": "acceleration-candidate"}
            ),
        )
        add(
            "duplicate candidate across roles",
            lambda value: value["participants"][1].__setitem__("candidate_id", "CPU-REF"),
        )
        add(
            "two references",
            lambda value: value["participants"][1].__setitem__("role", "scientific-reference"),
        )
        add(
            "no reference",
            lambda value: value["participants"][0].__setitem__("role", "acceleration-candidate"),
        )
        add(
            "no candidate",
            lambda value: value.__setitem__(
                "participants",
                [{"candidate_id": "CPU-REF", "role": "scientific-reference"}],
            ),
        )
        add(
            "whitespace candidate",
            lambda value: value["participants"][1].__setitem__("candidate_id", "   "),
        )
        add(
            "participant extra field",
            lambda value: value["participants"][0].__setitem__("extra", 1),
        )
        add(
            "empty tolerances",
            lambda value: value.__setitem__("numerical_tolerances", {}),
        )
        add(
            "negative absolute tolerance",
            lambda value: value["numerical_tolerances"]["energy_ev"].__setitem__(
                "absolute",
                -1.0,
            ),
        )
        add(
            "nonfinite relative tolerance",
            lambda value: value["numerical_tolerances"]["energy_ev"].__setitem__(
                "relative",
                math.nan,
            ),
        )
        add(
            "boolean tolerance",
            lambda value: value["numerical_tolerances"]["energy_ev"].__setitem__(
                "absolute",
                False,
            ),
        )
        add(
            "tolerance extra field",
            lambda value: value["numerical_tolerances"]["energy_ev"].__setitem__(
                "extra",
                0.0,
            ),
        )
        add(
            "whitespace tolerance name",
            lambda value: value.__setitem__(
                "numerical_tolerances",
                {"   ": {"absolute": 0.0, "relative": 0.0}},
            ),
        )

        legacy_overlap = legacy_campaign()
        legacy_overlap["candidate_ids"] = ["CPU-REF"]
        cases.append(("legacy contradictory reference candidate", legacy_overlap))
        legacy_duplicate = legacy_campaign()
        legacy_duplicate["candidate_ids"] = ["GPU-CANDIDATE", "GPU-CANDIDATE"]
        cases.append(("legacy duplicate candidate", legacy_duplicate))
        legacy_extra = legacy_campaign()
        legacy_extra["extra"] = 1
        cases.append(("legacy extra field", legacy_extra))

        for name, invalid in cases:
            with self.subTest(name=name):
                errors = policy.validate_campaign(invalid)
                self.assertTrue(errors, invalid)
                report = qualification.qualify(invalid, support.complete_raw())
                self.assertFalse(report["ok"], report)
                self.assertEqual(report["state"], qualification.UNQUALIFIED)
                self.assertFalse(report["performance"]["evaluated"])
                self.assertEqual(report["document_count"], 0)

    def test_loader_rejects_duplicate_keys_nonfinite_values_and_wrong_roots(self) -> None:
        fixtures = {
            "duplicate.yaml": 'schema_version: "1.1"\nschema_version: "1.1"\n',
            "nonfinite.yaml": 'schema_version: "1.1"\nminimum_reference_over_candidate_ratio: .inf\n',
            "list.yaml": "- one\n- two\n",
            "duplicate.json": '{"schema_version":"1.1","schema_version":"1.1"}',
            "nonfinite.json": '{"minimum_reference_over_candidate_ratio":1e999}',
            "constant.json": '{"minimum_reference_over_candidate_ratio":NaN}',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in fixtures.items():
                with self.subTest(name=name):
                    path = root / name
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(policy.CampaignContractError):
                        policy.load_mapping(path)

    def test_schema_and_semantics_are_consistent(self) -> None:
        canonical = canonical_campaign()
        self.assertEqual(policy.schema_errors(canonical, policy.canonical_schema()), [])
        self.assertEqual(policy.validate_campaign(canonical), [])

        whitespace = copy.deepcopy(canonical)
        whitespace["participants"][0]["candidate_id"] = " "
        self.assertEqual(policy.schema_errors(whitespace, policy.canonical_schema()), [])
        self.assertTrue(policy.validate_campaign(whitespace))

        legacy = legacy_campaign()
        self.assertEqual(policy.schema_errors(legacy, policy.legacy_schema()), [])
        migrated, migration = policy.normalize_campaign(legacy)
        self.assertEqual(policy.schema_errors(migrated, policy.canonical_schema()), [])
        self.assertEqual(migration["defaults_applied"], [])
        self.assertEqual(migration["evidence_fields_added"], [])

    def test_campaign_config_and_campaign_document_are_defensively_immutable(self) -> None:
        source = canonical_campaign()
        config = policy.prepare_campaign(source)
        source["campaign_id"] = "MUTATED-SOURCE"
        self.assertEqual(config.campaign_id, "CAMPAIGN-1")
        with self.assertRaises(TypeError):
            cast(Any, config.record)["campaign_id"] = "MUTATED"
        with self.assertRaises(TypeError):
            cast(Any, config.record)["participants"][0]["candidate_id"] = "MUTATED"
        detached = config.to_dict()
        detached["participants"][0]["candidate_id"] = "DETACHED"
        self.assertEqual(config.reference_candidate_id, "CPU-REF")

        raw = support.canonical_result("CPU-REF", 1, 10.0)
        document = qualification.prepare_document(raw)
        raw["candidate_id"] = "MUTATED-SOURCE"
        self.assertEqual(document.candidate_id, "CPU-REF")
        with self.assertRaises(TypeError):
            cast(Any, document.record)["scientific"]["results"]["energy_ev"] = 0.0
        mutable = document.mutable_record()
        mutable["scientific"]["results"]["energy_ev"] = 0.0
        self.assertEqual(document.scientific_observables()["energy_ev"], -10.0)

    def test_cli_accepts_canonical_and_legacy_only_through_central_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, value in (
                ("canonical", canonical_campaign()),
                ("legacy", legacy_campaign()),
            ):
                with self.subTest(label=label):
                    path = root / f"{label}.json"
                    path.write_text(json.dumps(value), encoding="utf-8")
                    completed = subprocess.run(
                        [sys.executable, str(QUALIFICATION_PATH), str(path)],
                        cwd=ROOT,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    report = json.loads(completed.stdout)
                    self.assertEqual(report["state"], qualification.EXTERNAL_HOLD)
                    self.assertFalse(report["performance"]["evaluated"])
                    self.assertEqual(report["campaign_contract"], policy.CANONICAL_CONTRACT)
                    if label == "legacy":
                        self.assertEqual(
                            report["campaign_migration_qualification_impact"],
                            policy.NO_EVIDENCE_PROMOTION,
                        )

            invalid = root / "invalid.json"
            invalid.write_text(
                json.dumps({**canonical_campaign(), "schema_version": "9.9"}),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(QUALIFICATION_PATH), str(invalid)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            report = json.loads(completed.stdout)
            self.assertEqual(report["state"], qualification.UNQUALIFIED)
            self.assertFalse(report["performance"]["evaluated"])


if __name__ == "__main__":
    unittest.main()
