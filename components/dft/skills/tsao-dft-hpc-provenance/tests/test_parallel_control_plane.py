from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
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


class ParallelControlPlaneTests(unittest.TestCase):
    utils: Any
    provenance: Any
    base_environment: Any
    parallel_environment: Any
    importer: Any

    @classmethod
    def setUpClass(cls) -> None:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.utils = load_named(SCRIPTS / "utils.py", "utils")
        cls.provenance = load_named(SCRIPTS / "collect_provenance.py", "parallel_collect_provenance")
        cls.base_environment = load_named(
            SCRIPTS / "inspect_execution_environment.py",
            "inspect_execution_environment",
        )
        cls.parallel_environment = load_named(
            SCRIPTS / "inspect_execution_environment_parallel.py",
            "parallel_environment_inventory",
        )
        load_named(SCRIPTS / "performance_evidence.py", "performance_evidence")
        load_named(SCRIPTS / "trust_boundary.py", "trust_boundary")
        cls.importer = load_named(SCRIPTS / "import_benchmark_evidence.py", "parallel_evidence_importer")

    def test_ordered_parallel_hashing_is_exact_and_concurrent(self) -> None:
        active = 0
        maximum = 0
        lock = threading.Lock()
        original = self.utils.sha256_file

        def observed(path: Path) -> str:
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.01)
                return original(path)
            finally:
                with lock:
                    active -= 1

        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / f"file-{index}.bin" for index in range(8)]
            for index, path in enumerate(paths):
                path.write_bytes(bytes([index]) * 4096)
            expected = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
            with patch.object(self.utils, "sha256_file", side_effect=observed):
                observed_hashes = self.utils.sha256_files(paths, workers=4)
            self.assertEqual(observed_hashes, expected)
            self.assertGreater(maximum, 1)
            self.assertEqual(self.utils.sha256_files([], workers=4), [])
        self.assertEqual(self.utils.normalized_workers(9, 2), 2)
        for workers in (-1, True, 1.5):
            with self.subTest(workers=workers), self.assertRaises(ValueError):
                self.utils.normalized_workers(workers, 3)
        with self.assertRaises(ValueError):
            self.utils.normalized_workers(1, -1)
        with self.assertRaises(ValueError):
            self.utils.normalized_workers(1, 2, maximum=0)

    def test_provenance_parallel_hashing_and_atomic_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root / f"input-{index}.dat" for index in range(4)]
            for index, path in enumerate(paths):
                path.write_text(f"payload-{index}\n", encoding="utf-8")
            payload = self.provenance.collect(paths, workers=4)
            self.assertEqual(payload["hashing"]["workers"], 4)
            self.assertEqual([item["path"] for item in payload["files"]], [str(path) for path in paths])
            out = root / "nested" / "provenance.json"
            self.provenance.write_json_atomic(out, payload)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["files"], payload["files"])
            self.assertEqual(list(out.parent.glob(f".{out.name}.*.tmp")), [])
            with self.assertRaises(ValueError):
                self.provenance.collect([])
            with self.assertRaisesRegex(ValueError, "not a file"):
                self.provenance.collect([root / "missing"])

    def test_parallel_command_and_gpu_probes_are_deterministic(self) -> None:
        env = self.parallel_environment
        base = env.base
        active = 0
        maximum = 0
        lock = threading.Lock()

        def runner(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.01)
                return subprocess.CompletedProcess(command, 0, stdout=f"{Path(command[0]).name} 1.0\n", stderr="")
            finally:
                with lock:
                    active -= 1

        specs = {f"tool-{index}": {"names": [f"tool-{index}"], "args": ["--version"]} for index in range(8)}
        with patch.object(base, "resolve_command", side_effect=lambda names: f"/bin/{names[0]}"):
            report = env.inspect_command_group_parallel(
                specs,
                probe_commands=True,
                runner=runner,
                workers=4,
            )
        self.assertEqual(list(report), sorted(specs))
        self.assertTrue(all(item["status"] == base.AVAILABLE for item in report.values()))
        self.assertGreater(maximum, 1)

        with patch.object(base, "inspect_command_group") as serial:
            serial.return_value = {"x": {"status": base.NOT_AVAILABLE}}
            self.assertEqual(
                env.inspect_command_group_parallel(
                    {"x": {"names": ["x"], "args": []}},
                    probe_commands=False,
                    workers=4,
                ),
                serial.return_value,
            )
            serial.assert_called_once()

        with (
            patch.object(base, "query_nvidia_devices", return_value=[{"vendor": "nvidia"}]),
            patch.object(base, "query_rocm_devices", return_value=[{"vendor": "amd"}]),
            patch.object(base, "query_intel_devices", return_value=[{"vendor": "intel"}]),
            patch.object(base, "apple_gpu_inventory", return_value=[{"vendor": "apple"}]),
        ):
            devices = env.query_gpu_devices_parallel(workers=3)
        self.assertEqual([item["vendor"] for item in devices], ["nvidia", "amd", "intel", "apple"])

    def test_parallel_environment_collection_and_cli_failure(self) -> None:
        env = self.parallel_environment
        base = env.base
        commands = {key: {"status": base.NOT_AVAILABLE, "command": None, "version": None} for key in base.COMMAND_SPECS}
        engines = {key: {"status": base.NOT_AVAILABLE, "command": None, "version": None} for key in base.ENGINE_SPECS}
        with (
            patch.object(env, "inspect_command_group_parallel", side_effect=[commands, engines]),
            patch.object(base, "apple_gpu_inventory", return_value=[]),
            patch.object(base, "cpu_inventory", return_value={}),
            patch.object(base, "python_backend_inventory", return_value={}),
            patch.object(base.platform, "node", return_value="node"),
            patch.object(base.platform, "machine", return_value="x86_64"),
            patch.object(base.platform, "system", return_value="Linux"),
            patch.object(base.platform, "release", return_value="1"),
            patch.object(base.platform, "python_version", return_value="3.12"),
        ):
            report = env.collect_inventory(probe_commands=False, observed_at="fixed", workers=2)
        self.assertEqual(report["source_kind"], "static-local-inspection")
        self.assertEqual(base.validate_inventory(report), [])
        self.assertIn("not DFT or GPU performance evidence", report["non_claims"][-1])

        with (
            patch.object(sys, "argv", ["inspect_execution_environment_parallel.py", "--workers", "-1"]),
            patch("builtins.print") as rendered,
        ):
            self.assertEqual(env.main(), 1)
        self.assertIn("workers must be non-negative", rendered.call_args.args[0])

    def test_parallel_evidence_validation_preserves_order_and_duplicates(self) -> None:
        importer = self.importer
        active = 0
        maximum = 0
        lock = threading.Lock()
        records = [
            {
                "schema_version": "1.1",
                "benchmark_plan_id": "PLAN",
                "candidate_id": f"candidate-{index:02d}",
                "repeat_index": 1,
                "execution": {"run_id": f"run-{index:02d}"},
            }
            for index in reversed(range(12))
        ]
        schema = {
            "$id": importer.contract.CANONICAL_SCHEMA_ID,
            "properties": {"schema_version": {"const": "1.1"}},
        }

        def normalize(record: dict[str, Any], role_hint: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
            del role_hint
            return record, {"migration": "none"}

        def validate(record: dict[str, Any], _: Path | None) -> tuple[dict[str, Any], list[str], list[str]]:
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.01)
                normalized = json.loads(json.dumps(record))
                normalized["validation"] = {"ok": True, "errors": [], "warnings": []}
                return normalized, [], []
            finally:
                with lock:
                    active -= 1

        with (
            patch.object(importer, "load_json", return_value=schema),
            patch.object(importer, "load_records", return_value=records),
            patch.object(importer.contract, "normalize_record", side_effect=normalize),
            patch.object(importer, "validate_result", side_effect=validate),
        ):
            imported, report = importer.import_with_schema(
                [Path("records.json")],
                Path("schema.json"),
                None,
                workers=4,
            )
        self.assertTrue(report["ok"])
        self.assertEqual(report["validation_workers"], 4)
        self.assertEqual([item["candidate_id"] for item in imported], sorted(item["candidate_id"] for item in records))
        self.assertGreater(maximum, 1)

        duplicate = [records[0], dict(records[0])]
        with (
            patch.object(importer, "load_json", return_value=schema),
            patch.object(importer, "load_records", return_value=duplicate),
            patch.object(importer.contract, "normalize_record", side_effect=normalize),
            patch.object(importer, "validate_result", side_effect=validate),
        ):
            _, report = importer.import_with_schema(
                [Path("duplicates.json")],
                Path("schema.json"),
                None,
                workers=2,
            )
        self.assertFalse(report["ok"])
        self.assertTrue(any("duplicate" in " ".join(item["errors"]) for item in report["failures"]))


if __name__ == "__main__":
    unittest.main()
