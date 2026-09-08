from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"bridge_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BenchmarkBridgeTests(unittest.TestCase):
    bridge: Any
    parser: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = load_script("benchmark_bridge.py")
        cls.parser = load_script("engine_parser_contract.py")

    def test_vasp_bridge_extracts_fields_without_manual_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "INCAR").write_text("ENCUT=500\n", encoding="utf-8")
            out = root / "OUTCAR"
            out.write_text(
                "vasp.6.5.1\nfree energy TOTEN = -10.0 eV\naborting loop because EDIFF is reached\n"
                "General timing and accounting informations for this job\n",
                encoding="utf-8",
            )
            parsed = self.parser.parse_vasp(out)
            manifest = {
                "input": "INCAR",
                "executable": "vasp_std",
                "scheduler": "slurm",
                "resources": {"nodes": 1, "tasks_per_node": 1, "cpus_per_task": 8},
                "acceleration": {
                    "benchmark_plan_id": "PLAN-1",
                    "build_fingerprint_id": "BUILD-1",
                    "gpu_vendor": "none",
                    "gpu_bind": "none",
                },
            }
            fingerprint = {
                "method_fingerprint_id": "MF-1",
                "model_chemistry": {
                    "method": "PBE",
                    "basis_or_pseudopotential": "POTCAR-HASH",
                    "corrections": "none",
                },
                "numerics": {"ediff": 1e-6},
            }
            record = self.bridge.build_record(
                "vasp",
                parsed,
                manifest,
                fingerprint,
                root,
                Path("OUTCAR"),
                "cpu-reference",
                "scientific-reference",
                1,
                runtime={
                    "site_id": "SITE-A",
                    "hardware_fingerprint_id": "HW-A",
                    "run_id": "RUN-1",
                    "timestamp": "2026-07-29T00:00:00Z",
                },
            )
            self.assertEqual(record["engine"]["version"], "6.5.1")
            self.assertEqual(record["scientific"]["results"]["energy_ev"], -10.0)
            self.assertNotIn("engine version", record["evidence_source"]["missing_fields"])

    def test_missing_fields_block_parser_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parsed = self.parser.missing_result("cp2k", root / "missing.out")
            record = self.bridge.build_record(
                "cp2k",
                parsed,
                {"input": "missing.inp", "resources": {}, "acceleration": {}},
                {},
                root,
                Path("missing.out"),
                "gpu-1",
                "acceleration-candidate",
                1,
            )
            self.assertFalse(record["scientific"]["parser_accepted"])
            self.assertEqual(record["evidence_source"]["kind"], "imported-unverified")
            self.assertTrue(record["evidence_source"]["missing_fields"])


if __name__ == "__main__":
    unittest.main()
