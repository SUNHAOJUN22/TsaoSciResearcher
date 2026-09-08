from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_audit():
    path = ROOT / "scripts" / "audit_compute_architecture.py"
    module_name = "tsao_compute_architecture_audit"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


class ComputeArchitectureAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()

    def test_repository_report_is_structured_and_fail_closed(self):
        report = self.audit.build_report(ROOT)
        self.assertTrue(report["ok"], report.get("parse_failures"))
        self.assertGreater(report["summary"]["text_files"], 400)
        self.assertGreater(report["summary"]["python_files"], 50)
        self.assertGreater(report["summary"]["python_lines"], 1000)
        self.assertGreater(report["summary"]["python_source_line_percent"], 0)
        self.assertIn("control-plane", report["architecture"]["python_roles"])
        self.assertTrue(report["non_claims"])

    def test_generated_and_cache_paths_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "kept.py").write_text("import argparse\n", encoding="utf-8")
            cache = root / ".audit-snapshot"
            cache.mkdir()
            (cache / "ignored.py").write_text("import numpy\n", encoding="utf-8")
            report = self.audit.build_report(root)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["python_files"], 1)

    def test_numeric_loop_is_ranked_without_claiming_a_bottleneck(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "kernel.py").write_text(
                "import numpy as np\n"
                "def kernel(values):\n"
                "    total = 0.0\n"
                "    for row in values:\n"
                "        for value in row:\n"
                "            total += value\n"
                "    return np.asarray(total)\n",
                encoding="utf-8",
            )
            report = self.audit.build_report(root)
        self.assertTrue(report["ok"])
        self.assertEqual(report["ranked_static_candidates"][0]["path"], "kernel.py")
        self.assertIn("not runtime profiling", " ".join(report["non_claims"]))

    def test_markdown_contains_composition_and_migration_sequence(self):
        report = self.audit.build_report(ROOT)
        rendered = self.audit.render_markdown(report)
        self.assertIn("Repository composition", rendered)
        self.assertIn("Python source-line share", rendered)
        self.assertIn("Required implementation sequence", rendered)

    def test_invalid_root_is_rejected(self):
        report = self.audit.build_report(ROOT / "not-present")
        self.assertFalse(report["ok"])
        self.assertIn("not a directory", report["errors"][0])


if __name__ == "__main__":
    unittest.main()
