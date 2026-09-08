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
NETWORK = ROOT / "examples/catalysis/network.yaml"


def load_script() -> Any:
    path = ROOT / "scripts/validate_reaction_network.py"
    spec = importlib.util.spec_from_file_location("reaction_network_fail_closed", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReactionNetworkFailClosedTests(unittest.TestCase):
    module: Any
    base: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()
        cls.base = yaml.safe_load(NETWORK.read_text(encoding="utf-8"))

    def test_valid_network_still_passes(self) -> None:
        errors, warnings = self.module.validate(copy.deepcopy(self.base))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_root_and_collection_types_fail_closed(self) -> None:
        self.assertIn("root must be a mapping", " ".join(self.module.validate([])[0]))
        data = copy.deepcopy(self.base)
        data["temperature_K"] = True
        data["species"] = "bad"
        data["reactions"] = {}
        errors, _ = self.module.validate(data)
        rendered = " ".join(errors)
        self.assertIn("temperature_K must be finite numeric", rendered)
        self.assertIn("species must be a list", rendered)
        self.assertIn("reactions must be a list", rendered)

    def test_malformed_species_and_reactions_do_not_crash(self) -> None:
        data = copy.deepcopy(self.base)
        data["species"] = [
            None,
            {
                "id": "",
                "composition": [],
                "charge": float("inf"),
                "phase": "solution",
                "free_energy": "bad",
                "artifact_id": "ART",
                "method_fingerprint_id": "MF",
                "acceptance_status": "pending",
            },
        ]
        data["reactions"] = [
            None,
            {
                "id": "",
                "reactants": [],
                "products": {"UNKNOWN": 0},
                "reversible": "yes",
                "forward_barrier": float("nan"),
                "reaction_free_energy": float("inf"),
                "reverse_barrier": "bad",
                "path_degeneracy": False,
            },
        ]
        errors, warnings = self.module.validate(data)
        rendered = " ".join(errors)
        self.assertIn("species[0] must be a mapping", rendered)
        self.assertIn("reactions[0] must be a mapping", rendered)
        self.assertIn("reversible must be boolean", rendered)
        self.assertIn("path_degeneracy must be finite numeric", rendered)
        self.assertTrue(warnings)

    def test_balance_warnings_and_accepted_status_are_enforced(self) -> None:
        data = copy.deepcopy(self.base)
        data["species"][1]["composition"]["H"] = 3
        data["reactions"][0].pop("reverse_barrier")
        data["reactions"][0].pop("transition_state_artifact_id")
        data["status"] = "accepted"
        errors, warnings = self.module.validate(data)
        self.assertTrue(any("violates element balance" in error for error in errors))
        self.assertTrue(any("accepted network" in error for error in errors))
        self.assertTrue(any("reverse_barrier" in warning for warning in warnings))
        self.assertTrue(any("transition-state" in warning for warning in warnings))

    def test_malformed_yaml_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "network.yaml"
            path.write_text("species: [\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_reaction_network.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
