from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_constraints.py"
    spec = importlib.util.spec_from_file_location("tsao_validate_constraints", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_constraints = load_validator()


class ConstraintContractTests(unittest.TestCase):
    def test_current_repository_constraints(self):
        self.assertEqual(validate_constraints.validate(ROOT), [])

    def test_parser_rejects_nonexact_duplicate_and_bootstrap_pins(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "constraints.txt"
            path.write_text(
                "numpy>=2\nNumPy==2.5.1\nnumpy==2.5.1\npip==26.0\n",
                encoding="utf-8",
            )
            _, failures = validate_constraints.parse_constraint_file(path)
            self.assertTrue(any("exact name==version" in item for item in failures), failures)
            self.assertTrue(any("duplicate constraint" in item for item in failures), failures)
            self.assertTrue(any("bootstrap tool" in item for item in failures), failures)

    def test_direct_requirement_must_be_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "constraints").mkdir()
            (root / "requirements.txt").write_text("numpy>=1,<3\n", encoding="utf-8")
            (root / "requirements-dev.txt").write_text("-r requirements.txt\nruff==0.15.22\n", encoding="utf-8")
            dummy = [f"package{index}==1.0" for index in range(20)]
            for stem, version in validate_constraints.SUPPORTED.items():
                (root / "constraints" / f"{stem}.txt").write_text(
                    f"# CPython {version} GitHub Actions run fixture\n" + "\n".join(dummy) + "\n",
                    encoding="utf-8",
                )
            failures = validate_constraints.validate(root)
            self.assertTrue(any("direct requirements missing" in item for item in failures), failures)


if __name__ == "__main__":
    unittest.main()
