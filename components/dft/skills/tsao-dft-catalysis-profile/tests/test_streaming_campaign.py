from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"catalysis_streaming_{name.replace('.', '_')}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CatalysisStreamingTests(unittest.TestCase):
    campaign: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.campaign = load_script("build_coordination_campaign.py")

    def valid_campaign(self) -> dict[str, Any]:
        return {
            "campaign_id": "C",
            "axes": {
                "substrate_or_additive": ["A", "B"],
                "catalyst_model": ["M1", "M2"],
                "coordination_mode": ["x", "y"],
                "conformer": ["c1", "c2"],
                "charge": [0],
                "multiplicity": [1],
            },
            "exclusions": [
                "substrate_or_additive=A|catalyst_model=M1|coordination_mode=x|conformer=c1|charge=0|multiplicity=1"
            ],
            "max_candidates": 32,
        }

    def test_streaming_output_and_cleanup(self) -> None:
        campaign = self.valid_campaign()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "campaign.csv"
            self.assertEqual(self.campaign.expand(campaign, out), 15)
            with out.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[-1]["candidate_id"], "C-0015")
            self.assertTrue(all(row["dft_status"] == "planned" for row in rows))
            campaign["max_candidates"] = 2
            blocked = root / "blocked.csv"
            with self.assertRaisesRegex(ValueError, "max_candidates"):
                self.campaign.expand(campaign, blocked)
            self.assertFalse(blocked.exists())

    def test_contract_edges(self) -> None:
        valid = self.valid_campaign()
        cases: list[Any] = [
            None,
            [],
            {"axes": []},
            {"axes": {}},
            {**valid, "exclusions": {}},
            {**valid, "max_candidates": -1},
        ]
        missing = self.valid_campaign()
        del missing["axes"]["multiplicity"]
        cases.append(missing)
        with tempfile.TemporaryDirectory() as temporary:
            for index, value in enumerate(cases):
                with self.subTest(index=index), self.assertRaises((ValueError, TypeError)):
                    self.campaign.expand(value, Path(temporary) / f"{index}.csv")


if __name__ == "__main__":
    unittest.main()
