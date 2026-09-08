from __future__ import annotations

import importlib.util
import itertools
import re
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "parse_gaussian.py"


def load_script() -> Any:
    spec = importlib.util.spec_from_file_location("gaussian_taxonomy_target", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def legacy_taxonomy(module: Any, text: str) -> list[dict[str, str]]:
    return [
        {"category": category, "evidence_pattern": pattern}
        for category, pattern in module.ERROR_TAXONOMY_RULES
        if re.search(pattern, text, re.IGNORECASE)
    ]


class GaussianErrorTaxonomyTests(unittest.TestCase):
    module: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script()

    def test_all_category_combinations_match_legacy_algorithm(self) -> None:
        evidence = [
            "SCF has not converged",
            "Optimization stopped",
            "Not enough memory",
            "No space left on device",
            "Problem with the distance matrix",
            "ECP for atom 5 was not found",
            "No data on checkpoint file",
            "Error termination via Lnk1e in /opt/g16/l502.exe",
            "Error termination via Lnk1e in /opt/g16/l9999.exe",
        ]
        for enabled in itertools.product((False, True), repeat=len(evidence)):
            text = "\n".join(item for item, include in zip(evidence, enabled, strict=True) if include)
            with self.subTest(enabled=enabled):
                self.assertEqual(self.module._error_taxonomy(text), legacy_taxonomy(self.module, text))

    def test_shared_evidence_preserves_all_overlapping_categories(self) -> None:
        cases = {
            "Erroneous write": ["MEMORY", "DISK_OR_IO"],
            "FileIO operation on non-existent file": ["DISK_OR_IO", "CHECKPOINT"],
            "erroneous WRITE\nfileio OPERATION on non-existent file": ["MEMORY", "DISK_OR_IO", "CHECKPOINT"],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                result = self.module._error_taxonomy(text)
                self.assertEqual([item["category"] for item in result], expected)
                self.assertEqual(result, legacy_taxonomy(self.module, text))

    def test_taxonomy_order_is_rule_order_not_text_order(self) -> None:
        text = "\n".join(
            [
                "l9999.exe",
                "No data on checkpoint file",
                "Unrecognized atomic symbol",
                "Atoms too close",
                "No space left on device",
                "Out-of-memory",
                "Number of steps exceeded",
                "Convergence failure -- run terminated",
                "l502.exe",
            ]
        )
        result = self.module._error_taxonomy(text)
        self.assertEqual(
            [item["category"] for item in result],
            [
                "SCF_CONVERGENCE",
                "OPTIMIZATION",
                "MEMORY",
                "DISK_OR_IO",
                "GEOMETRY",
                "BASIS_ECP",
                "CHECKPOINT",
                "L502",
                "L9999",
            ],
        )
        self.assertEqual(result, legacy_taxonomy(self.module, text))

    def test_taxonomy_does_not_call_per_rule_re_search(self) -> None:
        with patch.object(self.module.re, "search", side_effect=AssertionError("per-rule search called")):
            result = self.module._error_taxonomy("SCF has not converged\nErroneous write\nl9999.exe")
        self.assertEqual(
            [item["category"] for item in result],
            ["SCF_CONVERGENCE", "MEMORY", "DISK_OR_IO", "L9999"],
        )

    def test_compiled_index_contains_every_unique_evidence_alternative(self) -> None:
        unique_evidence: dict[str, list[str]] = {}
        for category, pattern in self.module.ERROR_TAXONOMY_RULES:
            for evidence in pattern.split("|"):
                unique_evidence.setdefault(evidence, []).append(category)

        self.assertEqual(len(self.module.ERROR_EVIDENCE_CATEGORIES), len(unique_evidence))
        indexed_categories = {
            category for categories in self.module.ERROR_EVIDENCE_CATEGORIES.values() for category in categories
        }
        self.assertEqual(indexed_categories, {category for category, _ in self.module.ERROR_TAXONOMY_RULES})

    def test_empty_and_unrelated_text_remain_empty(self) -> None:
        self.assertEqual(self.module._error_taxonomy(""), [])
        self.assertEqual(self.module._error_taxonomy("Normal termination of Gaussian 16"), [])


if __name__ == "__main__":
    unittest.main()
