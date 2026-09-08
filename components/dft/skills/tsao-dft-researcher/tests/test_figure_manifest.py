import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_figure_manifest import (  # noqa: E402 -- test import follows explicit scripts path setup
    validate_manifest,
)


class FigureManifestTests(unittest.TestCase):
    def base_manifest(self):
        panel = {
            "id": "a",
            "type": "esp",
            "source_artifact_ids": ["art-1"],
            "method": "wB97X-D",
            "basis": "def2-SVP",
            "phase_or_solvent": "SMD",
            "renderer": "VMD/Tachyon",
            "camera_id": "cam-1",
            "comparison_group": "g",
            "parameters": {
                "density_isovalue_au": 0.001,
                "esp_min": -0.05,
                "esp_max": 0.05,
                "unit": "a.u.",
                "negative_color": "red",
                "positive_color": "blue",
                "palette": "diverging",
            },
        }
        return {
            "schema_version": "1.0",
            "project_id": "p1",
            "figures": [
                {
                    "id": "F1",
                    "title": "ESP",
                    "role": "main",
                    "conclusion": "ESP differs",
                    "evidence_grade": "A",
                    "outputs": ["F1.svg"],
                    "panels": [panel, {**panel, "id": "b"}],
                }
            ],
        }

    def test_valid_shared_scale(self):
        errors, _ = validate_manifest(self.base_manifest(), Path.cwd())
        self.assertEqual(errors, [])

    def test_asymmetric_esp_fails(self):
        data = self.base_manifest()
        data["figures"][0]["panels"][1]["parameters"] = dict(data["figures"][0]["panels"][1]["parameters"])
        data["figures"][0]["panels"][1]["parameters"]["esp_max"] = 0.06
        errors, _ = validate_manifest(data, Path.cwd())
        self.assertTrue(any("symmetric" in error or "differs" in error for error in errors))

    def test_ai_schematic_must_be_labeled(self):
        data = {
            "schema_version": "1.0",
            "project_id": "p1",
            "figures": [
                {
                    "id": "F2",
                    "title": "Workflow",
                    "role": "qa",
                    "conclusion": "workflow",
                    "evidence_grade": "D",
                    "outputs": ["F2.svg"],
                    "panels": [
                        {
                            "id": "a",
                            "type": "schematic",
                            "source_artifact_ids": ["prompt-1"],
                            "ai_generated": True,
                            "illustrative_only": False,
                            "quantitative": False,
                        }
                    ],
                }
            ],
        }
        errors, _ = validate_manifest(data, Path.cwd())
        self.assertTrue(any("illustrative_only" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
