from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
HPC = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AccelerationRegistrySingleSourceTests(unittest.TestCase):
    def test_public_planners_load_runtime_views_from_canonical_registry(self) -> None:
        registry = load_module("tsao_single_source_registry", HPC / "acceleration_registry.py")
        plan = load_module("tsao_single_source_plan", HPC / "plan_acceleration.py")
        optimizer = load_module(
            "tsao_single_source_optimizer",
            HPC / "hardware_optimization_contract.py",
        )
        self.assertEqual(plan.LIBRARIES, registry.plan_libraries())
        self.assertEqual(plan.ALIASES, registry.plan_aliases())
        self.assertEqual(plan.BACKEND_BY_VENDOR, registry.BACKEND_BY_VENDOR)
        self.assertEqual(optimizer.LIBRARIES, registry.optimizer_libraries())
        self.assertEqual(optimizer.ALIASES, registry.optimizer_aliases())

    def test_planners_do_not_define_mirror_catalogs(self) -> None:
        for name in ("plan_acceleration.py", "hardware_optimization_contract.py"):
            source = (HPC / name).read_text(encoding="utf-8")
            self.assertNotIn("def _library(", source)
            self.assertIn("def _load_acceleration_registry()", source)


if __name__ == "__main__":
    unittest.main()
