from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_acceleration_contracts.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("tsao_acceleration_contracts", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


contracts = load_module()


def valid_result() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": "run-001",
        "benchmark_plan_id": "plan-001",
        "candidate_id": "gpu-001",
        "engine": "vasp",
        "engine_version": "6.5.1",
        "build_fingerprint": {
            "id": "build-001",
            "sha256": "1" * 64,
            "components": {"compiler": "NVHPC 26.7", "mpi": "OpenMPI 5"},
        },
        "compiler": "NVHPC 26.7",
        "mpi": {
            "implementation": "OpenMPI",
            "version": "5.0",
            "ranks_per_node": 4,
            "cuda_aware": True,
        },
        "openmp_runtime": {
            "implementation": "NVHPC OpenMP",
            "version": "26.7",
            "threads_per_rank": 8,
        },
        "accelerator_runtime": {
            "backend": "openacc",
            "toolkit_version": "CUDA 13",
            "driver_version": "600.1",
        },
        "hardware_fingerprint": {
            "id": "hardware-001",
            "sha256": "2" * 64,
            "cpu": {
                "architecture": "x86_64",
                "model": "EPYC",
                "physical_cores": 64,
                "logical_threads": 128,
                "memory_bytes": 549755813888,
            },
            "accelerators": [
                {
                    "vendor": "nvidia",
                    "model": "H100",
                    "stable_id": "GPU-001",
                    "memory_bytes": 85899345920,
                }
            ],
            "topology": {
                "nodes": 1,
                "gpus_per_node": 4,
                "numa_nodes_per_node": 2,
                "interconnect": "NVLink",
            },
        },
        "binding": {"cpu": "cores", "accelerator": "closest"},
        "scheduler": {"kind": "slurm", "job_id": "12345"},
        "filesystem": {"kind": "lustre", "mount_fingerprint_sha256": "3" * 64},
        "input_sha256": "4" * 64,
        "method_fingerprint_id": "method-001",
        "convergence": {"policy_id": "conv-001", "achieved": True},
        "output_artifact_sha256": "5" * 64,
        "wall_time_seconds": 42.5,
        "cpu_time_seconds": 120.0,
        "scf_iterations": 18,
        "peak_host_memory_bytes": 1000000,
        "peak_device_memory_bytes": 2000000,
        "utilization": {"cpu_percent": 70.0, "accelerator_percent": 92.0, "device_memory_percent": 60.0},
        "scientific_results": {"energy_eV": -10.25, "forces_eV_per_angstrom": [0.1, 0.2, 0.3]},
        "parser_acceptance": "PASS",
        "exit_status": 0,
        "timestamp": "2026-08-05T01:00:00Z",
        "repeat_index": 1,
        "evidence_source": "real-engine-observation",
        "missing_fields": [],
    }


class AccelerationContractTests(unittest.TestCase):
    def test_current_templates_are_executable_and_valid(self) -> None:
        self.assertEqual(contracts.validate_contracts(), [])
        schema = contracts.load_json_mapping(contracts.DEFAULT_SCHEMA)
        self.assertEqual(contracts.validate_result_document(valid_result(), schema), [])

    def test_result_contract_rejects_bypass_values(self) -> None:
        schema = contracts.load_json_mapping(contracts.DEFAULT_SCHEMA)
        cases: list[tuple[str, dict[str, Any]]] = []

        zero_wall = valid_result()
        zero_wall["wall_time_seconds"] = 0
        cases.append(("zero wall time", zero_wall))

        uppercase_hash = valid_result()
        uppercase_hash["input_sha256"] = "A" * 64
        cases.append(("uppercase hash", uppercase_hash))

        extra = valid_result()
        extra["claimed_speedup"] = 99
        cases.append(("unknown field", extra))

        bad_timestamp = valid_result()
        bad_timestamp["timestamp"] = "not-a-date"
        cases.append(("bad timestamp", bad_timestamp))

        bool_integer = valid_result()
        bool_integer["repeat_index"] = True
        cases.append(("boolean integer", bool_integer))

        incomplete = valid_result()
        del incomplete["hardware_fingerprint"]
        cases.append(("incomplete accepted evidence", incomplete))

        nonfinite = valid_result()
        nonfinite["wall_time_seconds"] = float("nan")
        cases.append(("non-finite value", nonfinite))

        for label, document in cases:
            with self.subTest(label=label):
                self.assertTrue(contracts.validate_result_document(document, schema))

    def test_schema_and_policy_mutations_fail_closed(self) -> None:
        schema = contracts.load_json_mapping(contracts.DEFAULT_SCHEMA)
        policy = contracts.load_yaml_mapping(contracts.DEFAULT_POLICY)

        mutated_schema = copy.deepcopy(schema)
        mutated_schema["additionalProperties"] = True
        self.assertIn(
            "benchmark result schema must reject unknown top-level fields",
            contracts.validate_schema_contract(mutated_schema),
        )

        mutated_schema = copy.deepcopy(schema)
        mutated_schema["properties"]["wall_time_seconds"] = {"type": "number", "minimum": 0}
        self.assertIn("wall_time_seconds must be strictly positive", contracts.validate_schema_contract(mutated_schema))

        mutated_policy = copy.deepcopy(policy)
        mutated_policy["minimum_repeats"] = 2
        self.assertIn(
            "performance qualification minimum_repeats must be an integer >= 3",
            contracts.validate_policy_contract(mutated_policy),
        )

        mutated_policy = copy.deepcopy(policy)
        mutated_policy["requirements"]["evidence_source"] = "simulation"
        self.assertIn(
            "performance qualification requirements do not match the executable L3 contract",
            contracts.validate_policy_contract(mutated_policy),
        )

    def test_loaders_and_cli_fail_structurally(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result_path = root / "result.json"
            result_path.write_text(json.dumps(valid_result()), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--result", str(result_path), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["ok"])

            result_path.write_text('{"wall_time_seconds": NaN}', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--result", str(result_path), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["ok"])
            self.assertIn("non-finite JSON constant", " ".join(payload["failures"]))

            policy_path = root / "policy.yaml"
            policy_path.write_text(yaml.safe_dump(["not", "a", "mapping"]), encoding="utf-8")
            failures = contracts.validate_contracts(policy_path=policy_path)
            self.assertTrue(any("YAML contract root must be a mapping" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
