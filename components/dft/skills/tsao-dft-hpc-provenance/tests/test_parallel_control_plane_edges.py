from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_named(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ParallelControlPlaneEdgeTests(unittest.TestCase):
    provenance: Any
    base_environment: Any
    parallel_environment: Any
    importer: Any

    @classmethod
    def setUpClass(cls) -> None:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        load_named(SCRIPTS / "utils.py", "utils")
        load_named(SCRIPTS / "performance_evidence.py", "performance_evidence")
        load_named(SCRIPTS / "trust_boundary.py", "trust_boundary")
        cls.provenance = load_named(SCRIPTS / "collect_provenance.py", "parallel_provenance_edges")
        cls.base_environment = load_named(
            SCRIPTS / "inspect_execution_environment.py",
            "inspect_execution_environment",
        )
        cls.parallel_environment = load_named(
            SCRIPTS / "inspect_execution_environment_parallel.py",
            "parallel_environment_edges",
        )
        cls.importer = load_named(SCRIPTS / "import_benchmark_evidence.py", "parallel_importer_edges")

    def test_sequential_probe_paths_and_environment_main_formats(self) -> None:
        env = self.parallel_environment
        base = env.base
        specs = {
            "alpha": {"names": ["alpha"], "args": ["--version"]},
            "beta": {"names": ["beta"], "args": ["--version"]},
        }

        def runner(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=f"{command[0]} 1.0\n", stderr="")

        with patch.object(base, "resolve_command", side_effect=lambda names: names[0]):
            report = env.inspect_command_group_parallel(
                specs,
                probe_commands=True,
                runner=runner,
                workers=1,
            )
        self.assertEqual(list(report), ["alpha", "beta"])

        with (
            patch.object(base, "query_nvidia_devices", return_value=[{"vendor": "nvidia"}]),
            patch.object(base, "query_rocm_devices", return_value=[]),
            patch.object(base, "query_intel_devices", return_value=[]),
            patch.object(base, "apple_gpu_inventory", return_value=[]),
        ):
            self.assertEqual(env.query_gpu_devices_parallel(workers=1), [{"vendor": "nvidia"}])

        inventory = {
            "schema_version": base.SCHEMA_VERSION,
            "privacy": {},
            "non_claims": ["parallel probing is not performance evidence"],
        }
        with (
            patch.object(env, "collect_inventory", return_value=inventory),
            patch.object(base, "validate_inventory", return_value=[]),
            patch.object(sys, "argv", ["inspect_execution_environment_parallel.py", "--no-command-probes"]),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(env.main(), 0)
        self.assertTrue(json.loads(stdout.getvalue())["ok"])

        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "inventory.yaml"
            with (
                patch.object(env, "collect_inventory", return_value=inventory),
                patch.object(base, "validate_inventory", return_value=[]),
                patch.object(
                    sys,
                    "argv",
                    [
                        "inspect_execution_environment_parallel.py",
                        "--no-command-probes",
                        "--format",
                        "yaml",
                        "--out",
                        str(out),
                    ],
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(env.main(), 0)
            self.assertIn("ok: true", out.read_text(encoding="utf-8"))

        with (
            patch.object(env, "collect_inventory", return_value=inventory),
            patch.object(base, "validate_inventory", return_value=["invalid inventory"]),
            patch.object(sys, "argv", ["inspect_execution_environment_parallel.py"]),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(env.main(), 1)
        self.assertEqual(json.loads(stdout.getvalue())["errors"], ["invalid inventory"])

    def test_provenance_main_success_and_structured_failure(self) -> None:
        module = self.provenance
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "a.dat"
            second = root / "b.dat"
            first.write_text("alpha\n", encoding="utf-8")
            second.write_text("beta\n", encoding="utf-8")
            out = root / "provenance.json"
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "collect_provenance.py",
                        str(first),
                        str(second),
                        "--workers",
                        "2",
                        "--out",
                        str(out),
                    ],
                ),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(module.main(), 0)
            self.assertEqual(stdout.getvalue().strip(), str(out))
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["hashing"]["workers"], 2)

            with (
                patch.object(
                    sys,
                    "argv",
                    ["collect_provenance.py", str(root / "missing"), "--out", str(root / "bad.json")],
                ),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(module.main(), 1)
            self.assertFalse(json.loads(stdout.getvalue())["ok"])

    def test_importer_custom_schema_is_schema_only_and_sequential(self) -> None:
        importer = self.importer
        records = [
            {"schema_version": "2.0", "candidate_id": "schema-bad"},
            {"schema_version": "2.0", "candidate_id": "custom-a"},
            {"schema_version": "2.0", "candidate_id": "custom-b"},
        ]

        def result_key(record: dict[str, Any]) -> tuple[str, str, int, str]:
            return ("PLAN", str(record["candidate_id"]), 1, str(record["candidate_id"]))

        with (
            patch.object(importer, "load_json", return_value={"properties": {"schema_version": {"const": "2.0"}}}),
            patch.object(importer, "load_records", side_effect=[OSError("unreadable"), records]),
            patch.object(importer, "validate_record_schema", side_effect=[["schema failure"], [], []]),
            patch.object(importer, "validate_result") as semantic,
            patch.object(importer, "result_sort_key", side_effect=result_key),
        ):
            imported, report = importer.import_with_schema(
                [Path("unreadable.json"), Path("records.json")],
                Path("schema.json"),
                None,
                workers=1,
            )
        semantic.assert_not_called()
        self.assertFalse(report["ok"])
        self.assertEqual(report["validation_workers"], 1)
        self.assertEqual([record["candidate_id"] for record in imported], ["custom-a", "custom-b"])
        self.assertEqual([failure["stage"] for failure in report["failures"]], ["read", "schema"])
        self.assertTrue(all("nonqualifying" in record["validation"]["warnings"][0] for record in imported))
        self.assertFalse(report["schema_version_rewrite_used"])

    def test_importer_canonical_semantic_failure_is_structured(self) -> None:
        importer = self.importer
        raw = {"schema_version": "1.1", "candidate_id": "canonical"}
        canonical = {
            "schema_version": "1.1",
            "benchmark_plan_id": "PLAN",
            "candidate_id": "canonical",
            "repeat_index": 1,
            "execution": {"run_id": "canonical"},
        }
        schema = {
            "$id": importer.contract.CANONICAL_SCHEMA_ID,
            "properties": {"schema_version": {"const": "1.1"}},
        }
        with (
            patch.object(importer, "load_json", return_value=schema),
            patch.object(importer, "load_records", return_value=[raw]),
            patch.object(importer.contract, "normalize_record", return_value=(canonical, {"migration": "none"})),
            patch.object(importer, "validate_result", side_effect=ValueError("semantic crash")),
            patch.object(
                importer,
                "result_sort_key",
                return_value=("PLAN", "canonical", 1, "canonical"),
            ),
        ):
            imported, report = importer.import_with_schema(
                [Path("canonical.json")],
                Path("schema.json"),
                None,
                workers=1,
            )
        self.assertEqual(imported, [])
        self.assertFalse(report["ok"])
        self.assertEqual(report["failures"][0]["stage"], "semantic")
        self.assertIn("semantic validation failed", report["failures"][0]["errors"][0])

    def test_importer_main_success_and_initialization_failure(self) -> None:
        importer = self.importer
        record = {
            "schema_version": "2.0",
            "candidate_id": "candidate",
            "validation": {"ok": True},
        }
        report = {
            "ok": True,
            "records": 1,
            "valid_records": 1,
            "invalid_records": 0,
            "validation_workers": 2,
            "failures": [],
            "schema_version": "2.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "evidence.jsonl"
            audit = root / "report.json"
            with (
                patch.object(importer, "import_with_schema", return_value=([record], report)),
                patch.object(
                    sys,
                    "argv",
                    [
                        "import_benchmark_evidence.py",
                        "input.json",
                        "--schema",
                        "schema.json",
                        "--out",
                        str(out),
                        "--report",
                        str(audit),
                        "--workers",
                        "2",
                    ],
                ),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(importer.main(), 0)
            exported = json.loads(out.read_text(encoding="utf-8"))
            self.assertNotIn("validation", exported)
            self.assertTrue(json.loads(stdout.getvalue())["ok"])
            self.assertEqual(json.loads(audit.read_text(encoding="utf-8"))["validation_workers"], 2)

            failed_report = root / "failed-report.json"
            with (
                patch.object(importer, "import_with_schema", side_effect=ValueError("bad schema")),
                patch.object(
                    sys,
                    "argv",
                    [
                        "import_benchmark_evidence.py",
                        "input.json",
                        "--schema",
                        "schema.json",
                        "--out",
                        str(root / "missing-output.jsonl"),
                        "--report",
                        str(failed_report),
                    ],
                ),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(importer.main(), 1)
            failure = json.loads(stdout.getvalue())
            self.assertEqual(failure["failures"][0]["stage"], "initialization")
            self.assertFalse(json.loads(failed_report.read_text(encoding="utf-8"))["ok"])


if __name__ == "__main__":
    unittest.main()
