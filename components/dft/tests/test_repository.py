import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    "tsao-dft-suite",
    "tsao-dft-researcher",
    "tsao-structure-prep",
    "tsao-periodic-dft-materials",
    "tsao-dft-ml-active-learning",
    "tsao-dft-hpc-provenance",
    "tsao-dft-kinetics-multiscale",
    "tsao-dft-catalysis-profile",
]
DEMOS = [
    "workflow-architecture",
    "wavefunction-esp-gallery",
    "free-energy-profile",
    "dft-ml-dashboard",
    "periodic-dft-materials",
    "active-learning-loop",
    "hpc-provenance",
    "multiscale-kinetics",
]


class RepositoryTests(unittest.TestCase):
    @staticmethod
    def load_repository_validator() -> Any:
        path = ROOT / "scripts" / "validate_repo.py"
        spec = importlib.util.spec_from_file_location("tsao_validate_repo", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_required_skills(self):
        for skill_name in SKILLS:
            base = ROOT / "skills" / skill_name
            self.assertTrue((base / "SKILL.md").exists())
            self.assertTrue((base / "catalog.yaml").exists())

    def test_readme_demo_assets(self):
        for stem in DEMOS:
            path = ROOT / f"assets/demo/{stem}.svg"
            self.assertGreater(path.stat().st_size, 800)
            self.assertIn("SYNTHETIC DEMO", path.read_text(encoding="utf-8"))

    def test_demo_regeneration_is_deterministic(self):
        def hashes():
            return {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((ROOT / "assets/demo").glob("*.svg"))
            }

        before = hashes()
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_readme_demos.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, hashes())

    def test_catalog(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_catalog.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installer_dry_run(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/install.py"),
                "--agent",
                "codex",
                "--scope",
                "project",
                "--skill",
                "all",
                "--dry-run",
                "--validate",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_support_docs_and_plugin(self):
        for rel in [
            "docs/ENGINE_SUPPORT_MATRIX.md",
            "docs/CAPABILITY_STATUS.yaml",
            "docs/CROSS_SKILL_HANDOFF.md",
            "docs/DFT_VALIDATION_LADDER.md",
            ".codex-plugin/plugin.json",
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)
        data = yaml.safe_load((ROOT / "docs/CAPABILITY_STATUS.yaml").read_text(encoding="utf-8"))
        self.assertEqual(data["release"], "0.4.0-alpha.2")

    def test_repo_validator(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_repo.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_paths_cannot_escape_repository_scope(self):
        validator = self.load_repository_validator()
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = parent / "skill"
            skill.mkdir()
            inside = skill / "inside.md"
            inside.write_text("inside", encoding="utf-8")
            outside = parent / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            self.assertEqual(validator.contained_path(skill, "inside.md"), inside.resolve())
            self.assertIsNone(validator.contained_path(skill, "../outside.md"))
            self.assertIsNone(validator.contained_path(skill, str(outside.resolve())))
            link = skill / "outside-link.md"
            try:
                link.symlink_to(outside)
            except OSError:
                return
            self.assertIsNone(validator.contained_path(skill, "outside-link.md"))


if __name__ == "__main__":
    unittest.main()
