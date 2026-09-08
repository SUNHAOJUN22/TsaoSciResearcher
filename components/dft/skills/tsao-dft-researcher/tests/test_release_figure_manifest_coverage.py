from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_figure_manifest.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("release_figure_manifest_coverage", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseFigureManifestCoverageTests(unittest.TestCase):
    validator: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()

    def esp_panel(self, panel_id: str = "a") -> dict[str, Any]:
        return {
            "id": panel_id,
            "type": "esp",
            "source_artifact_ids": ["art-1"],
            "method": "wB97X-D",
            "basis": "def2-SVP",
            "phase_or_solvent": "SMD",
            "renderer": "VMD/Tachyon",
            "camera_id": "camera-1",
            "comparison_group": "group-1",
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

    def base_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "project_id": "project-1",
            "figures": [
                {
                    "id": "figure-1",
                    "title": "ESP comparison",
                    "role": "main",
                    "conclusion": "The surfaces differ.",
                    "evidence_grade": "A",
                    "outputs": ["figure-1.svg"],
                    "panels": [self.esp_panel("a"), self.esp_panel("b")],
                }
            ],
        }

    def research_manifest(self) -> dict[str, Any]:
        return {
            "artifacts": [
                {"id": "art-1", "path": "artifact-1.dat"},
                {"id": "art-2", "path": "artifact-2.dat"},
                "ignored",
            ]
        }

    def validate(
        self,
        data: Any,
        *,
        base: Path | None = None,
        research: dict[str, Any] | None = None,
        check_files: bool = False,
    ) -> tuple[list[str], list[str]]:
        return self.validator.validate_manifest(data, base or Path.cwd(), research, check_files)

    def assert_error(self, data: Any, fragment: str, **kwargs: Any) -> None:
        errors, _ = self.validate(data, **kwargs)
        self.assertTrue(any(fragment in error for error in errors), (fragment, errors))

    def assert_warning(self, data: Any, fragment: str, **kwargs: Any) -> None:
        _, warnings = self.validate(data, **kwargs)
        self.assertTrue(any(fragment in warning for warning in warnings), (fragment, warnings))

    def test_root_figure_and_output_contracts(self) -> None:
        self.assert_error([], "root must be an object")
        self.assert_error({}, "figures must be an array")

        non_object = self.base_manifest()
        non_object["figures"] = ["bad"]
        self.assert_error(non_object, "figures[0]: must be an object")

        missing_strings = self.base_manifest()
        missing_strings["project_id"] = ""
        missing_strings["figures"][0]["title"] = ""
        errors, _ = self.validate(missing_strings)
        self.assertTrue(any("project_id" in error for error in errors))
        self.assertTrue(any("title" in error for error in errors))

        duplicate = self.base_manifest()
        duplicate["figures"].append(copy.deepcopy(duplicate["figures"][0]))
        self.assert_error(duplicate, "duplicate figure id")

        invalid_role = self.base_manifest()
        invalid_role["figures"][0]["role"] = "paper"
        self.assert_error(invalid_role, "role must be one of")

        invalid_grade = self.base_manifest()
        invalid_grade["figures"][0]["evidence_grade"] = "E"
        self.assert_error(invalid_grade, "evidence_grade must be A/B/C/D")

        main_d = self.base_manifest()
        main_d["figures"][0]["evidence_grade"] = "D"
        self.assert_error(main_d, "grade D evidence cannot be placed")

        no_outputs = self.base_manifest()
        no_outputs["figures"][0]["outputs"] = []
        self.assert_error(no_outputs, "outputs must be a non-empty list")

        no_panels = self.base_manifest()
        no_panels["figures"][0]["panels"] = []
        self.assert_error(no_panels, "panels must be a non-empty array")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing_output = self.base_manifest()
            self.assert_error(
                missing_output,
                "missing or empty output",
                base=root,
                check_files=True,
            )
            (root / "figure-1.svg").write_text("<svg/>", encoding="utf-8")
            errors, _ = self.validate(missing_output, base=root, check_files=True)
            self.assertFalse(any("missing or empty output" in error for error in errors))

    def test_panel_identity_and_research_links(self) -> None:
        non_object = self.base_manifest()
        non_object["figures"][0]["panels"] = ["bad"]
        self.assert_error(non_object, "panels[0]: must be an object")

        duplicate = self.base_manifest()
        duplicate["figures"][0]["panels"][1]["id"] = "a"
        self.assert_error(duplicate, "duplicate panel id")

        missing_sources = self.base_manifest()
        missing_sources["figures"][0]["panels"][0]["source_artifact_ids"] = []
        self.assert_error(missing_sources, "source_artifact_ids must be a non-empty list")

        absent = self.base_manifest()
        absent["figures"][0]["panels"][0]["source_artifact_ids"] = ["missing"]
        self.assert_error(absent, "is absent from research manifest", research=self.research_manifest())

        valid = self.base_manifest()
        errors, _ = self.validate(valid, research=self.research_manifest())
        self.assertFalse(any("absent from research manifest" in error for error in errors))

    def test_surface_parameter_and_palette_boundaries(self) -> None:
        no_parameters = self.base_manifest()
        no_parameters["figures"][0]["panels"][0]["parameters"] = []
        self.assert_error(no_parameters, "surface panel requires parameters object")

        forbidden = self.base_manifest()
        forbidden["figures"][0]["panels"][0]["parameters"]["palette"] = "jet"
        self.assert_error(forbidden, "forbidden palette jet")

        density = self.base_manifest()
        panel = density["figures"][0]["panels"][0]
        panel["type"] = "spin_density"
        panel["parameters"] = {}
        self.assert_error(density, "signed density panel requires")

    def test_mo_open_shell_boundaries(self) -> None:
        data = self.base_manifest()
        panel = data["figures"][0]["panels"][0]
        panel["type"] = "mo"
        panel["multiplicity"] = 2
        panel["parameters"] = {
            "isovalue_au": 0,
            "orbital_or_state_label": "HOMO",
            "positive_phase_color": "blue",
            "negative_phase_color": "red",
        }
        errors, _ = self.validate(data)
        fragments = (
            "requires positive isovalue_au",
            "must label SOMO or alpha/beta channel",
            "requires spin_channel",
        )
        for fragment in fragments:
            self.assertTrue(any(fragment in error for error in errors), (fragment, errors))

        missing_labels = self.base_manifest()
        mo = missing_labels["figures"][0]["panels"][0]
        mo["type"] = "nto"
        mo["parameters"] = {"isovalue_au": 0.02}
        errors, _ = self.validate(missing_labels)
        self.assertTrue(any("orbital_or_state_label" in error for error in errors))
        self.assertTrue(any("positive_phase_color" in error for error in errors))
        self.assertTrue(any("negative_phase_color" in error for error in errors))

    def test_esp_scale_boundaries(self) -> None:
        missing = self.base_manifest()
        missing["figures"][0]["panels"][0]["parameters"] = {}
        errors, _ = self.validate(missing)
        for field in (
            "density_isovalue_au",
            "esp_min",
            "esp_max",
            "unit",
            "negative_color",
            "positive_color",
        ):
            self.assertTrue(any(f"missing {field}" in error for error in errors), (field, errors))

        no_zero = self.base_manifest()
        no_zero["figures"][0]["panels"][0]["parameters"]["esp_min"] = 0.01
        self.assert_error(no_zero, "ESP scale must cross zero")

        asymmetric = self.base_manifest()
        asymmetric["figures"][0]["panels"][0]["parameters"]["esp_max"] = 0.06
        self.assert_error(asymmetric, "ESP comparison scale must be symmetric")

    def test_quantitative_panel_boundaries(self) -> None:
        data = self.base_manifest()
        panel = data["figures"][0]["panels"][0]
        panel.clear()
        panel.update(
            {
                "id": "quant",
                "type": "bar",
                "source_artifact_ids": ["art-1"],
                "quantitative": False,
                "outputs": ["plot.png"],
            }
        )
        errors, warnings = self.validate(data)
        self.assertTrue(any("quantitative=true" in error for error in errors))
        self.assertTrue(any("requires source_data" in error for error in errors))
        self.assertTrue(any("should provide SVG or PDF" in warning for warning in warnings))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            panel["quantitative"] = True
            panel["source_data"] = "missing.csv"
            self.assert_error(data, "source_data is missing or empty", base=root, check_files=True)
            (root / "missing.csv").write_text("x,y\n1,2\n", encoding="utf-8")
            panel["outputs"] = ["plot.svg"]
            errors, _ = self.validate(data, base=root, check_files=True)
            self.assertFalse(any("source_data is missing" in error for error in errors))

    def test_schematic_and_unknown_panel_boundaries(self) -> None:
        ai = self.base_manifest()
        panel = ai["figures"][0]["panels"][0]
        panel.clear()
        panel.update(
            {
                "id": "schematic",
                "type": "schematic",
                "source_artifact_ids": ["prompt-1"],
                "ai_generated": True,
                "illustrative_only": False,
                "quantitative": True,
                "computed_surface": True,
            }
        )
        errors, _ = self.validate(ai)
        self.assertTrue(any("illustrative_only" in error for error in errors))
        self.assertTrue(any("cannot be marked as a computed surface" in error for error in errors))

        unlabeled = self.base_manifest()
        unlabeled_panel = unlabeled["figures"][0]["panels"][0]
        unlabeled_panel.clear()
        unlabeled_panel.update({"id": "schematic", "type": "schematic", "source_artifact_ids": ["prompt-1"]})
        self.assert_warning(unlabeled, "does not state whether AI generation was used")

        unknown = self.base_manifest()
        unknown["figures"][0]["panels"][0]["type"] = "custom"
        self.assert_warning(unknown, "unrecognized panel type")

    def test_comparison_group_strict_and_exploratory_paths(self) -> None:
        strict = self.base_manifest()
        second = strict["figures"][0]["panels"][1]
        second["method"] = "PBE0"
        second["parameters"]["esp_max"] = 0.06
        errors, _ = self.validate(strict)
        self.assertTrue(any("method differs" in error for error in errors))
        self.assertTrue(any("parameter esp_max differs" in error for error in errors))

        exploratory = self.base_manifest()
        exploratory["figures"][0]["role"] = "exploratory"
        exploratory["figures"][0]["panels"][1]["camera_id"] = "camera-2"
        errors, warnings = self.validate(exploratory)
        self.assertFalse(any("camera_id differs" in error for error in errors))
        self.assertTrue(any("camera_id differs" in warning for warning in warnings))

        singleton = self.base_manifest()
        singleton["figures"][0]["panels"] = [singleton["figures"][0]["panels"][0]]
        errors, _ = self.validate(singleton)
        self.assertEqual(errors, [])

    def test_path_load_self_test_and_cli_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = root / "relative.dat"
            absolute = root / "absolute.dat"
            relative.write_text("data", encoding="utf-8")
            absolute.write_text("data", encoding="utf-8")
            self.assertTrue(self.validator._path_exists(root, "relative.dat"))
            self.assertTrue(self.validator._path_exists(root, str(absolute)))
            self.assertFalse(self.validator._path_exists(root, "missing.dat"))

            manifest_path = root / "figures.json"
            research_path = root / "research.yaml"
            manifest_path.write_text(json.dumps(self.base_manifest()), encoding="utf-8")
            research_path.write_text("artifacts:\n  - id: art-1\n", encoding="utf-8")
            self.assertEqual(self.validator._load(manifest_path)["project_id"], "project-1")
            self.assertEqual(self.validator._load(research_path)["artifacts"][0]["id"], "art-1")

            stdout = io.StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "validate_figure_manifest.py",
                        str(manifest_path),
                        "--research-manifest",
                        str(research_path),
                        "--json",
                    ],
                ),
                redirect_stdout(stdout),
            ):
                self.assertEqual(self.validator.main(), 0)
            self.assertTrue(json.loads(stdout.getvalue())["ok"])

            with (
                patch.object(sys, "argv", ["validate_figure_manifest.py", str(root / "missing.json")]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.validator.main(), 2)

            with (
                patch.object(sys, "argv", ["validate_figure_manifest.py"]),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                self.validator.main()

        with (
            patch.object(sys, "argv", ["validate_figure_manifest.py", "--self-test"]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.validator.main(), 0)


if __name__ == "__main__":
    unittest.main()
