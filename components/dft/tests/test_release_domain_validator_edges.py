from __future__ import annotations

import importlib.metadata
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(relative: str, name: str) -> Any:
    path = ROOT / relative
    script_dir = path.parent
    previous_path = list(sys.path)
    sentinel = object()
    previous_utils: object = sys.modules.get("utils", sentinel)
    try:
        sys.path.insert(0, str(script_dir))
        local_utils = script_dir / "utils.py"
        if local_utils.is_file():
            utils_spec = importlib.util.spec_from_file_location("utils", local_utils)
            if utils_spec is None or utils_spec.loader is None:
                raise RuntimeError(f"cannot import {local_utils}")
            utils_module = importlib.util.module_from_spec(utils_spec)
            sys.modules["utils"] = utils_module
            utils_spec.loader.exec_module(utils_module)
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = previous_path
        if previous_utils is sentinel:
            sys.modules.pop("utils", None)
        else:
            assert isinstance(previous_utils, ModuleType)
            sys.modules["utils"] = previous_utils


class ReleaseDomainValidatorEdgesTests(unittest.TestCase):
    structure: Any
    periodic: Any
    vasp: Any
    vmd: Any
    environment: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.structure = load_script(
            "skills/tsao-structure-prep/scripts/validate_structure_manifest.py",
            "release_structure_manifest_edges",
        )
        cls.periodic = load_script(
            "skills/tsao-periodic-dft-materials/scripts/validate_periodic_manifest.py",
            "release_periodic_manifest_edges",
        )
        cls.vasp = load_script(
            "skills/tsao-periodic-dft-materials/scripts/preflight_vasp.py",
            "release_vasp_preflight_edges",
        )
        cls.vmd = load_script(
            "skills/tsao-dft-researcher/scripts/make_vmd_tcl.py",
            "release_vmd_generator_edges",
        )
        cls.environment = load_script(
            "skills/tsao-dft-hpc-provenance/scripts/inspect_execution_environment.py",
            "release_environment_inspection_edges",
        )

    def test_three_utils_modules_all_contracts(self) -> None:
        paths = (
            "skills/tsao-dft-hpc-provenance/scripts/utils.py",
            "skills/tsao-structure-prep/scripts/utils.py",
            "skills/tsao-dft-researcher/scripts/utils.py",
        )
        for index, relative in enumerate(paths):
            with self.subTest(module=relative), tempfile.TemporaryDirectory() as temporary:
                module = load_script(relative, f"release_utils_{index}")
                root = Path(temporary)
                source = root / "source.yaml"
                source.write_text("a: 1\n", encoding="utf-8")
                self.assertEqual(module.load_yaml(source), {"a": 1})
                source.write_text("- bad\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    module.load_yaml(source)
                target = root / "nested" / "dump.yaml"
                module.dump_yaml({"b": 2}, target)
                self.assertEqual(yaml.safe_load(target.read_text(encoding="utf-8")), {"b": 2})
                self.assertEqual(len(module.sha256_file(target)), 64)
                with redirect_stdout(io.StringIO()) as stdout:
                    module.print_result({"ok": True}, as_json=True)
                self.assertTrue(json.loads(stdout.getvalue())["ok"])
                with redirect_stdout(io.StringIO()) as stdout:
                    module.print_result({"a": 1, "b": 2})
                self.assertIn("a: 1", stdout.getvalue())

    def structure_base(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "structure_id": "S-1",
            "model_type": "molecule",
            "source": {"path": "unknown", "sha256": "unknown"},
            "length_unit": "angstrom",
            "periodicity": "none",
            "charge_candidates": [0],
            "multiplicity_candidates": [1],
            "transformations": [],
            "review": {"status": "draft", "checks": {}},
        }

    def test_structure_manifest_source_and_scalar_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            errors, warnings = self.structure.validate(self.structure_base(), root)
            self.assertEqual(errors, [])
            self.assertIn("source path unresolved", warnings)

            invalid: dict[str, Any] = {
                "model_type": "bad",
                "source": {},
                "length_unit": "meter",
                "charge_candidates": [0.5],
                "multiplicity_candidates": [0, "one"],
                "transformations": [{}],
                "review": {"status": "bad"},
            }
            errors, warnings = self.structure.validate(invalid, root)
            self.assertGreater(len(errors), 10)
            self.assertIn("source path unresolved", warnings)

            missing_source = self.structure_base()
            missing_source["source"] = {"path": "missing.xyz"}
            _, warnings = self.structure.validate(missing_source, root)
            self.assertTrue(any("source file not found" in warning for warning in warnings))

            source = root / "source.xyz"
            source.write_text("H 0 0 0\n", encoding="utf-8")
            no_hash = self.structure_base()
            no_hash["source"] = {"path": source.name}
            _, warnings = self.structure.validate(no_hash, root)
            self.assertIn("source sha256 not recorded", warnings)

            malformed = self.structure_base()
            malformed["source"] = {"path": source.name, "sha256": "bad"}
            errors, _ = self.structure.validate(malformed, root)
            self.assertIn("source sha256 malformed", errors)

            mismatch = self.structure_base()
            mismatch["source"] = {"path": source.name, "sha256": "0" * 64}
            errors, _ = self.structure.validate(mismatch, root)
            self.assertIn("source sha256 mismatch", errors)

            digest = load_script(
                "skills/tsao-structure-prep/scripts/utils.py",
                "release_structure_utils_digest",
            ).sha256_file(source)
            valid = self.structure_base()
            valid["source"] = {"path": source.name, "sha256": digest}
            self.assertEqual(self.structure.validate(valid, root), ([], []))

    def test_structure_manifest_periodic_review_and_cli_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            periodic = self.structure_base()
            periodic["model_type"] = "slab"
            periodic["periodic_model"] = {"vacuum_angstrom": "bad"}
            errors, _ = self.structure.validate(periodic, root)
            self.assertTrue(any("periodic_model missing" in error for error in errors))
            self.assertIn("vacuum_angstrom must be numeric", errors)

            negative = self.structure_base()
            negative["model_type"] = "defect"
            negative["periodic_model"] = {
                "cell": [],
                "vacuum_angstrom": 0,
                "periodic_image_separation_angstrom": 10,
                "termination_or_defect": "vacancy",
                "fixed_region_policy": "none",
                "charge_correction_policy": "review",
            }
            errors, _ = self.structure.validate(negative, root)
            self.assertIn("vacuum_angstrom must be positive", errors)

            reviewed = self.structure_base()
            reviewed["review"] = {"status": "reviewed", "checks": {"identity": True}}
            errors, _ = self.structure.validate(reviewed, root)
            self.assertTrue(any("missing passed check" in error for error in errors))

            accepted = self.structure_base()
            accepted["review"] = {
                "status": "accepted",
                "checks": {
                    "identity": True,
                    "valence_or_stoichiometry": True,
                    "closest_contacts": True,
                    "atom_order": True,
                    "model_intent": True,
                },
            }
            errors, _ = self.structure.validate(accepted, root)
            self.assertIn("accepted structure has unresolved validation errors/warnings", errors)

            manifest = root / "manifest.yaml"
            manifest.write_text(yaml.safe_dump(self.structure_base()), encoding="utf-8")
            with (
                patch.object(sys, "argv", ["validate_structure_manifest.py", str(manifest), "--json"]),
                redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                self.structure.main()
            self.assertEqual(raised.exception.code, 0)

            manifest.write_text("{}\n", encoding="utf-8")
            with (
                patch.object(sys, "argv", ["validate_structure_manifest.py", str(manifest)]),
                redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                self.structure.main()
            self.assertEqual(raised.exception.code, 1)

    def periodic_base(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "project_id": "P-1",
            "engine": "vasp",
            "engine_version": "6.5",
            "support_level": "L2_VALIDATED_ADAPTER",
            "task_type": "static",
            "structure_id": "S-1",
            "structure_sha256": "a" * 64,
            "method_fingerprint": {
                "xc": "PBE",
                "dispersion": "none",
                "basis_or_pseudopotential_family": "PAW",
                "cutoff_or_grid_policy": "converged",
                "kpoint_or_supercell_policy": "converged",
                "smearing_or_occupations": "fixed",
                "spin_and_u_policy": "reviewed",
                "electrostatics": "periodic",
                "convergence_thresholds": {"ediff": 1e-6},
            },
            "convergence": {"studies": ["cutoff"]},
            "validation_plan": {"technical_checks": ["termination"], "scientific_checks": ["energy"]},
            "status": "planned",
        }

    def test_periodic_manifest_task_specific_boundaries(self) -> None:
        errors, warnings = self.periodic.validate({})
        self.assertGreater(len(errors), 10)
        self.assertTrue(warnings)
        self.assertEqual(self.periodic.validate(self.periodic_base()), ([], []))

        unresolved = self.periodic_base()
        unresolved["method_fingerprint"] = {}
        unresolved["convergence"] = {}
        _, warnings = self.periodic.validate(unresolved)
        self.assertGreaterEqual(len(warnings), 10)

        for task in ("band", "dos", "charge", "phonon", "elastic"):
            data = self.periodic_base()
            data["task_type"] = task
            errors, _ = self.periodic.validate(data)
            self.assertTrue(any("requires accepted" in error for error in errors), (task, errors))

        surface = self.periodic_base()
        surface["task_type"] = "surface"
        errors, _ = self.periodic.validate(surface)
        self.assertTrue(any("model_review_id" in error for error in errors))
        self.assertTrue(any("periodic_model missing" in error for error in errors))

        adsorption = self.periodic_base()
        adsorption["task_type"] = "adsorption"
        adsorption["model_review_id"] = "R-1"
        adsorption["periodic_model"] = {
            "cell_or_supercell": "cell",
            "vacuum_policy": "20A",
            "termination_or_defect": "surface",
            "fixed_region_policy": "bottom",
            "dipole_or_polarity_policy": "dipole",
            "periodic_image_policy": "reviewed",
        }
        adsorption["energy_expression"] = {"formula": "unknown", "reference_artifact_ids": ["clean"]}
        errors, _ = self.periodic.validate(adsorption)
        self.assertTrue(any("explicit energy_expression" in error for error in errors))
        self.assertTrue(any("clean-surface" in error for error in errors))

        defect = self.periodic_base()
        defect["task_type"] = "defect"
        defect["model_review_id"] = "R-1"
        defect["periodic_model"] = adsorption["periodic_model"]
        defect["defect_model"] = {}
        errors, _ = self.periodic.validate(defect)
        self.assertEqual(sum("defect_model missing" in error for error in errors), 3)

        neb = self.periodic_base()
        neb["task_type"] = "neb"
        neb["model_review_id"] = "R-1"
        neb["periodic_model"] = adsorption["periodic_model"]
        neb["neb_model"] = {"initial_artifact_id": "same", "final_artifact_id": "same"}
        errors, _ = self.periodic.validate(neb)
        self.assertTrue(any("neb_model missing" in error for error in errors))
        self.assertIn("NEB endpoints must be distinct", errors)

        accepted = self.periodic_base()
        accepted["status"] = "accepted"
        accepted["support_level"] = "L0_REFERENCE"
        accepted["convergence"] = {}
        errors, warnings = self.periodic.validate(accepted)
        self.assertTrue(warnings)
        self.assertIn("accepted project has unresolved errors/warnings", errors)

    def test_periodic_manifest_cli_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "periodic.yaml"
            path.write_text(yaml.safe_dump(self.periodic_base()), encoding="utf-8")
            with (
                patch.object(sys, "argv", ["validate_periodic_manifest.py", str(path), "--json"]),
                redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                self.periodic.main()
            self.assertEqual(raised.exception.code, 0)
            path.write_text("{}\n", encoding="utf-8")
            with (
                patch.object(sys, "argv", ["validate_periodic_manifest.py", str(path)]),
                redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                self.periodic.main()
            self.assertEqual(raised.exception.code, 1)

    def poscar(self, *, selective: bool = False, cartesian: bool = False, scale: float = 1.0) -> str:
        mode = "Cartesian" if cartesian else "Direct"
        selector = "Selective dynamics\n" if selective else ""
        return f"test\n{scale}\n1 0 0\n0 1 0\n0 0 1\nH He\n1 1\n{selector}{mode}\n0 0 0 T T T\n0.5 0.5 0.5 F F F\n"

    def test_vasp_parsers_and_validation_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(self.vasp.parse_incar(root / "missing"), {})
            incar = root / "INCAR"
            incar.write_text("ENCUT = 500 ! comment\nISPIN=2 # comment\nLDAUL=2\n", encoding="utf-8")
            parsed = self.vasp.parse_incar(incar)
            self.assertEqual(parsed["ENCUT"], "500")

            short = root / "short"
            short.write_text("too short\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.vasp.parse_poscar(short)
            invalid = root / "invalid"
            invalid.write_text(self.poscar().replace("H He", "1 2"), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.vasp.parse_poscar(invalid)
            fewer = root / "fewer"
            fewer.write_text(self.poscar().rsplit("\n", 2)[0] + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.vasp.parse_poscar(fewer)

            poscar = root / "POSCAR"
            poscar.write_text(self.poscar(selective=True, cartesian=True, scale=2.0), encoding="utf-8")
            parsed_poscar = self.vasp.parse_poscar(poscar)
            self.assertTrue(parsed_poscar["selective_dynamics"])
            self.assertTrue(parsed_poscar["coordinate_mode"].startswith("c"))

            self.assertEqual(self.vasp.parse_kpoints(root / "missing-k"), {})
            kpoints = root / "KPOINTS"
            kpoints.write_text("short\nline\n", encoding="utf-8")
            self.assertIn("raw_lines", self.vasp.parse_kpoints(kpoints))
            kpoints.write_text("mesh\n0\nGamma\n2 2 2\n", encoding="utf-8")
            self.assertEqual(self.vasp.parse_kpoints(kpoints)["mode"], "Gamma")

            self.assertEqual(self.vasp.potcar_titles(root / "missing-potcar"), [])
            potcar = root / "POTCAR"
            potcar.write_text("TITEL = PAW_PBE H\nTITEL = PAW_PBE He\n", encoding="utf-8")
            self.assertEqual(len(self.vasp.potcar_titles(potcar)), 2)

            result = self.vasp.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("DFT+U" in error for error in result["errors"]))
            warnings = "\n".join(result["warnings"])
            self.assertIn("MAGMOM", warnings)
            self.assertIn("selective dynamics", warnings)
            self.assertIn("Cartesian POSCAR", warnings)

            incar.write_text("ENCUT=500\nEDIFF=1E-6\nPREC=Accurate\nNSW=2\nIBRION=-1\n", encoding="utf-8")
            result = self.vasp.validate(root)
            self.assertTrue(any("IBRION" in warning for warning in result["warnings"]))

            potcar.write_text("TITEL = PAW_PBE H\n", encoding="utf-8")
            result = self.vasp.validate(root)
            self.assertTrue(any("dataset count" in error for error in result["errors"]))
            potcar.write_text("TITEL = PAW_PBE He\nTITEL = PAW_PBE H\n", encoding="utf-8")
            result = self.vasp.validate(root)
            self.assertTrue(any("order mismatch" in error for error in result["errors"]))

    def test_vasp_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "POSCAR").write_text(self.poscar(), encoding="utf-8")
            (root / "INCAR").write_text("ENCUT=500\nEDIFF=1E-6\nPREC=Accurate\nKSPACING=0.2\n", encoding="utf-8")
            with (
                patch.object(sys, "argv", ["preflight_vasp.py", str(root), "--json"]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.vasp.main(), 0)
            (root / "INCAR").unlink()
            with (
                patch.object(sys, "argv", ["preflight_vasp.py", str(root)]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.vasp.main(), 1)

    def test_vmd_document_camera_selection_and_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            json_path = root / "spec.json"
            yaml_path = root / "spec.yaml"
            json_path.write_text('{"a": 1}', encoding="utf-8")
            yaml_path.write_text("a: 1\n", encoding="utf-8")
            self.assertEqual(self.vmd.load_document(json_path), {"a": 1})
            self.assertEqual(self.vmd.load_document(yaml_path), {"a": 1})
            json_path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.vmd.load_document(json_path)
            self.assertEqual(self.vmd.replace("{{A}}", {"A": 3}), "3")
            self.assertEqual(self.vmd.resolve_input(root, "a").parent, root)
            self.assertEqual(self.vmd.resolve_input(root, str(root / "a")), root / "a")
            self.assertIn("no explicit camera", self.vmd.camera_commands({}))
            self.assertIn("no transform", self.vmd.camera_commands({"camera": {}}))
            commands = self.vmd.camera_commands(
                {"camera": {"rotations": [["x", 10], ["bad", 2]], "scale_by": 1.2, "translate_by": [1, 2, 3]}}
            )
            self.assertIn("rotate x", commands)
            self.assertIn("scale by", commands)
            self.assertIn("translate by", commands)

            with self.assertRaises(ValueError):
                self.vmd.select_panel({"figures": []}, None, None, 0)
            with self.assertRaises(ValueError):
                self.vmd.select_panel({"figures": [{"id": "one", "panels": [{}]}]}, "missing", None, 0)
            with self.assertRaises(ValueError):
                self.vmd.select_panel({"figures": [{"id": "one", "panels": []}]}, None, None, 0)
            with self.assertRaises(ValueError):
                self.vmd.select_panel({"figures": [{"id": "one", "panels": [{}]}]}, None, "missing", 0)
            with self.assertRaises(ValueError):
                self.vmd.select_panel({"panels": ["bad"]}, None, None, 0)
            figure, panel = self.vmd.select_panel({"figures": [{"id": "one", "panels": [{"id": "a"}]}]}, "one", "a", 0)
            self.assertEqual((figure["id"], panel["id"]), ("one", "a"))

            templates = root / "skill" / "templates"
            templates.mkdir(parents=True)
            (templates / "vmd-esp.tcl").write_text(
                "{{DENSITY_CUBE}} {{ESP_CUBE}} {{WIDTH}} {{CAMERA_COMMANDS}}", encoding="utf-8"
            )
            (templates / "vmd-orbital.tcl").write_text("{{CUBE_FILE}} {{ISOVALUE}} {{HEIGHT}}", encoding="utf-8")

            esp_spec = root / "esp.yaml"
            esp_spec.write_text(
                yaml.safe_dump(
                    {
                        "figures": [
                            {
                                "id": "f",
                                "panels": [
                                    {
                                        "id": "a",
                                        "type": "esp",
                                        "density_cube": "density.cube",
                                        "esp_cube": "esp.cube",
                                        "parameters": {"density_isovalue_au": 0.002},
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out = root / "esp.tcl"
            with (
                patch.object(self.vmd, "SKILL_DIR", root / "skill"),
                patch.object(sys, "argv", ["make_vmd_tcl.py", str(esp_spec), "--out", str(out), "--allow-missing"]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.vmd.main(), 0)
            self.assertTrue(out.is_file())

            bad_esp = root / "bad-esp.yaml"
            bad_esp.write_text("figure_type: esp\n", encoding="utf-8")
            with (
                patch.object(self.vmd, "SKILL_DIR", root / "skill"),
                patch.object(sys, "argv", ["make_vmd_tcl.py", str(bad_esp), "--out", str(out)]),
                self.assertRaises(SystemExit),
            ):
                self.vmd.main()

            orbital = root / "orbital.yaml"
            orbital.write_text("cube_file: orbital.cube\nisovalue: 0.03\n", encoding="utf-8")
            with (
                patch.object(self.vmd, "SKILL_DIR", root / "skill"),
                patch.object(sys, "argv", ["make_vmd_tcl.py", str(orbital), "--out", str(out), "--allow-missing"]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.vmd.main(), 0)
            missing_orbital = root / "missing-orbital.yaml"
            missing_orbital.write_text("figure_type: orbital\n", encoding="utf-8")
            with (
                patch.object(self.vmd, "SKILL_DIR", root / "skill"),
                patch.object(sys, "argv", ["make_vmd_tcl.py", str(missing_orbital), "--out", str(out)]),
                self.assertRaises(SystemExit),
            ):
                self.vmd.main()

    def test_environment_text_command_and_inventory_helpers(self) -> None:
        env = self.environment
        synthetic_home = Path("/") / "home" / "person"
        with patch.object(env.Path, "home", return_value=synthetic_home):
            sanitized = env.sanitize_text(f"{synthetic_home}/file token=abc user@example.com\nsecond", limit=80)
        self.assertNotIn("token=abc", sanitized)
        self.assertNotIn("user@example.com", sanitized)
        self.assertIn("<HOME>", sanitized)
        self.assertEqual(env.sanitize_text("\x00\r"), "")

        with patch.object(env.shutil, "which", side_effect=[None, "/usr/bin/tool"]):
            self.assertEqual(env.resolve_command(["a", "b"]), "/usr/bin/tool")
        with patch.object(env.shutil, "which", return_value=None):
            self.assertIsNone(env.resolve_command(["a"]))

        success = subprocess.CompletedProcess([], 0, stdout="tool 1.0\n", stderr="")
        no_version = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        failed = subprocess.CompletedProcess([], 2, stdout="bad", stderr="")
        self.assertEqual(env.run_read_only("tool", [], runner=lambda *a, **k: success)["status"], env.AVAILABLE)
        self.assertEqual(
            env.run_read_only("tool", [], runner=lambda *a, **k: no_version)["status"], env.AVAILABLE_NO_VERSION
        )
        self.assertEqual(
            env.run_read_only("tool", [], runner=lambda *a, **k: failed)["status"], env.AVAILABLE_NO_VERSION
        )

        def exploding(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
            raise OSError("boom")

        self.assertEqual(env.run_read_only("tool", [], runner=exploding)["status"], env.PROBE_FAILED)

        specs = {"a": {"names": ["a"], "args": ["--version"]}, "b": {"names": ["b"], "args": []}}
        with patch.object(env, "resolve_command", side_effect=[None, "/bin/b"]):
            report = env.inspect_command_group(specs, probe_commands=False, runner=lambda *a, **k: success)
        self.assertEqual(report["a"]["status"], env.NOT_AVAILABLE)
        self.assertEqual(report["b"]["status"], env.AVAILABLE_NO_VERSION)
        with (
            patch.object(env, "resolve_command", return_value="/bin/tool"),
            patch.object(env, "run_read_only", return_value={"status": env.AVAILABLE, "version": "1", "returncode": 0}),
        ):
            report = env.inspect_command_group({"a": specs["a"]}, probe_commands=True, runner=lambda *a, **k: success)
        self.assertEqual(report["a"]["status"], env.AVAILABLE)

    def test_environment_device_parsers_queries_and_backends(self) -> None:
        env = self.environment
        nvidia = env.parse_nvidia_csv("H100,GPU-1,81920,590\nshort\nA,GPU-2,bad,591")
        self.assertEqual(len(nvidia), 2)
        self.assertEqual(nvidia[0]["memory_gb"], 80.0)
        self.assertIsNone(nvidia[1]["memory_gb"])

        rocm_payload = {
            "card0": {
                "Card series": "MI300",
                "Unique ID": "AMD-1",
                "VRAM Total Memory (B)": str(80 * 1024**3),
                "Driver Version": "6.0",
            },
            "card1": {"Device Name": "MI", "VRAM Total Memory (B)": "bad"},
            "skip": "bad",
        }
        self.assertEqual(env.parse_rocm_json("bad"), [])
        self.assertEqual(env.parse_rocm_json("[]"), [])
        rocm = env.parse_rocm_json(json.dumps(rocm_payload))
        self.assertEqual(len(rocm), 2)
        self.assertEqual(rocm[0]["memory_gb"], 80.0)
        self.assertIsNone(rocm[1]["memory_gb"])

        intel_payload = {
            "device_list": [
                {
                    "device_name": "Max",
                    "uuid": "INTEL-1",
                    "memory_physical_size_byte": str(64 * 1024**3),
                    "driver_version": "1",
                },
                {"name": "Arc", "memory_size": "bad"},
                "skip",
            ]
        }
        self.assertEqual(env.parse_intel_json("bad"), [])
        self.assertEqual(env.parse_intel_json("{}"), [])
        intel = env.parse_intel_json(json.dumps(intel_payload))
        self.assertEqual(len(intel), 2)
        self.assertEqual(intel[0]["memory_gb"], 64.0)
        self.assertIsNone(intel[1]["memory_gb"])

        completed = subprocess.CompletedProcess([], 0, stdout="H100,GPU-1,1024,590\n", stderr="")
        nonzero = subprocess.CompletedProcess([], 1, stdout="", stderr="")
        for query, parser_text in (
            (env.query_nvidia_devices, "H100,GPU-1,1024,590\n"),
            (env.query_rocm_devices, json.dumps(rocm_payload)),
            (env.query_intel_devices, json.dumps(intel_payload)),
        ):
            with patch.object(env, "resolve_command", return_value=None):
                self.assertEqual(query(runner=lambda *a, **k: completed), [])
            with patch.object(env, "resolve_command", return_value="/bin/tool"):
                result = query(
                    runner=lambda *a, parser_text=parser_text, **k: subprocess.CompletedProcess(
                        [], 0, stdout=parser_text, stderr=""
                    )
                )
                self.assertTrue(result)
                self.assertEqual(query(runner=lambda *a, **k: nonzero), [])
                self.assertEqual(query(runner=exploding_runner), [])

        with patch.object(env.platform, "system", return_value="Linux"):
            self.assertEqual(env.apple_gpu_inventory(), [])
        with (
            patch.object(env.platform, "system", return_value="Darwin"),
            patch.object(env.platform, "processor", return_value="Apple M"),
            patch.object(env.platform, "machine", return_value="arm64"),
            patch.object(env.platform, "mac_ver", return_value=("15.0", ("", "", ""), "")),
        ):
            self.assertEqual(env.apple_gpu_inventory()[0]["vendor"], "apple")

        versions = {"numpy": "2.0", "torch": "3.0"}
        with patch.object(
            env.importlib.metadata,
            "version",
            side_effect=lambda name: versions[name] if name in versions else raise_not_found(name),
        ):
            backends = env.python_backend_inventory()
        self.assertEqual(backends["numpy"]["status"], env.AVAILABLE)
        self.assertEqual(backends["tensorflow"]["status"], env.NOT_AVAILABLE)

    def test_environment_collection_validation_and_main(self) -> None:
        env = self.environment
        commands = {key: {"status": env.NOT_AVAILABLE, "command": None, "version": None} for key in env.COMMAND_SPECS}
        engines = {key: {"status": env.NOT_AVAILABLE, "command": None, "version": None} for key in env.ENGINE_SPECS}
        with (
            patch.object(env, "inspect_command_group", side_effect=[commands, engines]),
            patch.object(env, "query_nvidia_devices", return_value=[{"vendor": "nvidia"}]),
            patch.object(env, "query_rocm_devices", return_value=[{"vendor": "amd"}]),
            patch.object(env, "query_intel_devices", return_value=[{"vendor": "intel"}]),
            patch.object(env, "apple_gpu_inventory", return_value=[{"vendor": "apple"}]),
            patch.object(env, "cpu_inventory", return_value={"logical_threads": 8}),
            patch.object(env, "python_backend_inventory", return_value={}),
            patch.object(env.platform, "node", return_value="node"),
            patch.object(env.platform, "machine", return_value="x86_64"),
            patch.object(env.platform, "system", return_value="Linux"),
            patch.object(env.platform, "release", return_value="1"),
            patch.object(env.platform, "python_version", return_value="3.12"),
        ):
            report = env.collect_inventory(probe_commands=True, observed_at="2026-01-01T00:00:00Z")
        self.assertEqual(len(report["gpus"]), 4)
        self.assertEqual(env.validate_inventory(report), [])

        invalid = {"schema_version": "bad", "cpu": [], "gpus": {}, "toolchain": [], "privacy": {}}
        self.assertGreaterEqual(len(env.validate_inventory(invalid)), 8)

        static_commands = {
            key: {"status": env.NOT_AVAILABLE, "command": None, "version": None} for key in env.COMMAND_SPECS
        }
        static_engines = {
            key: {"status": env.NOT_AVAILABLE, "command": None, "version": None} for key in env.ENGINE_SPECS
        }
        with (
            patch.object(env, "inspect_command_group", side_effect=[static_commands, static_engines]),
            patch.object(env, "apple_gpu_inventory", return_value=[]),
            patch.object(env, "cpu_inventory", return_value={}),
            patch.object(env, "python_backend_inventory", return_value={}),
        ):
            report = env.collect_inventory(probe_commands=False, observed_at="fixed")
        self.assertEqual(report["source_kind"], "static-local-inspection")

        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "inventory.yaml"
            with (
                patch.object(env, "collect_inventory", return_value=report),
                patch.object(
                    sys,
                    "argv",
                    ["inspect_execution_environment.py", "--no-command-probes", "--format", "yaml", "--out", str(out)],
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(env.main(), 0)
            self.assertTrue(out.is_file())
            with (
                patch.object(env, "collect_inventory", return_value=invalid),
                patch.object(sys, "argv", ["inspect_execution_environment.py"]),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(env.main(), 1)


def raise_not_found(name: str) -> str:
    raise importlib.metadata.PackageNotFoundError(name)


def exploding_runner(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
    raise OSError("boom")


if __name__ == "__main__":
    unittest.main()
