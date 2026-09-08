from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CURATED_DEMOS = {
    "assets/demo/workflow-architecture.svg",
    "assets/demo/wavefunction-esp-gallery.svg",
    "assets/demo/dft-ml-dashboard.svg",
    "assets/demo/periodic-dft-materials.svg",
    "assets/demo/multiscale-kinetics.svg",
    "assets/demo/hybrid-compute-architecture.svg",
    "assets/demo/cuda-x-decision-map.svg",
    "assets/demo/edge-hpc-closed-loop.svg",
    "assets/demo/native-acceleration-roadmap.svg",
    "assets/demo/evidence-qualification-pipeline.svg",
    "assets/demo/acceleration-registry-governance.svg",
    "assets/demo/backend-portability-stack.svg",
    "assets/demo/windows-linux-execution-matrix.svg",
    "assets/demo/scientific-acceleration-funnel.svg",
}


def load_demo_validator():
    path = ROOT / "scripts" / "generate_readme_demos.py"
    spec = importlib.util.spec_from_file_location("tsao_demo_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadmeVisualTests(unittest.TestCase):
    def test_all_governed_ai_assets_are_embedded(self):
        manifest = yaml.safe_load((ROOT / "assets/ai/manifest.yaml").read_text(encoding="utf-8"))
        readmes = [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README_EN.md").read_text(encoding="utf-8"),
        ]
        for item in manifest["assets"]:
            for readme in readmes:
                self.assertIn(item["path"], readme)

    def test_readmes_use_minimal_ai_and_curated_demos(self):
        for readme_name in ("README.md", "README_EN.md"):
            readme = (ROOT / readme_name).read_text(encoding="utf-8")
            self.assertEqual(readme.count("assets/ai/"), 1)
            self.assertNotIn("assets/ai/modules/", readme)
            for demo in CURATED_DEMOS:
                self.assertIn(demo, readme)
        self.assertIn("AI图像声明", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("AI image declaration", (ROOT / "README_EN.md").read_text(encoding="utf-8"))
        hero = (ROOT / "assets/ai/hero/tsao-dft-hero.svg").read_text(encoding="utf-8")
        self.assertIn("NOT COMPUTATIONAL DATA", hero)

    def test_demo_validator_is_read_only_when_assets_are_missing(self):
        module = load_demo_validator()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "assets" / "demo"
            out.mkdir(parents=True)
            module.ROOT = root
            module.OUT = out
            failures, checked = module.validate()
            self.assertEqual(checked, [])
            self.assertEqual(list(out.iterdir()), [])
            self.assertEqual(sum(item.startswith("missing demo asset:") for item in failures), len(module.DEMO_SPECS))

    def test_demo_asset_validator_cli(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_readme_demos.py")], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("README demo asset validation: PASS", result.stdout)

    def test_readme_visual_validator(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_readme_visuals.py"), "--strict"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
