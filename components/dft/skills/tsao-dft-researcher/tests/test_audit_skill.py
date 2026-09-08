from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


class AuditSkillTests(unittest.TestCase):
    @staticmethod
    def load_auditor() -> Any:
        skill = Path(__file__).resolve().parents[1]
        path = skill / "scripts" / "audit_skill.py"
        spec = importlib.util.spec_from_file_location("tsao_audit_skill", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_package_static_audit_passes(self) -> None:
        skill = Path(__file__).resolve().parents[1]
        script = skill / "scripts" / "audit_skill.py"
        result = subprocess.run(
            [sys.executable, str(script), str(skill), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"ok": true', result.stdout)

    def test_manifest_paths_cannot_escape_skill_root(self) -> None:
        auditor = self.load_auditor()
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = parent / "skill"
            skill.mkdir()
            inside = skill / "inside.md"
            inside.write_text("inside", encoding="utf-8")
            outside = parent / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            self.assertEqual(auditor.contained_path(skill, "inside.md"), inside.resolve())
            self.assertIsNone(auditor.contained_path(skill, "../outside.md"))
            self.assertIsNone(auditor.contained_path(skill, str(outside.resolve())))
            link = skill / "outside-link.md"
            try:
                link.symlink_to(outside)
            except OSError:
                return
            self.assertIsNone(auditor.contained_path(skill, "outside-link.md"))


if __name__ == "__main__":
    unittest.main()
