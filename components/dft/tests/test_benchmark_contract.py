from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
HPC = ROOT / "skills" / "tsao-dft-hpc-provenance"
CONTRACT_PATH = HPC / "scripts" / "benchmark_contract.py"
PERFORMANCE_PATH = HPC / "scripts" / "performance_evidence.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_benchmark_contract.py"
IMPORTER_PATH = HPC / "scripts" / "import_benchmark_evidence.py"
TEMPLATE_PATH = HPC / "templates" / "benchmark-result.yaml"


def load_module(name: str, path: Path) -> ModuleType:
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def accelerate_reference(row: dict[str, Any]) -> None:
    row["accelerator_runtime"].update(backend="cuda")
    row["hardware_fingerprint"]["accelerators"].append({"vendor": "nvidia", "model": "H100", "stable_id": "GPU-A"})


contract = load_module("tsao_benchmark_contract_tests", CONTRACT_PATH)
performance = load_module("tsao_benchmark_performance_tests", PERFORMANCE_PATH)
validator = load_module("tsao_benchmark_contract_validator_tests", VALIDATOR_PATH)
importer = load_module("tsao_benchmark_contract_importer_tests", IMPORTER_PATH)


class BenchmarkContractTests(unittest.TestCase):
    def template(self) -> dict[str, Any]:
        loaded = yaml.safe_load(TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(loaded, dict)
        return loaded

    def legacy(self) -> dict[str, Any]:
        return copy.deepcopy(validator.legacy_flat_fixture())

    def test_repository_has_one_authoritative_contract(self) -> None:
        report = validator.validate()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["canonical_contract"], "nested-v1.1")
        self.assertTrue(report["root_mirror_synchronized"])
        self.assertEqual(report["native_semantic_schema_version"], "1.1")
        self.assertFalse(report["compatibility_view_present"])
        self.assertEqual(report["legacy_semantic_bypass"], "FAIL_CLOSED")
        self.assertEqual(report["legacy_flat_qualification_impact"], "EXTERNAL_HOLD")
        self.assertEqual(report["unknown_or_mixed_input"], "FAIL_CLOSED")
        self.assertFalse(report["external_engine_invoked"])
        self.assertFalse(report["performance_ratio_published"])

    def test_native_semantics_are_v11_and_public_entry_uses_central_adapter(self) -> None:
        canonical = self.template()
        native, errors, _ = performance.validate_canonical_result(canonical)
        self.assertEqual(errors, [])
        self.assertEqual(native["schema_version"], "1.1")

        legacy_nested = copy.deepcopy(canonical)
        legacy_nested["schema_version"] = "1.0"
        _, direct_errors, _ = performance.validate_canonical_result(legacy_nested)
        self.assertIn("schema_version must be 1.1", direct_errors)

        migrated, public_errors, _ = performance.validate_result(legacy_nested)
        self.assertEqual(public_errors, [])
        self.assertEqual(migrated["schema_version"], "1.1")
        self.assertFalse(hasattr(contract, "semantic_compatibility_record"))

    def test_canonical_and_legacy_nested_versions_are_explicit(self) -> None:
        current = self.template()
        canonical, direct = contract.normalize_record(current)
        self.assertEqual(direct["migration"], "none")
        self.assertEqual(canonical["schema_version"], "1.1")

        legacy = copy.deepcopy(current)
        legacy["schema_version"] = "1.0"
        migrated, report = contract.normalize_record(legacy)
        self.assertEqual(migrated, canonical)
        self.assertEqual(report["migration"], "version-only-shape-preserving")
        self.assertEqual(report["qualification_impact"], "none")

    def test_unknown_mixed_role_and_nonfinite_inputs_fail_closed_table(self) -> None:
        canonical_cases: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
            ("unknown nested version", lambda row: row.__setitem__("schema_version", "2.0"), "unsupported nested"),
            ("mixed shape", lambda row: row.__setitem__("wall_time_seconds", 1.0), "mixed flat and nested"),
            (
                "nonfinite wall",
                lambda row: row["performance"].__setitem__("wall_time_s", float("inf")),
                "non-finite",
            ),
            (
                "nonfinite force",
                lambda row: row["scientific"]["results"].__setitem__("forces_ev_per_angstrom", [float("nan")]),
                "non-finite",
            ),
        ]
        for name, mutate, expected in canonical_cases:
            with self.subTest(name=name):
                record = self.template()
                mutate(record)
                with self.assertRaisesRegex(contract.BenchmarkContractError, expected):
                    contract.normalize_record(record)

        flat = self.legacy()
        flat["schema_version"] = "9.9"
        with self.assertRaisesRegex(contract.BenchmarkContractError, "unsupported flat"):
            contract.normalize_record(flat, role_hint="scientific-reference")
        with self.assertRaisesRegex(contract.BenchmarkContractError, "explicit"):
            contract.normalize_record(self.legacy(), role_hint="reference")

    def test_json_loader_rejects_nonstandard_and_overflowed_numbers_table(self) -> None:
        payloads = [
            '{"value": NaN}',
            '{"value": Infinity}',
            '{"value": -Infinity}',
            '{"value": 1e999}',
            '{"value": [0.0, 1e999]}',
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for payload in payloads:
                with self.subTest(payload=payload):
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaisesRegex(contract.BenchmarkContractError, "non-finite"):
                        contract.load_json_mapping(path)

    def test_legacy_flat_requires_role_and_forces_hold(self) -> None:
        legacy = self.legacy()
        with self.assertRaisesRegex(contract.BenchmarkContractError, "explicit"):
            contract.normalize_record(legacy)

        migrated, report = contract.normalize_record(legacy, role_hint="scientific-reference")
        self.assertEqual(migrated["schema_version"], "1.1")
        self.assertEqual(migrated["role"], "scientific-reference")
        self.assertEqual(migrated["evidence_source"]["kind"], "imported-unverified")
        self.assertTrue(migrated["evidence_source"]["missing_fields"])
        self.assertFalse(migrated["scientific"]["parser_accepted"])
        self.assertEqual(report["qualification_impact"], "EXTERNAL_HOLD")

        view = contract.compute_qualification_view(migrated)
        self.assertNotEqual(view["evidence_source"], "real-engine-observation")
        self.assertTrue(view["missing_fields"])

    def test_legacy_rare_field_combinations_remain_loss_explicit(self) -> None:
        multi_gpu = self.legacy()
        multi_gpu["candidate_id"] = "legacy-gpu"
        multi_gpu["accelerator_runtime"] = {
            "backend": "cuda",
            "toolkit_version": "12.8",
            "driver_version": "600.1",
        }
        multi_gpu["hardware_fingerprint"]["accelerators"] = [
            {"vendor": "nvidia", "model": "H100", "stable_id": "GPU-A", "memory_bytes": 24_000_000_000},
            {"vendor": "nvidia", "model": "H100", "stable_id": "GPU-B", "memory_bytes": 24_000_000_000},
        ]
        multi_gpu["hardware_fingerprint"]["topology"]["gpus_per_node"] = 2
        multi_gpu["binding"]["accelerator"] = "GPU-A,GPU-B"
        multi_gpu["scientific_results"] = {
            "energy_eV": -11.0,
            "forces_eV_per_angstrom": [0.1, 0.2, 0.3],
            "band_gap_ev": 1.5,
        }
        migrated, report = contract.normalize_record(multi_gpu, role_hint="acceleration-candidate")
        self.assertEqual(migrated["hardware"]["gpu_uuids"], ["GPU-A", "GPU-B"])
        self.assertEqual(migrated["hardware"]["gpu_memory_gb"], 48.0)
        self.assertEqual(migrated["scientific"]["results"]["energy_ev"], -11.0)
        self.assertEqual(migrated["scientific"]["results"]["properties"]["band_gap_ev"], 1.5)
        self.assertEqual(report["qualification_impact"], "EXTERNAL_HOLD")

        heterogeneous = copy.deepcopy(multi_gpu)
        heterogeneous["hardware_fingerprint"]["accelerators"][1]["vendor"] = "amd"
        heterogeneous["hardware_fingerprint"]["accelerators"][1]["model"] = "MI300X"
        migrated, _ = contract.normalize_record(heterogeneous, role_hint="acceleration-candidate")
        self.assertTrue(
            any("heterogeneous accelerator inventory" in item for item in migrated["evidence_source"]["missing_fields"])
        )

        surrogate = self.legacy()
        surrogate["engine"] = "ml-surrogate"
        surrogate["build_fingerprint"] = None
        surrogate["hardware_fingerprint"] = None
        surrogate["output_artifact_sha256"] = None
        surrogate["evidence_source"] = "simulation"
        migrated, _ = contract.normalize_record(surrogate, role_hint="acceleration-candidate")
        missing = migrated["evidence_source"]["missing_fields"]
        self.assertEqual(migrated["engine"]["name"], "generic")
        for expected in (
            "legacy ml-surrogate engine is mapped to generic",
            "build fingerprint identity unavailable",
            "hardware fingerprint identity unavailable",
            "legacy source simulation",
            "output artifact SHA-256 unavailable",
        ):
            self.assertTrue(any(expected in item for item in missing), expected)

    def test_contradictory_legacy_provenance_is_table_driven_and_held(self) -> None:
        cases: list[tuple[str, str, Callable[[dict[str, Any]], None], str]] = [
            (
                "runtime without hardware",
                "acceleration-candidate",
                lambda row: row["accelerator_runtime"].update(backend="cuda"),
                "runtime contradicts empty hardware",
            ),
            (
                "hardware without runtime",
                "acceleration-candidate",
                lambda row: row["hardware_fingerprint"]["accelerators"].append(
                    {"vendor": "nvidia", "model": "H100", "stable_id": "GPU-A"}
                ),
                "hardware inventory contradicts runtime backend none",
            ),
            (
                "accelerated reference",
                "scientific-reference",
                accelerate_reference,
                "reference role contradicts accelerator runtime",
            ),
            (
                "parser exit contradiction",
                "scientific-reference",
                lambda row: row.__setitem__("exit_status", 1),
                "parser acceptance contradicts exit",
            ),
        ]
        for name, role, mutate, expected in cases:
            with self.subTest(name=name):
                record = self.legacy()
                mutate(record)
                migrated, report = contract.normalize_record(record, role_hint=role)
                self.assertEqual(report["qualification_impact"], "EXTERNAL_HOLD")
                self.assertFalse(migrated["scientific"]["parser_accepted"])
                self.assertTrue(any(expected in item for item in migrated["evidence_source"]["missing_fields"]))

    def test_duplicate_legacy_gpu_identity_fails_closed(self) -> None:
        legacy = self.legacy()
        legacy["candidate_id"] = "duplicate-gpu"
        legacy["accelerator_runtime"].update(backend="cuda")
        legacy["hardware_fingerprint"]["accelerators"] = [
            {"vendor": "nvidia", "model": "H100", "stable_id": "GPU-DUP", "memory_bytes": 1},
            {"vendor": "nvidia", "model": "H100", "stable_id": "GPU-DUP", "memory_bytes": 2},
        ]
        with self.assertRaisesRegex(contract.BenchmarkContractError, "unique"):
            contract.normalize_record(legacy, role_hint="acceleration-candidate")

    def test_formal_import_migrates_flat_only_with_explicit_role(self) -> None:
        legacy = self.legacy()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            records, report = importer.import_with_schema(
                [path],
                contract.CANONICAL_SCHEMA_PATH,
                None,
                legacy_roles={"legacy-cpu-reference": "scientific-reference"},
                require_authoritative=True,
            )
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["contract_mode"], "canonical-nested-v1.1")
        self.assertEqual(report["canonical_semantic_schema_version"], "1.1")
        self.assertFalse(report["schema_version_rewrite_used"])
        self.assertEqual(report["migration_counts"], {"field-mapping-with-explicit-missing-evidence": 1})
        self.assertEqual(records[0]["schema_version"], "1.1")
        self.assertEqual(records[0]["evidence_source"]["kind"], "imported-unverified")
        self.assertTrue(records[0]["evidence_source"]["missing_fields"])

        with self.assertRaisesRegex(ValueError, "authoritative"):
            importer.import_with_schema(
                [],
                contract.LEGACY_FLAT_SCHEMA_PATH,
                None,
                require_authoritative=True,
            )

    def test_custom_schema_is_not_rewritten_or_semantically_qualified(self) -> None:
        custom_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["schema_version", "candidate_id"],
            "properties": {
                "schema_version": {"const": "2.0"},
                "candidate_id": {"type": "string"},
            },
            "additionalProperties": True,
        }
        record = {"schema_version": "2.0", "candidate_id": "custom-candidate"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schema_path = root / "custom.schema.json"
            record_path = root / "custom.json"
            schema_path.write_text(json.dumps(custom_schema), encoding="utf-8")
            record_path.write_text(json.dumps(record), encoding="utf-8")
            records, report = importer.import_with_schema([record_path], schema_path, None)
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(records[0]["schema_version"], "2.0")
        self.assertEqual(report["migration_counts"], {"custom-schema-nonqualifying": 1})
        self.assertFalse(report["schema_version_rewrite_used"])
        self.assertIn("nonqualifying", records[0]["validation"]["warnings"][0])
        self.assertEqual(report["record_migrations"][0]["qualification_impact"], "NOT_ELIGIBLE")

    def test_authoritative_and_legacy_schema_identities_are_distinct(self) -> None:
        canonical = contract.canonical_schema()
        legacy = contract.legacy_flat_schema()
        self.assertEqual(contract.approved_schema_kind(canonical), "canonical-nested-v1.1")
        self.assertEqual(contract.approved_schema_kind(legacy), "legacy-flat-v1.0")
        self.assertNotEqual(canonical["$id"], legacy["$id"])
        self.assertEqual(
            contract.ROOT_SCHEMA_MIRROR_PATH.read_text(encoding="utf-8"),
            contract.CANONICAL_SCHEMA_PATH.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
