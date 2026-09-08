from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTES = ROOT / ".gitattributes"


class PortableLineEndingTests(unittest.TestCase):
    def test_scientific_and_control_text_is_locked_to_lf(self) -> None:
        lines = {
            line.strip()
            for line in ATTRIBUTES.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for pattern in (
            "*.py text eol=lf",
            "*.ps1 text eol=lf",
            "*.sh text eol=lf",
            "*.md text eol=lf",
            "*.yaml text eol=lf",
            "*.yml text eol=lf",
            "*.json text eol=lf",
            "*.jsonl text eol=lf",
            "*.toml text eol=lf",
            "*.csv text eol=lf",
            "*.svg text eol=lf",
            "*.xml text eol=lf",
            "*.tcl text eol=lf",
            "*.xyz text eol=lf",
        ):
            self.assertIn(pattern, lines)

    def test_binary_artifacts_are_not_subject_to_text_conversion(self) -> None:
        lines = {
            line.strip()
            for line in ATTRIBUTES.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for pattern in (
            "*.png binary",
            "*.jpg binary",
            "*.jpeg binary",
            "*.pdf binary",
            "*.zip binary",
            "*.whl binary",
            "*.so binary",
            "*.dll binary",
            "*.dylib binary",
            "*.exe binary",
            "*.pyd binary",
        ):
            self.assertIn(pattern, lines)

    def test_git_resolves_governed_svg_to_lf(self) -> None:
        completed = subprocess.run(
            [
                "git",
                "check-attr",
                "text",
                "eol",
                "--",
                "assets/ai/hero/tsao-dft-hero.svg",
                "templates/benchmark-result.schema.json",
                "scripts/quality_gate.ps1",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        output = completed.stdout.replace("\\", "/")
        for path in (
            "assets/ai/hero/tsao-dft-hero.svg",
            "templates/benchmark-result.schema.json",
            "scripts/quality_gate.ps1",
        ):
            self.assertIn(f"{path}: text: set", output)
            self.assertIn(f"{path}: eol: lf", output)


if __name__ == "__main__":
    unittest.main()
