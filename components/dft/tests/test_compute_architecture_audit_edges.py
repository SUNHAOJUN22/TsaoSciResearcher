from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "scripts" / "audit_compute_architecture.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = load_module("tsao_compute_architecture_edge_tests", AUDIT_PATH)


class ComputeArchitectureAuditEdgeTests(unittest.TestCase):
    def test_tracked_paths_fall_back_without_git_or_after_probe_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kept = root / "kept.py"
            kept.write_text("value = 1\n", encoding="utf-8")
            with patch.object(audit.shutil, "which", return_value=None):
                self.assertEqual(audit._tracked_paths(root), [kept])
            with (
                patch.object(audit.shutil, "which", return_value="/usr/bin/git"),
                patch.object(audit.subprocess, "run", side_effect=OSError("blocked")),
            ):
                self.assertEqual(audit._tracked_paths(root), [kept])

    def test_text_reader_rejects_binary_invalid_utf8_and_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "binary.dat"
            binary.write_bytes(b"a\0b")
            invalid = root / "invalid.txt"
            invalid.write_bytes(b"\xff")
            self.assertIsNone(audit._read_text(binary))
            self.assertIsNone(audit._read_text(invalid))
            self.assertIsNone(audit._read_text(root / "missing.txt"))

    def test_candidate_actions_cover_batch_parallel_and_threshold_paths(self) -> None:
        batch = SimpleNamespace(nested_loops=0, loops=0, file_reads=4, subprocess_calls=0)
        parallel = SimpleNamespace(nested_loops=0, loops=0, file_reads=0, subprocess_calls=4)
        quiet = SimpleNamespace(nested_loops=0, loops=1, file_reads=0, subprocess_calls=0)
        batch_result = audit._candidate("batch.py", batch, False)
        parallel_result = audit._candidate("parallel.py", parallel, False)
        self.assertEqual(batch_result["recommended_action"], "batch-or-stream-io-before-changing-language")
        self.assertEqual(
            parallel_result["recommended_action"],
            "parallelize-independent-processes-with-bounded-workers",
        )
        self.assertIsNone(audit._candidate("quiet.py", quiet, False))

    def test_report_surfaces_parse_failures_roles_parallel_gpu_and_engine_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "invalid.py").write_text("def broken(:\n", encoding="utf-8")
            (root / "mixed.py").write_text(
                "import argparse\nimport numpy\n"
                "from concurrent.futures import ProcessPoolExecutor\n"
                "def work(values):\n"
                "    for row in values:\n"
                "        for value in row:\n"
                "            print(value)\n"
                "    return numpy.asarray(values)\n"
                "CUDA = '__dlpack__'\n",
                encoding="utf-8",
            )
            (root / "engine.sh").write_text("vasp_std\n", encoding="utf-8")
            report = audit.build_report(root)
        self.assertFalse(report["ok"])
        self.assertEqual(report["parse_failures"][0]["path"], "invalid.py")
        self.assertEqual(report["architecture"]["python_roles"]["mixed-control-and-numeric"], 1)
        self.assertIn("mixed.py", report["architecture"]["parallel_or_distributed_files"])
        self.assertIn("mixed.py", report["architecture"]["gpu_or_array_interface_files"])
        self.assertIn("engine.sh", report["architecture"]["external_engine_boundary_files"])

    def test_markdown_failure_empty_candidate_write_and_cli_outputs(self) -> None:
        failed = audit.render_markdown({"ok": False, "errors": ["fixture"]})
        self.assertIn("Audit failed", failed)
        self.assertIn("fixture", failed)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plain.py").write_text("value = 1\n", encoding="utf-8")
            report = audit.build_report(root)
            rendered = audit.render_markdown(report)
            self.assertIn("No static candidate crossed", rendered)
            output = root / "nested" / "report.txt"
            audit._write(None, "ignored")
            audit._write(output, "written")
            self.assertEqual(output.read_text(encoding="utf-8"), "written")

            json_out = root / "audit.json"
            markdown_out = root / "audit.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_PATH),
                    "--root",
                    str(root),
                    "--json",
                    "--json-out",
                    str(json_out),
                    "--markdown-out",
                    str(markdown_out),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["ok"])
            self.assertTrue(json.loads(json_out.read_text(encoding="utf-8"))["ok"])
            self.assertIn("Compute Architecture Audit", markdown_out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
