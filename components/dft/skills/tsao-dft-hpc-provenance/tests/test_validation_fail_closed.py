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


def load_script(name: str) -> Any:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"hpc_fail_closed_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HpcValidationFailClosedTests(unittest.TestCase):
    site: Any
    restart: Any
    resources: Any
    site_profile: dict[str, Any]
    lineage: dict[str, Any]
    manifest: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.site = load_script("validate_site_profile.py")
        cls.restart = load_script("validate_restart_lineage.py")
        cls.resources = load_script("estimate_resources.py")
        cls.site_profile = yaml.safe_load((ROOT / "templates/site-profile.yaml").read_text(encoding="utf-8"))
        cls.lineage = yaml.safe_load((ROOT / "templates/restart-lineage.yaml").read_text(encoding="utf-8"))
        cls.manifest = yaml.safe_load((ROOT / "examples/slurm/hpc-manifest.yaml").read_text(encoding="utf-8"))

    def test_site_profile_valid_and_root_paths(self) -> None:
        errors, warnings = self.site.validate(copy.deepcopy(self.site_profile))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIn("root must be a mapping", " ".join(self.site.validate([])[0]))

    def test_site_profile_rejects_wrong_types_credentials_and_limits(self) -> None:
        data = copy.deepcopy(self.site_profile)
        data["software"] = {"vasp": []}
        data["scratch"] = []
        data["security"] = {"contains_credentials": "false", "token": "literal"}
        data["resource_limits"] = {
            "max_nodes": True,
            "max_walltime": "00:99:00",
            "max_memory_gb_per_node": float("nan"),
        }
        data["status"] = "accepted"
        errors, _ = self.site.validate(data)
        rendered = " ".join(errors)
        self.assertIn("software.vasp must be mapping", rendered)
        self.assertIn("scratch must be a mapping", rendered)
        self.assertIn("contains_credentials must be boolean false", rendered)
        self.assertIn("possible credential literal", rendered)
        self.assertIn("max_nodes", rendered)
        self.assertIn("max_walltime", rendered)
        self.assertIn("max_memory", rendered)
        self.assertIn("accepted site profile", rendered)

    def test_restart_valid_and_type_paths(self) -> None:
        errors, warnings = self.restart.validate(copy.deepcopy(self.lineage))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIn("root must be a mapping", " ".join(self.restart.validate([])[0]))
        data = copy.deepcopy(self.lineage)
        data["parent_checkpoint"] = []
        data["parent_method_fingerprint"] = ""
        data["child_method_fingerprint"] = "other"
        data["restart_mode"] = "exact_restart"
        data["changes"] = "bad"
        errors, _ = self.restart.validate(data)
        rendered = " ".join(errors)
        self.assertIn("parent_checkpoint must be a mapping", rendered)
        self.assertIn("sha256 invalid", rendered)
        self.assertIn("parent_method_fingerprint", rendered)
        self.assertIn("identical method fingerprints", rendered)
        self.assertIn("changes must be a list", rendered)

    def test_restart_reuse_warning_blocks_accepted_status(self) -> None:
        data = copy.deepcopy(self.lineage)
        data["restart_mode"] = "geometry_reuse"
        data["changes"] = ["geometry"]
        data["status"] = "accepted"
        errors, warnings = self.restart.validate(data)
        self.assertTrue(any("accepted lineage" in error for error in errors))
        self.assertTrue(any("distinct run" in warning for warning in warnings))

    def test_resource_estimate_exact_types_and_walltime(self) -> None:
        report = self.resources.estimate(copy.deepcopy(self.manifest), 2)
        self.assertTrue(report["ok"])
        self.assertEqual(report["allocated_cpu_hours_total"], 192.0)
        self.assertAlmostEqual(self.resources.hours("1-01:30:00"), 25.5)
        for bad_walltime in ("00:99:00", "1-24:00:00", "bad"):
            with self.assertRaises(ValueError):
                self.resources.hours(bad_walltime)
        with self.assertRaisesRegex(ValueError, "manifest root"):
            self.resources.estimate([], 1)
        with self.assertRaisesRegex(ValueError, "jobs"):
            self.resources.estimate(copy.deepcopy(self.manifest), True)
        bad_manifest = copy.deepcopy(self.manifest)
        bad_manifest["resources"]["memory_gb"] = float("inf")
        with self.assertRaisesRegex(ValueError, "memory_gb"):
            self.resources.estimate(bad_manifest, 1)

    def test_malformed_yaml_is_structured_failure(self) -> None:
        scripts = ("validate_site_profile.py", "validate_restart_lineage.py", "estimate_resources.py")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.yaml"
            path.write_text("resources: [\n", encoding="utf-8")
            for script in scripts:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / script), str(path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertFalse(report["ok"])
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
