from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from typing import Any

import yaml

# SIMULATION_ONLY
# NOT_REAL_HARDWARE
# NOT_PERFORMANCE_EVIDENCE

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_modules():
    sys.path.insert(0, str(SCRIPTS))
    try:
        contract = importlib.import_module("hardware_optimization_contract")
        policy = importlib.import_module("hardware_provider_policy")
        optimizer = importlib.import_module("hardware_aware_optimizer")
    finally:
        sys.path.remove(str(SCRIPTS))
    return contract, policy, optimizer


def clone(value: dict[str, Any]) -> dict[str, Any]:
    return yaml.safe_load(yaml.safe_dump(value))


def normalized(contract, profile: dict[str, Any]) -> dict[str, Any]:
    errors, _warnings, output = contract.validate_profile(profile)
    if errors:
        raise AssertionError(errors)
    return output


class HardwareAwareOptimizerEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract, cls.policy, cls.optimizer = load_modules()
        cls.base = yaml.safe_load((ROOT / "templates/hardware-optimization-profile.yaml").read_text(encoding="utf-8"))
        cls.edge = yaml.safe_load((ROOT / "templates/edge-inference-profile.yaml").read_text(encoding="utf-8"))

    def test_scalar_and_collection_contracts_fail_closed(self):
        cases: list[tuple[str, dict[str, Any], str]] = []

        bad_evidence = clone(self.base)
        bad_evidence["evidence"] = []
        cases.append(("mapping", bad_evidence, "evidence must be a mapping"))

        missing_id = clone(self.base)
        missing_id["profile_id"] = None
        cases.append(("empty-string", missing_id, "profile_id must be a non-empty string"))

        unavailable_id = clone(self.base)
        unavailable_id["profile_id"] = "NOT_AVAILABLE"
        cases.append(("not-available-string", unavailable_id, "profile_id cannot be NOT_AVAILABLE"))

        zero_nodes = clone(self.base)
        zero_nodes["hardware"]["nodes"] = 0
        cases.append(("minimum-int", zero_nodes, "hardware.nodes must be >= 1"))

        boolean_memory = clone(self.base)
        boolean_memory["hardware"]["memory_gb"] = True
        cases.append(("boolean-number", boolean_memory, "hardware.memory_gb must be numeric"))

        zero_memory = clone(self.base)
        zero_memory["hardware"]["memory_gb"] = 0
        cases.append(("minimum-number", zero_memory, "hardware.memory_gb must be finite and > 0.0"))

        float_cores = clone(self.base)
        float_cores["hardware"]["physical_cores"] = 1.5
        cases.append(("integer-type", float_cores, "hardware.physical_cores must be an integer"))

        zero_cores = clone(self.base)
        zero_cores["hardware"]["physical_cores"] = 0
        cases.append(("integer-minimum", zero_cores, "hardware.physical_cores must be >= 1"))

        labels_not_list = clone(self.base)
        labels_not_list["evidence"]["labels"] = "SIMULATION_ONLY"
        cases.append(("list-type", labels_not_list, "evidence.labels must be a list"))

        bad_label_item = clone(self.base)
        bad_label_item["evidence"]["labels"] = [
            "SIMULATION_ONLY",
            "NOT_REAL_HARDWARE",
            "NOT_PERFORMANCE_EVIDENCE",
            None,
        ]
        cases.append(("list-item", bad_label_item, "evidence.labels[3] must be a non-empty string"))

        string_boolean = clone(self.base)
        string_boolean["software"]["custom_integration"] = "false"
        cases.append(("boolean-type", string_boolean, "software.custom_integration must be boolean"))

        for label, profile, fragment in cases:
            with self.subTest(label=label):
                report = self.optimizer.build_optimization_plan(profile)
                self.assertFalse(report["ok"])
                self.assertIn(fragment, " ".join(report["errors"]))

    def test_enum_hardware_and_missing_value_boundaries(self):
        cases: list[tuple[str, dict[str, Any], str]] = []
        mutations = [
            ("schema", ("schema_version",), "2.0", "schema_version must be 1.0"),
            ("engine", ("engine",), "unknown", "engine must be one of"),
            ("stage", ("stage",), "unknown", "stage must be one of"),
            ("target", ("hardware", "target"), "unknown", "hardware.target must be one of"),
            ("vendor", ("hardware", "gpu_vendor"), "unknown", "hardware.gpu_vendor must be one of"),
            ("backend", ("software", "backend"), "unknown", "software.backend must be one of"),
            ("provider", ("software", "provider"), "unknown", "software.provider must be one of"),
            ("precision", ("policy", "precision"), "unknown", "policy.precision must be one of"),
            ("kernel", ("workload", "expected_kernel"), "unknown-kernel", "workload.expected_kernel must be one of"),
            ("runtime", ("software", "edge_runtime"), "unknown", "software.edge_runtime must be one of"),
            ("source", ("evidence", "source_kind"), "unknown", "evidence.source_kind must be simulation or observed"),
        ]
        for label, path, value, fragment in mutations:
            profile = clone(self.base)
            target: Any = profile
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            cases.append((label, profile, fragment))

        no_vendor = clone(self.base)
        no_vendor["hardware"]["gpu_vendor"] = "none"
        no_vendor["software"]["backend"] = "cpu"
        no_vendor["software"]["libraries"] = []
        no_vendor["software"]["available_libraries"] = []
        cases.append(("gpu-without-vendor", no_vendor, "requires a non-none gpu_vendor"))

        no_gpu = clone(self.base)
        no_gpu["hardware"]["gpus_per_node"] = 0
        cases.append(("accelerator-without-gpu", no_gpu, "accelerator backend requires at least one GPU"))

        bad_threads = clone(self.base)
        bad_threads["hardware"]["logical_threads"] = 32
        cases.append(("logical-less-than-physical", bad_threads, "logical_threads must be >="))

        bad_numa = clone(self.base)
        bad_numa["hardware"]["numa_nodes"] = 128
        cases.append(("numa-more-than-cores", bad_numa, "numa_nodes cannot exceed"))

        for label, profile, fragment in cases:
            with self.subTest(label=label):
                report = self.optimizer.build_optimization_plan(profile)
                self.assertFalse(report["ok"])
                self.assertIn(fragment, " ".join(report["errors"]))

        warning_profile = clone(self.base)
        warning_profile["hardware"]["tasks_per_node"] = 128
        warning_profile["hardware"]["gpu_memory_gb"] = "NOT_AVAILABLE"
        warning_profile["hardware"]["memory_gb"] = "NOT_AVAILABLE"
        warning_profile["hardware"]["memory_bandwidth_gb_s"] = "NOT_AVAILABLE"
        report = self.optimizer.build_optimization_plan(warning_profile)
        self.assertTrue(report["ok"])
        warnings = " ".join(report["warnings"])
        self.assertIn("oversubscription", warnings)
        self.assertIn("GPU memory is NOT_AVAILABLE", warnings)
        self.assertIn("host memory is NOT_AVAILABLE", warnings)
        self.assertIn("memory bandwidth is NOT_AVAILABLE", warnings)

    def test_engine_provider_edge_and_claim_gates(self):
        cases: list[tuple[str, dict[str, Any], str]] = []

        unsupported_engine = clone(self.base)
        unsupported_engine["software"]["engine_build"]["accelerator_supported"] = False
        cases.append(("unsupported-engine-build", unsupported_engine, "accelerator_supported=true"))

        no_fingerprint = clone(self.base)
        no_fingerprint["software"]["engine_build"]["build_fingerprint_id"] = "NOT_AVAILABLE"
        cases.append(("missing-build-fingerprint", no_fingerprint, "immutable build_fingerprint_id"))

        explicit_engine_provider = clone(self.base)
        explicit_engine_provider["software"]["provider"] = "engine-native"
        explicit_engine_provider["software"]["engine_build"]["accelerator_supported"] = False
        cases.append(("engine-provider", explicit_engine_provider, "engine-native provider requires"))

        custom_provider = clone(self.base)
        custom_provider["stage"] = "postprocessing"
        custom_provider["software"]["provider"] = "custom-native"
        custom_provider["software"]["engine_build"] = {
            "accelerator_supported": False,
            "build_fingerprint_id": "NOT_AVAILABLE",
        }
        cases.append(("custom-provider", custom_provider, "custom-native provider requires"))

        no_cpu_reference = clone(self.base)
        no_cpu_reference["policy"]["require_cpu_fp64_reference"] = False
        cases.append(("cpu-reference", no_cpu_reference, "require_cpu_fp64_reference must remain true"))

        no_cpu_fallback = clone(self.base)
        no_cpu_fallback["policy"]["require_cpu_fallback"] = False
        cases.append(("cpu-fallback", no_cpu_fallback, "require_cpu_fallback=true"))

        no_remote_fallback = clone(self.edge)
        no_remote_fallback["policy"]["remote_dft_fallback"] = False
        cases.append(("edge-fallback", no_remote_fallback, "remote DFT fallback"))

        edge_engine = clone(self.base)
        edge_engine["hardware"]["target"] = "edge"
        edge_engine["software"]["provider"] = "cpu"
        cases.append(("edge-engine-provider", edge_engine, "edge engine plans must use the remote-dft provider"))

        requested_claim = clone(self.base)
        requested_claim["policy"]["requested_speedup_claim"] = True
        cases.append(("speedup-claim", requested_claim, "requested_speedup_claim is forbidden"))

        wrong_vendor_library = clone(self.base)
        wrong_vendor_library["software"]["libraries"] = ["rocBLAS"]
        cases.append(("vendor-library", wrong_vendor_library, "targets amd"))

        wrong_tensorrt_scope = clone(self.base)
        wrong_tensorrt_scope["software"]["libraries"] = ["TensorRT"]
        cases.append(("tensorrt-scope", wrong_tensorrt_scope, "TensorRT is limited"))

        wrong_openvino_scope = clone(self.base)
        wrong_openvino_scope["software"]["libraries"] = ["OpenVINO"]
        cases.append(("openvino-scope", wrong_openvino_scope, "OpenVINO is limited"))

        for label, profile, fragment in cases:
            with self.subTest(label=label):
                report = self.optimizer.build_optimization_plan(profile)
                self.assertFalse(report["ok"])
                self.assertIn(fragment, " ".join(report["errors"]))

    def test_bottleneck_classification_matrix(self):
        base = normalized(self.contract, clone(self.base))
        cases: list[tuple[str, dict[str, Any], str]] = []

        explicit = clone(base)
        explicit["expected_kernel"] = "io"
        cases.append(("explicit", explicit, "io"))

        edge_engine = clone(base)
        edge_engine["target"] = "edge"
        cases.append(("edge-engine", edge_engine, "communication"))

        ml_transfer = clone(base)
        ml_transfer["stage"] = "ml-surrogate"
        ml_transfer["workload"] = {
            "estimated_transfer_gb": 4,
            "arithmetic_intensity_flop_per_byte": 10,
        }
        cases.append(("ml-low-intensity-transfer", ml_transfer, "transfer"))

        ml_memory_transfer = clone(base)
        ml_memory_transfer["stage"] = "ml-surrogate"
        ml_memory_transfer["gpu_memory_gb"] = 4.0
        ml_memory_transfer["workload"] = {
            "estimated_transfer_gb": 3,
            "arithmetic_intensity_flop_per_byte": 100,
        }
        cases.append(("ml-device-capacity-transfer", ml_memory_transfer, "transfer"))

        ml_tensor = clone(base)
        ml_tensor["stage"] = "ml-surrogate"
        ml_tensor["workload"] = {}
        cases.append(("ml-tensor", ml_tensor, "tensor"))

        post_tensor = clone(base)
        post_tensor["stage"] = "postprocessing"
        post_tensor["workload"] = {"tensor_order": 3}
        cases.append(("post-tensor", post_tensor, "tensor"))

        post_io = clone(base)
        post_io["stage"] = "postprocessing"
        post_io["workload"] = {"tensor_order": 2}
        cases.append(("post-io", post_io, "io"))

        workflow_multi = clone(base)
        workflow_multi["stage"] = "workflow"
        workflow_multi["nodes"] = 2
        cases.append(("workflow-multi", workflow_multi, "communication"))

        workflow_single = clone(base)
        workflow_single["stage"] = "workflow"
        workflow_single["nodes"] = 1
        cases.append(("workflow-single", workflow_single, "io"))

        vasp_communication = clone(base)
        vasp_communication["workload"] = {"kpoints": 8}
        cases.append(("vasp-communication", vasp_communication, "communication"))

        vasp_dense = clone(base)
        vasp_dense["workload"] = {"kpoints": 1}
        cases.append(("vasp-dense", vasp_dense, "dense-solve"))

        cp2k_dense = clone(base)
        cp2k_dense["engine"] = "cp2k"
        cp2k_dense["workload"] = {"atoms": 100, "model": "gpw"}
        cases.append(("cp2k-dense", cp2k_dense, "dense-solve"))

        gaussian_dense = clone(base)
        gaussian_dense["engine"] = "gaussian"
        gaussian_dense["workload"] = {"basis_functions": 2000}
        cases.append(("gaussian-dense", gaussian_dense, "dense-solve"))

        generic_unknown = clone(base)
        generic_unknown["engine"] = "generic"
        generic_unknown["workload"] = {}
        cases.append(("generic-unknown", generic_unknown, "unknown"))

        for label, profile, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(self.policy.classify_bottleneck(profile), expected)

    def test_provider_runtime_and_resource_layout_matrix(self):
        base = normalized(self.contract, clone(self.base))

        explicit = clone(base)
        explicit["provider"] = "custom-native"
        self.assertEqual(self.policy.select_provider(explicit), ("custom-native", None))

        remote = clone(base)
        remote["target"] = "edge"
        self.assertEqual(self.policy.select_provider(remote), ("remote-dft", None))

        custom = clone(base)
        custom["stage"] = "postprocessing"
        custom["backend"] = "cuda"
        custom["custom_integration"] = True
        self.assertEqual(self.policy.select_provider(custom), ("custom-native", None))

        array_api = clone(base)
        array_api["stage"] = "postprocessing"
        array_api["custom_integration"] = False
        self.assertEqual(self.policy.select_provider(array_api), ("array-api", None))

        cpu = clone(base)
        cpu["stage"] = "workflow"
        cpu["backend"] = "cpu"
        self.assertEqual(self.policy.select_provider(cpu), ("cpu", None))

        nvidia_runtime = clone(base)
        nvidia_runtime["target"] = "edge"
        nvidia_runtime["stage"] = "ml-surrogate"
        nvidia_runtime["edge_runtime"] = "auto"
        nvidia_runtime["libraries"] = ["tensorrt"]
        self.assertEqual(self.policy.select_provider(nvidia_runtime), ("edge-runtime", "tensorrt"))

        intel_runtime = clone(nvidia_runtime)
        intel_runtime["vendor"] = "intel"
        intel_runtime["libraries"] = ["openvino"]
        self.assertEqual(self.policy.select_provider(intel_runtime), ("edge-runtime", "openvino"))

        portable_runtime = clone(nvidia_runtime)
        portable_runtime["vendor"] = "amd"
        portable_runtime["libraries"] = []
        self.assertEqual(self.policy.select_provider(portable_runtime), ("edge-runtime", "onnxruntime"))

        no_cpu_topology = clone(base)
        no_cpu_topology["physical_cores"] = None
        no_cpu_topology["cpus_per_gpu"] = None
        layout, assumptions = self.policy.resource_layout(no_cpu_topology, "engine-native")
        self.assertEqual(layout["openmp_threads"], 1)
        self.assertTrue(any("conservatively one thread" in item for item in assumptions))

        cpu_unknown = clone(base)
        cpu_unknown["backend"] = "cpu"
        cpu_unknown["gpus"] = 0
        cpu_unknown["physical_cores"] = None
        cpu_unknown["tasks_per_node"] = None
        layout, assumptions = self.policy.resource_layout(cpu_unknown, "cpu")
        self.assertEqual(layout["mpi_ranks_per_node"], 1)
        self.assertEqual(layout["openmp_threads"], 1)
        self.assertEqual(len(assumptions), 2)

        edge_layout, _ = self.policy.resource_layout(nvidia_runtime, "edge-runtime")
        self.assertEqual(edge_layout["gpus_per_node"], nvidia_runtime["gpus"])

        remote_layout, _ = self.policy.resource_layout(remote, "remote-dft")
        self.assertEqual(remote_layout["gpus_per_node"], 0)

    def test_library_assessment_availability_and_safety_edges(self):
        base = normalized(self.contract, clone(self.base))

        single_gpu = clone(base)
        single_gpu["gpus"] = 1
        single_gpu["nodes"] = 1
        single_gpu["libraries"] = ["nccl"]
        single_gpu["available_libraries"] = ["nccl"]
        rows = self.policy.library_assessment(single_gpu, "communication", "engine-native", None)
        nccl = next(row for row in rows if row["name"] == "nccl")
        self.assertEqual(nccl["decision"], "optional")
        self.assertEqual(nccl["availability"], "SIMULATED_AVAILABLE")
        self.assertIn("manifest injection is forbidden", nccl["reason"])

        observed = clone(base)
        observed["source_kind"] = "observed"
        observed["libraries"] = ["cufft"]
        observed["available_libraries"] = ["cufft"]
        rows = self.policy.library_assessment(observed, "fft", "engine-native", None)
        cufft = next(row for row in rows if row["name"] == "cufft")
        self.assertEqual(cufft["availability"], "DECLARED_AVAILABLE")

        blocked = clone(base)
        blocked["stage"] = "ml-surrogate"
        blocked["libraries"] = ["cuequivariance"]
        blocked["available_libraries"] = []
        blocked["model_family"] = "ridge"
        rows = self.policy.library_assessment(blocked, "tensor", "array-api", None)
        cueq = next(row for row in rows if row["name"] == "cuequivariance")
        self.assertEqual(cueq["decision"], "blocked")
        self.assertEqual(cueq["availability"], "NOT_AVAILABLE")

        requirements = self.policy.validation_requirements(blocked, "transfer", "edge-runtime")
        rendered = " ".join(requirements)
        self.assertIn("host-device bytes", rendered)
        self.assertIn("interconnect", rendered)
        self.assertIn("out-of-domain", rendered)


if __name__ == "__main__":
    unittest.main()
